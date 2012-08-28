import simplejson
from django.http import HttpResponse
from locking import LOCK_TIMEOUT
from locking.models import Lock, ObjectLockedError

def lock(request, app, model, id):
	""" Create or re-lock an object based on the app/model/id """
	try:
		lock = Lock.objects.set_lock(entry_id=id, app=app, model=model, user=request.user)
		return HttpResponse(status=200)
	except ObjectLockedError, ValueError:
		return HttpResponse(status=403)


def unlock(request, app, model, id):
	"""
	Delete the lock when closing a page or other situations when the user is no longer editing
	"""
	if Lock.objects.delete_lock(entry_id=id, app=app, model=model):
		return HttpResponse(status=200)
	else:
		return HttpResponse(status=403)

def is_locked(request, app, model, id):
	""" 
	Check lock status of object, return 200 response if not, return lock details if it is
	"""
	lock = Lock.objects.get_active_lock(entry_id=id, app=app, model=model, user=request.user)
	if lock:
		response = simplejson.dumps({
			"for_user": getattr(obj.locked_by, "username", None),
			})
		return HttpResponse(response, mimetype="application/javascript")
	else:
		return HttpResponse(status=200)

def js_variables(request):
	"""
	Pass locking settings to the admin page as JS variables
	"""
	response = "var locking = " + simplejson.dumps({
		"base_url": "/".join(request.path.split("/")[:-1]),
		"timeout": LOCK_TIMEOUT,
		})
	return HttpResponse(response, mimetype="application/javascript")