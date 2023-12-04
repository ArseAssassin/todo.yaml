import re
from colorama import just_fix_windows_console, Style

def dumpCards(matchedTasks, output, doc, fields, sorter):
    just_fix_windows_console()

    cards = list(matchTasks(doc, matchedTasks, fields, sorter))
    if not cards:
        output.write('''No tasks found!\n\n''')
        output.write('''Either you've finished all your tasks, or your query needs to be updated.''')

    output.write(formatCards(cards))

def matchTasks(tasklist, matches, fields, sorter):
    for task in sorter(tasklist):
        matched = matchTask(matches, task, fields, sorter)
        if matched:
            yield matched

def matchTask(matches, task, fields, sorter):
    matched = False

    for match in matches:
        if task == match:
            task = task.copy()
            task['_queryMatch'] = True
            matched = True
            break

    if 'tasks' in task:
        childMatches = []
        for subtask in sorter(task['tasks']):
            matchedSubtask = matchTask(matches, subtask, fields, sorter)
            if matchedSubtask:
                childMatches.append(matchedSubtask)

        if childMatches:
            task = task.copy()
            task['tasks'] = childMatches
            matched = True

    if matched:
        return { key: value for key, value in task.items() if key in fields or (key == 'tasks' and childMatches) }

def brighten(s):
    return Style.BRIGHT + s + Style.RESET_ALL

def dim(s):
    return Style.DIM + s + Style.RESET_ALL

def stripAnsiCodes(line):
    ansi_escape = re.compile(r'(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', line)

def ansiLen(s):
    return len(stripAnsiCodes(s))

def ansiLjust(s, width):
    return s + ' ' * (width - ansiLen(s))

def formatCards(cards):
    output = []
    for card in cards:
        output.append(formatBox(formatCardName(card), formatCardBody(card)))

    return '\n'.join(output)

def formatCardName(card):
    s = card['name']
    if '_queryMatch' in card:
        s = brighten(s)
    return s

cardBodyHandlers = {
    'description': lambda card: (card['description'],),
    'status': lambda card: ('Status', formatCardStatus(card['status']) + '\n'),
    'version': lambda card: ('Version', card['version']),
    'date': lambda card: ('Date', card['date']),
    'name': lambda card: (),
    'tasks': lambda card: (),
    '_queryMatch': lambda card: (),
    'tags': lambda card: ('Tags', ', '.join(map(lambda it: it, card['tags'])))
}

def formatCardStatus(status):
    if status == 'done':
        return '✓'
    else:
        return status

def formatCardBody(card):
    lines = []

    if '_queryMatch' in card:
        for key in cardBodyHandlers:
            if key in card:
                lines.append(cardBodyHandlers[key](card))

        for key in card:
            if key not in cardBodyHandlers:
                lines.append((key, card[key]))

    if 'tasks' in card:
        lines.append((formatCards(card['tasks']),))

    return formatMetadataLines(lines)

def formatMetadataLines(lines):
    lines = list(filter(lambda it: len(it) > 0, lines))

    doubleLines = list(filter(lambda it: len(it) == 2, lines))

    if doubleLines:
        leftColWidth = max(map(
            lambda it: ansiLen(it[0]),
            doubleLines
        )) + 1

    output = []

    lastType = -1
    for line in lines:
        lineType = len(line)

        if lastType != lineType:
            output.append('')

        if lineType == 1:
            output.append(line[0])
        elif lineType == 2:
            output.append(
                '%s %s' % (
                    ansiLjust(line[0] + ':', leftColWidth),
                    line[1]
                )
            )

        lastType = lineType

    return '\n'.join(output).strip()

def formatBox(heading, content):
    lines = content.split('\n')
    width = max(ansiLen(heading), *map(lambda it: ansiLen(it), lines))

    s = ''
    s += '.' + '—' * (width + 2) + '.\n'

    s += '| %s |\n' % (ansiLjust(heading, width))

    corner = (content.strip() and '+' or '\'')

    s += corner + '—' * (width + 2) + corner + '\n'
    if content.strip():
        for line in content.split('\n'):
            s += '| %s |\n' % ansiLjust(line, width)
        s += '\'' + '—' * (width + 2) + '\'\n'
    return s

