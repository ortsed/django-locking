import simplejson
from django.http import HttpResponse
from locking import LOCK_TIMEOUT
from locking.models import Lock, ObjectLockedError

"""
These views are called from javascript to open and close assets (objects), in order
to prevent concurrent editing.
"""

def lock(request, app, model, id):

	try:
		obj = Lock.objects.get(entry_id=id, app=app, model=model, _locked_by=request.user)
		   	
		obj.lock_for(request.user)
		obj.save()
		return HttpResponse(status=200)
		
	except:
		try:
			obj = Lock()
			obj.entry_id = id
			obj.app = app
			obj.model = model
			obj.lock_for(request.user)
			obj.save()
			return HttpResponse(status=200)
			
		except ObjectLockedError:
			# The user tried to overwrite an existing lock by another user.
			# No can do, pal!
			return HttpResponse(status=403)

def unlock(request, app, model, id):
	'''
	Users who don't have exclusive access to an object anymore may still
	request we unlock an object. This happens e.g. when a user navigates
	away from an edit screen that's been open for very long.
	When this happens, LockableModel.unlock_for will throw an exception, 
	and we just ignore the request.
	That way, any new lock that may since have been put in place by another 
	user won't get accidentally overwritten.
	'''
	try:
		obj = Lock.objects.get(entry_id=id, app=app, model=model)
		obj.delete()

		return HttpResponse(status=200)
	except:
		return HttpResponse(status=403)

def is_locked(request, app, model, id):
	try:
		obj = Lock.objects.get(entry_id=id, app=app, model=model)
		
		if obj.locked_by == request.user:
			return HttpResponse(status=200)
		else :
			response = simplejson.dumps({
				"is_active": obj.is_locked,
				"for_user": getattr(obj.locked_by, 'username', None),
				"applies": obj.lock_applies_to(request.user),
				})
			return HttpResponse(response)
	except:
		return HttpResponse(status=200)

def js_variables(request):
	response = "var locking = " + simplejson.dumps({
		'base_url': "/".join(request.path.split('/')[:-1]),
		'timeout': LOCK_TIMEOUT,
		})
	return HttpResponse(response, mimetype="application/javascript")