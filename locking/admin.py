from django.contrib import admin
from django.conf import settings
from django.utils.translation import ugettext as _
from locking.models import Lock
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

class LockableAdmin(admin.ModelAdmin):
    
    def changelist_view(self, request, extra_context=None):
        # we need the request objects in a few places where it's usually not present, 
        # so we're tacking it on to the LockableAdmin class
        self.request = request
        return super(LockableAdmin, self).changelist_view(request, extra_context)

    def save_model(self, request, obj, form, change):
        # object creation doesn't need/have locking in place
        if obj.pk:
            obj.unlock_for(request.user)
        obj.save()
        
    def lock(self, obj):
        if obj.is_locked:
            seconds_remaining = obj.lock_seconds_remaining
            minutes_remaining = seconds_remaining/60
            locked_until = _("Still locked for %s minutes by %s") \
                % (minutes_remaining, obj.locked_by)
            if self.request.user == obj.locked_by: 
                locked_until_self = _("You have a lock on this article for %s more minutes.") \
                    % (minutes_remaining)
                return '<img src="%slocking/img/page_edit.png" title="%s" />' \
                    % (settings.MEDIA_URL, locked_until_self)
            else:
                locked_until = _("Still locked for %s minutes by %s") \
                    % (minutes_remaining, obj.locked_by)
                return '<img src="%slocking/img/lock.png" title="%s" />' \
                    % (settings.MEDIA_URL, locked_until)

        else:
            return ''
    lock.allow_tags = True
    
    list_display = ('__str__', 'lock')


def get_lock_for_admin(self_obj, obj):
	''' 
	Returns the locking status along with a nice icon for the admin interface 
	use in admin list display like so: list_display = ['title', 'get_lock_for_admin']
	'''
	
	locked_by = ""
	content_type = ContentType.objects.get_for_model(obj)

	try:
		lock = Lock.objects.get(entry_id=obj.id, app=content_type.app_label, model=content_type.model)
		class_name = "locked"
		locked_by = u'%s %s' % (lock.locked_by.first_name, lock.locked_by.last_name)
		
	
	except Lock.DoesNotExist:
		class_name = "unlocked"
	except User.DoesNotExist:
		locked_by = "N/A"
	
	output = str(obj.id)
	
	if hasattr(self_obj, "request") and self_obj.request.user.has_perm(u'blog.unlock_post'): 
	
		return u'<a href="#" class="lock-status %s" title="Locked By: %s" >%s</a>' % (class_name, locked_by, output)
	else: 
		return '<span class="lock-status %s" title="Locked By: %s">%s</span>' % (class_name, locked_by, output)
		
get_lock_for_admin.allow_tags = True
get_lock_for_admin.short_description = "Lock"
