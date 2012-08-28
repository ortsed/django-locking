from django.contrib import admin
from django.conf import settings
from django.utils.translation import ugettext as _
from locking.models import Lock
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

class LockableAdmin(admin.ModelAdmin):
	
	def changelist_view(self, request, extra_context=None):
		# we need the request objects in a few places where it"s usually not present, 
		# so we"re tacking it on to the LockableAdmin class
		self.request = request
		return super(LockableAdmin, self).changelist_view(request, extra_context)

	def save_model(self, request, obj, form, change):
		# object creation doesn"t need/have locking in place
		if obj.pk:
			obj.unlock_for(request.user)
		obj.save()
		
	def lock(self, lock):
		if lock.is_locked:
			minutes_remaining = lock.seconds_remaining/60
			
			locked_until = _("Still locked for %s minutes by %s") \
				% (minutes_remaining, lock.locked_by)
				
			if self.request.user == lock.locked_by: 
				locked_until_self = _("You have a lock on this article for %s more minutes.") \
					% (minutes_remaining)
				return u'<img src="%slocking/img/page_edit.png" title="%s" />' \
					% (settings.MEDIA_URL, locked_until_self)
			else:
				locked_until = _("Still locked for %s minutes by %s") \
					% (minutes_remaining, lock.locked_by)
				return u'<img src="%slocking/img/lock.png" title="%s" />' \
					% (settings.MEDIA_URL, locked_until)

		else:
			return ""
	lock.allow_tags = True
	
	list_display = ("__str__", "lock")


def get_lock_for_admin(self_obj, obj):
	""" 
	Returns the locking status along with a nice icon for the admin interface 
	use in admin list display like so: list_display = ["title", "get_lock_for_admin"]
	"""

	# Nevermind if we don't have the request object
	if not hasattr(self_obj, "request"):
		return ""
	else:
		content_type = ContentType.objects.get_for_model(obj)
		
		lock = Lock.objects.get_active_lock(entry_id=obj.id, app=content_type.app_label, model=content_type.model, user=self_obj.request.user)
		
		if lock:	
			class_name = "locked"
			locked_by = u"%s %s" % (lock.locked_by.first_name, lock.locked_by.last_name)	
		else:
			return ""
		
		
		if not lock.locked_by:
			locked_by = "N/A"
		
		output = str(obj.id)
		
		if hasattr(self_obj, "request") and self_obj.request.user.has_perm("blog.unlock_post"): 
			return u'<a href="#" class="lock-status %s" title="Locked By: %s" >%s</a>' % (class_name, locked_by, output)
		else: 
			return u'<span class="lock-status %s" title="Locked By: %s">%s</span>' % (class_name, locked_by, output)
		
get_lock_for_admin.allow_tags = True
get_lock_for_admin.short_description = "Lock"
