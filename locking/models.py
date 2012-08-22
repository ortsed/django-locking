from datetime import datetime, timedelta

from django.db import models, IntegrityError
from django.contrib.auth import models as auth
from locking import LOCK_TIMEOUT

class ObjectLockedError(IOError):
	pass
	
class LockManager(models.Manager):
	def get_active_lock(self, entry_id=None, app=None, model=None):
		last_locked_at = datetime.today() - timedelta(seconds=LOCK_TIMEOUT)
		return self.get(entry_id=entry_id, app=app, model=model, _locked_at__gte=last_locked_at)
		

class Lock(models.Model):
	""" 
	Main model for the locking app, has properties for the app/model/object that the lock is for and the time/person doing the locking
	"""
	objects = LockManager()

	class Meta:
		unique_together = (("app", "model", "entry_id"),)

	def __init__(self, *vargs, **kwargs):
		super(Lock, self).__init__(*vargs, **kwargs)
		self._state.locking = False
		
	_locked_at = models.DateTimeField(db_column='locked_at', 
		null=True,
		editable=False)
	
	app = models.CharField(max_length=255, null=True)
	
	model = models.CharField(max_length=255, null=True)
	
	entry_id = models.PositiveIntegerField(db_index=True)
	
	_locked_by = models.ForeignKey(auth.User, 
		db_column='locked_by',
		related_name="working_on_%(class)s",
		null=True,
		editable=False)
	
	# We don't want end-developers to manipulate database fields directly, 
	# hence we're putting these behind simple getters.
	# End-developers should use functionality like the lock_for method instead.
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
			if (datetime.today() - self.locked_at).seconds < LOCK_TIMEOUT:
				return True
			else:
				return False
		return False
		
	
	@property
	def lock_seconds_remaining(self):
		"""
		Time left before lock is no longer enabled
		"""
		return LOCK_TIMEOUT - (datetime.today() - self.locked_at).seconds
	
	def lock_for(self, user):
		"""
		Lock for a specific user
		"""

		if not isinstance(user, auth.User):
			raise ValueError("You should pass a valid auth.User to lock_for.")
		
		if self.lock_applies_to(user):
			raise ObjectLockedError("This object is already locked by another user.")
		else:
			self._locked_at = datetime.today()
			self._locked_by = user
			date = self.locked_at.strftime("%H:%M:%S")
			# an administrative toggle, to make it easier for devs to extend `django-locking`
			# and react to locking and unlocking
			self._state.locking = True

	def unlock(self):
		"""
		Override lock, for use by admins.
		"""
		self._locked_at = self._locked_by = None
		self._state.locking = True
	
	def unlock_for(self, user):
		"""
		Unlock for a specific user
		"""
	
		self.unlock()

	
	def lock_applies_to(self, user):
		"""
		A lock does not apply to the user who initiated the lock. Thus, 
		``lock_applies_to`` is used to ascertain whether a user is allowed
		to edit a locked object.
		"""
		# a lock does not apply to the person who initiated the lock
		if self.is_active and self.locked_by.id != user.id:
			return True
		else:
			return False

	
	def save(self, *vargs, **kwargs):

		try:
			super(Lock, self).save(*vargs, **kwargs)
		except IntegrityError:
			raise ObjectLockedError("Duplicate lock already in place")
			
		self._state.locking = False
