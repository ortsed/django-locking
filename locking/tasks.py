

def remove_stale_locks():
	from datetime import datetime, timedelta
	from django.db import connection, transaction
	cursor = connection.cursor()
	
	cursor.execute("DELETE FROM locking_lock WHERE locked_at < %s", [datetime.now() - timedelta(days=1)]) 
	
	transaction.commit_unless_managed()