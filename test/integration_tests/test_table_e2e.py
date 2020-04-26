import sys
import os
from unittest import mock

import pytest

from stograde.common import chdir
from stograde.toolkit.__main__ import main

_dir = os.path.dirname(os.path.realpath(__file__))

pytest.skip('testing coverage without integration tests', allow_module_level=True)


@pytest.mark.datafiles(os.path.join(_dir, 'fixtures'))
def test_stograde_table(datafiles, capsys):
    args = [sys.argv[0]] + ['table', '--skip-repo-update', '--skip-spec-update', '--skip-version-check',
                            '--skip-dependency-check']

    with chdir(str(datafiles)):
        try:
            with mock.patch('sys.argv', args):
                main()
        except SystemExit:
            pass

    out, err = capsys.readouterr()

    assert out == ("\n"
                   "USER      | 1 | 1 | 1\n"
                   "----------+---+---+--\n"
                   "rives     | - | - | -\n"
                   "student1  | 1 | - | -\n"
                   "student2  | 1 | - | -\n"
                   "student3  | 1 | - | -\n"
                   "student4  | 1 | - | -\n"
                   "student5  | \x1b[1m\x1b[31m1\x1b[0m | - | -\n\n")
