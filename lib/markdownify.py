#!/usr/bin/env python3

import sys
import os
from os.path import exists as path_exists, join as path_join
from textwrap import indent
from .flatten import flatten
from .run import run_command as run
from .find_unmerged_branches import find_unmerged_branches_in_cwd


def indent4(string):
    return indent(string, '    ')


def unicode_truncate(s, length, encoding='utf-8'):
    encoded = s.encode(encoding)[:length]
    return encoded.decode(encoding, 'ignore')


def process_file(filename, steps, spec, cwd):
    steps = steps if type(steps) is list else [steps]

    output = []
    header = '### ' + filename

    options = {
        'timeout': 4,
        'truncate_after': 10000,  # 10K
        'truncate_contents': False,
    }
    options.update(spec.get('options', {}).get(filename, {}))

    file_status, file_contents = run(['cat', filename])
    if file_status == 'success':
        _, last_edit = run(['git', 'log',
                            '-n', '1',
                            r'--pretty=format:%cd',
                            '--', filename])
        header += ' ({})'.format(last_edit)
    output.extend([header, '\n'])

    if options['truncate_contents']:
        file_contents = unicode_truncate(file_contents, options['truncate_contents'])

    if file_status != 'success':
        output.append('**the file %s does not exist**\n' % filename)
        output.append('`ls .` says that these files exist:\n')
        output.append(indent4('\n'.join(os.listdir('.'))) + '\n\n')
        return '\n'.join(output)

    output.extend(['**contents of %s**\n' % filename, indent4(file_contents)])
    output.append('\n')

    any_step_failed = False
    for step in steps:
        if step and not any_step_failed:
            command = step.replace('$@', filename)
            status, compilation = run(command.split())

            if compilation:
                warnings_header = '**warnings: `%s`**\n' % (command)
                output.extend([warnings_header, indent4(compilation)])
            else:
                warnings_header = '**no warnings: `%s`**' % (command)
                output.extend([warnings_header])

            if status != 'success':
                any_step_failed = True

            output.append('\n')

        elif any_step_failed:
            break

    if not steps or any_step_failed:
        return '\n'.join(output)

    inputs = spec.get('inputs', {})

    tests = spec.get('tests', {}).get(filename, [])
    if type(tests) is not list:
        tests = [tests]

    for test in tests:
        if not test:
            continue

        test = test.replace('$@', './%s' % filename)
        test_string = test

        test = test.split(' | ')

        input_for_test = None
        for cmd in test[:-1]:
            # decode('unicode_escape') de-escapes the backslash-escaped strings.
            # like, it turns the \n from "echo Hawken \n 26" into an actual newline,
            # like a shell would.
            cmd = bytes(cmd, 'utf-8').decode('unicode_escape')
            cmd = cmd.split(' ')

            status, input_for_test = run(cmd, input=input_for_test)
            input_for_test = input_for_test.encode('utf-8')

        test_cmd = test[-1].split(' ')

        if path_exists(path_join(cwd, filename)):
            status, full_result = run(test_cmd,
                                      input=input_for_test,
                                      timeout=options['timeout'])

            result = unicode_truncate(full_result, options['truncate_after'])
            truncate_msg = 'output truncated after %d bytes' % (options['truncate_after']) \
                           if full_result != result else ''

            items = [item for item in [status, truncate_msg] if item]
            status = '; '.join(items)
            output.append('**results of `%s`** (status: %s)\n' % (test_string, status))
            output.append(indent4(result))

        else:
            output.append('%s could not be found.\n' % filename)

        output.append('\n')

    output.extend(["\n\n"])

    return '\n'.join(output)


def find_unmerged_branches():
    # approach taken from https://stackoverflow.com/a/3602022/2347774
    unmerged_branches = find_unmerged_branches_in_cwd()
    if not unmerged_branches:
        return ''

    result = 'Unmerged branches:\n'

    for b in unmerged_branches:
        result += '    {}\n'.format(b)

    return result + '\n\n\n'


def markdownify_throws(hw_id, username, spec):
    cwd = os.getcwd()
    results = []

    inputs = spec.get('inputs', {})
    for filename, contents in inputs.items():
        with open(path_join(cwd, filename), 'w') as outfile:
            outfile.write(contents)

    files = [(filename, steps)
             for file in spec['files']
             for filename, steps in file.items()]

    for filename, steps in files:
        result = process_file(filename, steps, spec, cwd)
        results.append(result)

    [run(['rm', '-f', '%s.exec' % file]) for file, steps in files]
    [os.remove(path_join(cwd, inputfile)) for inputfile in inputs]

    unmerged = find_unmerged_branches()
    result_string = ''.join(results)
    return '# {} — {} \n\n{}{}'.format(hw_id, username, unmerged, result_string)


def markdownify(*args, **kwargs):
    try:
        return markdownify_throws(*args, **kwargs)
    except Exception as err:
        return str(err)
