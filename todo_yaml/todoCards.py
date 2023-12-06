import re, datetime
from colorama import just_fix_windows_console, Style, Fore
import pytz

from todo_yaml.task_fields import getTaskValue, taskIsDone, task_date

def danger(s):
    return Fore.RED + s + Style.RESET_ALL

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

def dumpCards(matchedTasks, output, doc, fields, sorter):
    def is_allowed_field(field):
        return not fields or field in fields

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

        childMatches = []
        if 'subtasks' in task:
            for subtask in sorter(task['subtasks']):
                matchedSubtask = matchTask(matches, subtask, fields, sorter)
                if matchedSubtask:
                    childMatches.append(matchedSubtask)

            if childMatches:
                task = task.copy()
                task['subtasks'] = childMatches
                matched = True

        if matched:
            task = task.copy()
            task['subtasks'] = childMatches
            return task

    def formatCards(cards):
        output = []
        for card in cards:
            output.append(formatBox(formatCardName(card), formatCardBody(card)))

        return '\n'.join(output)

    def formatCardName(card):
        if 'task' in card:
            s = "%s%s%s" % (taskIsDone(card) and '✓ ' or '', card['task'], ' (%s)' % str(getTaskValue(card, 'id'))[:4])
            if '_queryMatch' in card:
                s = brighten(s)

        return s

    cardBodyHandlers = {
        'description': lambda card: (card['description'],),
        'id': lambda card: ('ID', card['id']),
        'status': lambda card: ('Status', formatCardStatus(card)),
        'version': lambda card: ('Version', card['version']),
        'date': lambda card: ('Date',
            not taskIsDone(card) and (
                task_date(card) < pytz.utc.localize(datetime.datetime.now()) and
                        danger(card['date']))
            or card['date']
        ),
        'name': lambda card: (),
        'subtasks': lambda card: (),
        'task': lambda card: (),
        'done': lambda card: (),
        '_queryMatch': lambda card: (),
        'tags': lambda card: ('Tags', ', '.join(map(lambda it: it, card['tags'])))
    }

    def formatCardStatus(card):
        if taskIsDone(card):
            return '✓'
        else:
            return card['status']

    def formatCardBody(card):
        lines = []

        if '_queryMatch' in card:
            for key in cardBodyHandlers:
                if is_allowed_field(key) and key in card:
                    lines.append(cardBodyHandlers[key](card))

            for key in card:
                if is_allowed_field(key) and key not in cardBodyHandlers:
                    lines.append((key.title(), card[key]))

        if 'subtasks' in card:
            lines.append((formatCards(card['subtasks']),))

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

    just_fix_windows_console()

    cards = list(matchTasks(doc, matchedTasks, fields, sorter))
    # if not cards:
    #     output.write('''No tasks found!\n\n''')
    #     output.write('''Either you've finished all your tasks, or your query needs to be updated.''')

    output.write(formatCards(cards))

