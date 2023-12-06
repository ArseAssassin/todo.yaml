import sys, json, os, tempfile, shutil

import click
from ruyaml import YAML
import jq as jq_query

from todo_yaml.todoCards import dumpCards

from todo_yaml.task_fields import getTaskValue, matchTaskId

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

@click.group(invoke_without_command=True)
@click.option('-f', '--filename', type=click.Path(), help='yaml file to use')
@click.option('-w', '--where', help='jq query used to match tasks')
@click.option('-v', '--view', help='runs a query stored in views section of your yaml file', multiple=True)
@click.option('-i', '--id', type=str, help='yaml file to use')
@click.option('-n', '--number-of-tasks', default=None, help='yaml file to use')
@click.option('-s', '--search-by', default='', help='yaml file to use')
@click.option('-t', '--sort-by', default=[], help='yaml file to use', multiple=True)
@click.option('-o', '--output', default='cards', help='file format to output results in')
@click.pass_context
def todo_yaml(ctx, filename, where, view, id, number_of_tasks, search_by, sort_by, output):
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

    if len(docs) == 1:
        doc = docs[0]
    else:
        footer = docs[1]
        doc = docs[0]

    sorter = lambda it: it

    if sort_by:
        sorter = lambda tasks: sorted(tasks, key=lambda task:
            [
                field.startswith('-') and
                Reversor(getTaskValue(task, field[1:])) or
                getTaskValue(task, field)
                    for field in sort_by
            ])

    if id:
        where = 'true'
    elif search_by:
        where = f'select(.[] | type == "string" and (ascii_downcase|contains("{search_by}")))'

    if not where:
        if not view:
            if 'views' not in footer:
                where = '.status != "done"'
            else:
                selected_view = footer['views']['default']
                where = selected_view['query']
        else:
            selected_views = [footer['views'][q] for q in view]
            where = ' and '.join([selected_view['query'] for selected_view in selected_views])

    matched_tasks = jq_query.compile(f'.. | select(type == "object" and ({where}))').input_value(doc).all()

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
        for key, value in updates.items():
            task[key] = value

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
            for key in values:
                task[key] = values[key]

        if 'subtasks' in task:
            set_fields(task['subtasks'], matched_tasks, values)

class Reversor:
    def __init__(self, obj):
        self.obj = obj

    def __eq__(self, other):
        return other.obj == self.obj

    def __lt__(self, other):
        return other.obj < self.obj

if __name__ == '__main__':
    todo_yaml()
