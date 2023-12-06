import base64
import hashlib
import dateutil.parser
import pytz

defaultValues = {
    'status': lambda it: '',
    'id': lambda it: 'id' in it and it['id'] or \
        base64.b32encode(hashlib.sha1(it['task'].encode('utf-8')).digest()).decode('utf-8').lower()
}

def getTaskValue(task, key):
    if key not in task:
        return defaultValues[key](task)
    else:
        return task[key]

def taskHasValue(task, key):
    return key in task or key in defaultValues

def taskIsDone(task):
    return getTaskValue(task, 'status') == 'done'

def getTaskId(task):
    return getTaskValue(task, 'id')

def matchTaskId(task, id):
    return getTaskId(task).startswith(id)

def task_date(task):
    return dateutil.parser.isoparse(task['date'])