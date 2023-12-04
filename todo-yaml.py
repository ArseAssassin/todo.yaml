import sys, json
import click
from ruyaml import YAML
import jq as jqQuery

from todoCards import dumpCards

@click.command()
@click.option('-o', '--output', default='cards', help='file format to output results in')
@click.option('-q', '--query', help='jq query used to match tasks')
@click.option('-v', '--view', help='runs a query stored in views section of your yaml file', multiple=True)
@click.option('-i', '--input-file', default='./todo.yaml', type=click.Path(exists=True), help='yaml file to use')
@click.option('-s', '--field-set', default=[], help='yaml file to use', multiple=True)
@click.option('-t', '--sort-by', default=[], help='yaml file to use', multiple=True)
def todoYaml(input_file, field_set, query, view, output, sort_by):
    yaml = YAML()

    header = {}

    dumpers = {
        "yaml": lambda tasks, output, *_: yaml.dump(tasks, output),
        "json": lambda tasks, output, *_: json.dump(tasks, output),
        "cards": dumpCards
    }

    input = open(input_file, 'r')

    docs = list(yaml.load_all(input))

    input.close()

    if len(docs) == 1:
        doc = docs[0]
    else:
        header = docs[1]
        doc = docs[0]

    sorter = lambda it: it

    if sort_by:
        sorter = lambda tasks: sorted(tasks, key=lambda task:[
            field.startswith('-') and reversor(task[field[1:]]) or task[field]
                for field in sort_by
        ])

    if not field_set:
        if 'views' in header and 'default_fields' in header['views']:
            fields = header['views']['default_fields']
        else:
            fields = ['name', 'status', 'description', 'date']

    if not query:
        if not view:
            if 'views' not in header:
                query = '.status != "done"'
            else:
                selectedView = header['views']['default']
                query = selectedView['query']
                if 'fields' in selectedView:
                    fields = selectedView['fields']
        else:
            selectedViews = [header['views'][q] for q in view]
            query = ' and '.join([selectedView['query'] for selectedView in selectedViews])
            fields += [field for view in selectedViews for field in ('fields' in view and view['fields'] or [])]

    fields += internalFields

    completeQuery = '.. | select(type == "object" and (%s))' % query
    matchedTasks = jqQuery.compile(completeQuery).input_value(doc).all()

    dumpers[output](matchedTasks, sys.stdout, doc, fields, sorter)

internalFields = ['_queryMatch', 'name']

class reversor:
    def __init__(self, obj):
        self.obj = obj

    def __eq__(self, other):
        return other.obj == self.obj

    def __lt__(self, other):
        return other.obj < self.obj

if __name__ == '__main__':
    todoYaml()
