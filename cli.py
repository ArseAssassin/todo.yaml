@click.command()
@click.option('--jq', default='.', help='arbitrary query to run against supplied todo file')
@click.option('--format', default='yaml', help='file format to output results in')
@click.option('--filename', help='yaml file to use')
def todoYaml(filename, jq, format):
    doc = normalize(yaml.safe_load(open(filename, 'r')))
    print(formatters[format](jqQuery.compile(jq).input_value(doc).all()))

