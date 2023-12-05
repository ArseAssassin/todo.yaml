defaultValues = {
    'status': lambda it: '',
    'id': lambda it: 'id' in it and it['id'] or hex(hash(it['task']))[3:]
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