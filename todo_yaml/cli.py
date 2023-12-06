import sys, json, os, tempfile, shutil, datetime, pytz

import click
from ruyaml import YAML
import jq as jq_query

from dateutil.relativedelta import relativedelta
import dateutil.parser

from todo_yaml.todoCards import dumpCards

from todo_yaml.task_fields import getTaskValue, matchTaskId, task_date, taskIsDone

from todo_yaml import todo_yaml as ty

default_file_paths = [
    os.path.join(os.getcwd(), 'todo.yaml'),
    os.path.expanduser('~/todo.yaml')
]

output_formats = {
    "yaml": lambda tasks, output, *_: YAML.dump(tasks, output),
    "json": lambda tasks, output, *_: json.dump(tasks, output),
    "cards": dumpCards
}

undo_file = os.path.join(tempfile.gettempdir(), 'undo.todo.yaml')

def flatten_list(l):
    return [item for sublist in l for item in sublist]

def normalize_view_layer(it):
    if type(it) != str:
        return it
    else:
        return [it]

@click.group(invoke_without_command=True)
@click.option('-f', '--filename', type=click.Path(), help='yaml file to use')
@click.option('-w', '--where', default=[], help='jq query used to match tasks', multiple=True)
@click.option('-i', '--id', type=str, help='yaml file to use')
@click.option('-n', '--number-of-tasks', default=None, help='yaml file to use')
@click.option('-s', '--search-by', default='', help='yaml file to use')
@click.option('-t', '--sort-by', default=[], help='yaml file to use', multiple=True)
@click.option('-o', '--output', default='cards', help='file format to output results in')
@click.pass_context
def todo_yaml(ctx, filename, where, id, number_of_tasks, search_by, sort_by, output):
    yaml = YAML()

    footer = {}

    if not filename:
        for path in default_file_paths:
            if os.path.exists(path):
                filename = path
                break
        else:
            raise Exception(f"Couldn't find todo.yaml - tried paths {', '.join(default_file_paths)}")

    with open(filename, 'r', encoding='utf-8') as input_file:
        docs = list(yaml.load_all(input_file))

    doc = ty.get_body(docs)
    footer = ty.get_footer(docs)

    sorter = lambda it: it

    if sort_by:
        sorter = lambda tasks: sorted(tasks, key=lambda task:
            [
                field.startswith('-') and
                Reversor(getTaskValue(task, field[1:])) or
                getTaskValue(task, field)
                    for field in sort_by
            ])

    where = list(where)
    where = flatten_list([
        q.startswith('#') and q or
        q.split('/')
        for q in where
    ])
    if not where:
        where = ['default']

    if search_by:
        where += [f'select(.[] | type == "string" and (ascii_downcase|contains("{search_by}")))']

    where = flatten_list([
        q.startswith('#') and [q[1:]] or
        normalize_view_layer(footer['views'][q]['where'])
        for q in where
    ])


    for task in jq_query.compile('.. | select(type == "object" and has("date") and has("repeat") and .status == "done" and (.date | fromdateiso8601 < now))').input_value(doc).all():
        set_fields(doc, [task], reschedule_task(task))

    matched_tasks = jq_query.compile(
        ' | '.join([ty.prepare_query(part) for part in where])
    ).input_value(doc).all()

    if id:
        matched_tasks = list(filter(lambda task: matchTaskId(task, id), matched_tasks))

    matched_tasks = matched_tasks[:number_of_tasks]

    ctx.obj = {
        'footer':           footer,
        'yaml':             yaml,
        'matched_tasks':    matched_tasks,
        'doc':              doc,
        'sorter':           sorter,
        'filename':         filename,
        'output':           output
    }

    if ctx.invoked_subcommand is None:
        ctx.invoke(query)


@todo_yaml.command(name='query')
@click.option('-o', '--output', default='cards', help='file format to output results in')
@click.option('-s', '--field-set', default=[], help='yaml file to use', multiple=True)
@click.pass_context
def query(ctx, field_set, output):
    matched_tasks = ctx.obj['matched_tasks']
    doc = ctx.obj['doc']
    sorter = ctx.obj['sorter']

    output_formats[output](matched_tasks, sys.stdout, doc, field_set, sorter)

@todo_yaml.command(name='done')
@click.pass_context
def done(ctx):
    backup_doc(**ctx.obj)
    update_task(**ctx.obj, updates={ 'status': 'done' })

@todo_yaml.command(name='status')
@click.argument('status')
@click.pass_context
def done(ctx, status):
    backup_doc(**ctx.obj)
    update_task(**ctx.obj, updates={ 'status': status })

@todo_yaml.command(name='set')
@click.argument('updates', nargs=-1)
@click.pass_context
def set_task_values(ctx, updates):
    backup_doc(**ctx.obj)

    update_task(**ctx.obj, updates={
        updates[i]: updates[i+1] for i in range(0, len(updates), 2)
    })

@todo_yaml.command(name='undo')
@click.pass_context
def undo(ctx):
    shutil.move(undo_file, ctx.obj['filename'])
    backup_doc(**ctx.obj)

def update_task(doc, matched_tasks, filename, footer, output, updates, sorter, yaml, **_):
    set_fields(doc, matched_tasks, updates)

    for task in matched_tasks:
        update_task_values(task, updates)

    output_formats[output](matched_tasks, sys.stdout, doc, [], sorter)

    save_doc(doc, footer, filename, yaml)

@todo_yaml.command(name='task')
@click.argument('task')
@click.pass_context
def task(ctx, task):
    backup_doc(**ctx.obj)

    doc = ctx.obj['doc']

    added_task = { 'task': task }
    doc.append(added_task)

    output_formats[ctx.obj['output']]([added_task], sys.stdout, doc, [], lambda it: it)

    save_doc(doc, ctx.obj['footer'], ctx.obj['filename'], ctx.obj['yaml'])

@todo_yaml.command(name='subtask')
@click.argument('task')
@click.argument('values', nargs=-1)
@click.pass_context
def subtask(ctx, task, values):
    backup_doc(**ctx.obj)

    doc = ctx.obj['doc']

    added_task = {
        values[i]: values[i+1] for i in range(0, len(values), 2)
    }
    added_task['task'] = task

    matched_tasks = ctx.obj['matched_tasks']
    matched_task = matched_tasks[0]

    tasks = [] + (
        'subtasks' in matched_task and
        matched_task['subtasks'] or
        []
    ) + [added_task]

    set_fields(doc, [matched_task], { 'subtasks': tasks })

    output_formats[ctx.obj['output']]([added_task], sys.stdout, doc, [], lambda it: it)

    save_doc(doc, ctx.obj['footer'], ctx.obj['filename'], ctx.obj['yaml'])

def backup_doc(doc, footer, yaml, **_):
    save_doc(doc, footer, undo_file, yaml)

def save_doc(doc, footer, filename, yaml):
    whole_doc = [doc]

    if footer:
        whole_doc.append(footer)

    with open(filename, 'w', encoding='utf-8') as output:
        yaml.dump_all(whole_doc, output)

def set_fields(tasks, matched_tasks, values):
    for task in tasks:
        if task in matched_tasks:
            update_task_values(task, values)

        if 'subtasks' in task:
            set_fields(task['subtasks'], matched_tasks, values)

def update_task_values(task, values):
    for key, value in values.items():
        task[key] = value
        if value is None:
            del task[key]

repetition_cycles = {
    'daily': relativedelta(days = 1),
    'weekly': relativedelta(weeks = 1),
    'biweekly': relativedelta(weeks = 1),
    'monthly': relativedelta(months = 1),
    'monthly': relativedelta(months = 1),
    'annually': relativedelta(years = 1),
}

def reschedule_task(task):
    d = {}

    next_date = task_next_date(task_date(task), task['repeat'])

    if taskIsDone(task):
        d['status'] = None

    d['date'] = next_date.isoformat().replace('+00:00', 'Z')

    return d

def task_next_date(date, repeat):
    next_date = date + repetition_cycles[repeat]

    if next_date < pytz.utc.localize(datetime.datetime.now()):
        return task_next_date(next_date, repeat)
    else:
        return next_date

class Reversor:
    def __init__(self, obj):
        self.obj = obj

    def __eq__(self, other):
        return other.obj == self.obj

    def __lt__(self, other):
        return other.obj < self.obj

if __name__ == '__main__':
    todo_yaml()
