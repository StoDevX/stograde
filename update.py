#!/usr/bin/env python3

import os
import sys
import shutil
import textwrap
import datetime
import functools
import lib.yaml as yaml
from argparse import ArgumentParser
from concurrent.futures import ProcessPoolExecutor
from lib.find_unmerged_branches import find_unmerged_branches_in_cwd
from lib.format_collected_data import format_collected_data
from lib.progress import progress as progress_bar
from lib.get_students import get_students
from lib.markdownify import markdownify
from lib.run import run_command as run
from lib.columnize import columnize
from lib.flatten import flatten
from lib.size import size

stogit = 'git@stogit.cs.stolaf.edu:sd-s16'
labnames = {
    'sound': ['lab2', 'lab3'],
    'images': ['lab4', 'lab5', 'lab6'],
}


def check_for_tookit_updates():
    with open('.cs251toolkitrc.yaml', 'a+') as config_file:
        try:
            contents = config_file.read()
        except OSError as err:
            warn(err)
            return

        if not contents:
            contents = '%YAML 1.2\n---\n'

        config = yaml.safe_load(contents)

        if not config:
            config = {}

    now = datetime.datetime.utcnow()
    one_hour = datetime.timedelta(hours=1)

    last_checked = config.get('last checked', now)
    local_hash = config.get('local hash', None)
    remote_hash = config.get('remote hash', None)
    remote_is_local = config.get('remote hash exists locally', False)

    # don't bother checking more than once an hour
    if now and (now - last_checked) < one_hour:
        return

    if not local_hash:
        _, local_hash = run(['git', 'rev-parse', 'master'])
        local_hash = local_hash.strip()

    if not remote_hash:
        _, remote_hash = run(['git', 'ls-remote', 'origin', 'master'])
        remote_hash = remote_hash.split()[0]

    if not remote_is_local:
        _, remote_is_local = run(['git', 'show', '--oneline', '--no-patch', remote_hash])
        remote_is_local = 'fatal' in remote_is_local

    if local_hash != remote_hash and not remote_is_local:
        warn('there is a toolkit update!')
        warn('a simple `git pull` should bring you up-to-date.')

    config['last checked'] = last_checked
    config['local hash'] = local_hash
    config['remote hash'] = remote_hash
    config['remote hash exists locally'] = remote_is_local

    with open('.cs251toolkitrc.yaml', 'w') as config_file:
        header = '%YAML 1.2\n---\n'
        contents = yaml.safe_dump(config, default_flow_style=False)
        config_file.write(header + contents)


def warn(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def record_single_recording(results, output_file):
    str_results = format_collected_data(results)
    # str_results = '---\n' + yaml.dump(results)
    try:
        output_file.write(str_results)
    except Exception as err:
        warn('error! could not write recording:', err)


def record_recordings(records, files):
    for name, recording in records.items():
        if name in files:
            record_single_recording(recording, files[name])


def get_args():
    parser = ArgumentParser(description='The core of the CS251 toolkit.')
    parser.add_argument('--quiet', '-q', action='store_true',
                        help='Be quieter')
    parser.add_argument('--no-update', '-n', action='store_true',
                        help='Do not update the student folders before checking.')
    parser.add_argument('--no-check', '-c', action='store_true',
                        help='Do not check for unmerged branches.')
    parser.add_argument('--day', action='store',
                        help='Check out the student folder as of 5pm on the last <day of week>.')
    parser.add_argument('--date', action='store',
                        help='Check out the student folder as of 5pm on <date> (Y-M-D).')
    parser.add_argument('--clean', action='store_true',
                        help='Remove student folders and re-clone them')
    parser.add_argument('--record', action='append', nargs='+', metavar='HW',
                        help="Record information on student submissions. Requires a spec file.")
    parser.add_argument('--students', action='append', nargs='+', metavar='STUDENT',
                        help='Only iterate over these students.')
    parser.add_argument('--section', action='append', nargs='+', metavar='SECTION',
                        help='Only check these sections: my, all, a, b, etc.')
    parser.add_argument('--sort-by', action='store', default='name', type=str,
                        choices=['name', 'homework'],
                        help='Sort by either student name or homework count.')
    parser.add_argument('--all', action='store_true',
                        help='Shorthand for \'--section all\'')
    parser.add_argument('--workers', '-w', type=int, default=4,
                        help='Control the number of operations to perform in parallel')
    return vars(parser.parse_args())


def process_args():
    students = get_students()
    args = get_args()

    # argparser puts it into a nested list because you could have two
    # occurrences of the arg, each with a variable number of arguments.
    # `--students amy max --students rives` => `[[amy, max], [rives]]`
    args['students'] = list(flatten(args['students'] or []))
    args['section'] = list(flatten(args['section'] or []))
    args['record'] = list(flatten(args['record'] or []))

    if args['all']:
        args['section'] = ['all']

    # fall back to the students.my section
    if not args['students'] and not args['section']:
        args['section'] = ['my']

    # support 'my' students and 'all' students
    if 'my' in args['section']:
        if 'my' not in students:
            warn('There is no [my] section in students.txt')
            return
        args['students'] = students['my']

    elif 'all' in args['section']:
        sections = [students[section] for section in students]
        args['students'] = list(flatten(sections))

    # sections are identified by only being one char long
    elif args['section']:
        sections = []
        for section in args['section']:
            try:
                sections.append(students['section-' + section] or students[section])
            except KeyError:
                warn('Section "%s" could not be found in ./students.txt' % section)
        args['students'] = list(flatten(sections))

    # we can only read one stdin
    if '-' in args['students']:
        args['students'] = flatten(args['students'] + sys.stdin.read().splitlines())
        args['students'] = [student for student in args['students'] if student != '-']

    elif '-' in args['record']:
        args['record'] = flatten(args['record'] + sys.stdin.read().splitlines())
        args['record'] = [to_record for to_record in args['record'] if to_record != '-']

    # stop if we still don't have any students
    if not args['students']:
        msg = textwrap.dedent('''
            Could not find a list of students.
            You must provide the `--students` argument, the `--section` argument,
            a ./students.txt file, or a list of usernames to stdin.
        ''')
        warn(textwrap.fill(msg))
        return

    args['students'] = sorted(set(args['students']))

    if args['day']:
        _, args['day'] = run(['date', '-v1w', '-v-' + args['day'], '+%Y-%m-%d'])
    elif args['date']:
        args['day'] = args['date']

    return args


def single_student(student, args={}, specs={}):
    if args['clean']:
        # progress('cleaning')
        shutil.rmtree(student)

    if not os.path.exists(student):
        # progress('cloning')
        git_clone = ['git', 'clone', '--quiet', '{}/{}.git'.format(stogit, student)]
        run(git_clone)

    os.chdir(student)

    retval = ''
    recordings = {}

    try:
        # progress('stashing')
        if not args['no_update'] and run('git status --porcelain'.split())[1]:
            run(['git', 'stash', '-u'])
            run(['git', 'stash', 'clear'])

        if not args['no_update']:
            # progress('updating')
            run(['git', 'pull', '--quiet', 'origin', 'master'])

        if args['day']:
            # progress('checkouting')
            rev_list = ['git', 'rev-list', '-n', '1', '--before="%s 18:00"' % args['day'], 'master']
            _, rev = run(rev_list)
            run(['git', 'checkout', rev, '--force', '--quiet'])

        if args['no_check']:
            unmerged_branches = None
        else:
            unmerged_branches = find_unmerged_branches_in_cwd()

        all_folders = [folder
                       for folder in os.listdir('.')
                       if not folder.startswith('.') and os.path.isdir(folder)]

        filtered = [f for f in all_folders if size(f) > 100]
        FOLDERS = sorted([f.lower() for f in filtered])
        FOLDERS = list(flatten([(labnames[f] if f in labnames else f) for f in FOLDERS]))
        HWS = {f: f.startswith('hw') for f in FOLDERS}
        LABS = {f: f.startswith('lab') for f in FOLDERS}

        if args['record']:
            for to_record in args['record']:
                # progress('recording %s' % to_record)
                if os.path.exists(to_record):
                    os.chdir(to_record)
                    recording = markdownify(to_record, student, specs[to_record])
                    os.chdir('..')
                else:
                    recording = {
                        'spec': to_record,
                        'student': student,
                        'warnings': {
                            'no submission': True
                        },
                    }

                recordings[to_record] = recording

        retval = "{}\t{}\t{}".format(
            student + ' !' if unmerged_branches else student,
            ' '.join([hw for hw, result in HWS.items() if result]),
            ' '.join([lab for lab, result in LABS.items() if result]))

        if args['day']:
            run(['git', 'checkout', 'master', '--quiet', '--force'])

    except Exception as err:
        retval = "{}: {}".format(student, err)

    os.chdir('..')

    return student, retval, recordings


def main():
    check_for_tookit_updates()
    args = process_args()

    if args['day']:
        print('Checking out %s at 5:00pm' % args['day'])

    table_rows = []
    root = os.getcwd()

    recording_files = {}
    specs = {}
    if args['record']:
        for to_record in args['record']:
            filename = os.path.join('logs', 'log-' + to_record)
            recording_files[to_record] = open(filename + '.md', 'w')
            with open(os.path.join(root, 'specs', to_record + '.yaml'), 'r') as specfile:
                spec = specfile.read()
                if spec:
                    specs[to_record] = yaml.load(spec)

    os.makedirs('./students', exist_ok=True)
    os.chdir('./students')

    try:
        def progress(i, student):
            progress_bar(len(args['students']), i, message='%s' % student)

        single = functools.partial(single_student, args=args, specs=specs)

        # start the progress bar!
        students_left = set(args['students'])
        progress(0, ', '.join(students_left))

        if args['workers'] > 1:
            with ProcessPoolExecutor(max_workers=args['workers']) as pool:
                jobs = pool.map(single, args['students'])
                for i, (student, row, records) in enumerate(jobs):
                    students_left.remove(student)
                    progress(i+1, ', '.join(students_left))
                    table_rows.append(row)
                    record_recordings(records, recording_files)

        else:
            jobs = map(single, args['students'])
            for i, (student, row, records) in enumerate(jobs):
                students_left.remove(student)
                progress(i+1, ', '.join(students_left))
                table_rows.append(row)
                record_recordings(records, recording_files)

    finally:
        [recording.close() for recording in recording_files.values()]
        os.chdir(root)

    if not args['quiet']:
        print('\n' + columnize(table_rows, sort_by=args['sort_by']))


if __name__ == '__main__':
    main()
