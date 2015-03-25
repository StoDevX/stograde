#!/usr/bin/env python3

import sys, os
from run import run
from run_file import run_file
from textwrap import indent

def markdownify(hw_number, username):
	cwd = os.getcwd()
	header = "# %s – %s" % (hw_number, username)

	files = [file for file in os.listdir('.') if file.endswith('.cpp')]
	results = ['\n\n'.join([
		'### %s' % (file),
		'**contents of %s**' % (file),
		indent(run(['cat', file]), '    '),
		'**warnings about %s**' % (file),
		indent(run(['g++-4.8', '--std=c++11', file, '-o', '%s.exec' % (file)]), '    '),
		'**results of %s**' % (file),
		indent(run_file(hw, cwd + '/' + file + '.exec'), '    '),
	]) for file in files]

	[run(['rm', '-f', file + '.exec']) for file in files]

	return '\n'.join(results)


if __name__ == '__main__':
	hw = sys.argv[1]
	user = sys.argv[2]
	print(markdownify(hw, user))
