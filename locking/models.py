from datetime import datetime, timedelta

from django.db import models, IntegrityError
from django.contrib.auth import models as auth
from locking import LOCK_TIMEOUT

class ObjectLockedError(IOError):
	pass
	
class LockManager(models.Manager):
	def get_active_lock(self, entry_id=None, app=None, model=None, user=None):
		""" 
		Get a lock for an app/model/id, return None if none, stale lock, or already exists for this user 
		"""
		
		try:
			lock = self.get(entry_id=entry_id, app=app, model=model)
		except Lock.DoesNotExist:
			return None
		
		if lock.locked_by.id == user.id:
			return None
			
		elif not lock.is_active:
			lock.delete()
			return None
		else:
			return lock
			
	def delete_lock(self, entry_id=None, app=None, model=None):
		"""
		Try to delete the lock if it exists 
		"""
		
		try:
			lock = self.get(entry_id=entry_id, app=app, model=model)
			lock.delete()
			return True
			
		except Lock.DoesNotExist:
			return False
			
	def set_lock(self, entry_id=None, app=None, model=None, user=None):
		"""
		Update the lock if it exists, create a new one if it doesnt, and return false if this fails
		"""
		lock = self.get_active_lock(entry_id=entry_id, app=app, model=model, user=user)
		
		if lock:
			if lock.locked_by.id != user.id:
				raise ObjectLockedError("This object is already locked by another user.")
			
		else:
			# Lock doesnt exist, creating a new lock
			lock = Lock()
			lock.entry_id = entry_id
			lock.app = app
			lock.model = model
			
			#if not isinstance(user, auth.User):
			#	raise ValueError("You should pass a valid auth.User to lock_for.")
			
			lock._locked_at = datetime.today()
			lock._locked_by = user
		
		# try to save the lock
		lock.save()
		return True

	
	
	

class Lock(models.Model):
	""" 
	Main model for the locking app, has properties for the app/model/object that the lock is for and the time/person doing the locking
	"""
	objects = LockManager()

	class Meta:
		unique_together = (("app", "model", "entry_id"),)
		
	_locked_at = models.DateTimeField(db_column="locked_at", 
		null=True,
		editable=False
	)
	
	app = models.CharField(max_length=255, null=True)
	
	model = models.CharField(max_length=255, null=True)
	
	entry_id = models.PositiveIntegerField(db_index=True)
	
	_locked_by = models.ForeignKey(auth.User, 
		db_column="locked_by",
		null=True,
		editable=False)

	@property
	def locked_at(self):
		"""A simple ``DateTimeField`` that is the heart of the locking mechanism. Read-only."""
		return self._locked_at
	
	@property
	def locked_by(self):
		return self._locked_by

	@property
	def is_active(self):
		"""
		Checks if lock exists and hasn't timed out
		"""
		if isinstance(self.locked_at, datetime):
			if (datetime.now() - self.locked_at).seconds < LOCK_TIMEOUT:
				return True
			else:
				return False
		else:
			return False
		
	
	@property
	def seconds_remaining(self):
		"""
		Time left before lock is no longer enabled
		"""
		return LOCK_TIMEOUT - (datetime.today() - self.locked_at).seconds


	def unlock(self):
		"""
		Override lock, for use by admins.
		"""
		self._locked_at = self._locked_by = None
	
	def unlock_for(self, user):
		"""
		Unlock for a specific user
		"""
		if self._locked_by.id == user.id:
			self.unlock()
	
	def save(self, *vargs, **kwargs):
		""" Try to update the lock, except for duplicate errors """
		try:
			super(Lock, self).save(*vargs, **kwargs)
		except IntegrityError:
			raise ObjectLockedError("Duplicate lock already in place")
