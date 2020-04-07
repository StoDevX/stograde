import logging
from os import path

from ..common import run


def clone_student(student: str, base_url: str):
    logging.debug("Cloning {}'s repository".format(student))
    if not path.exists(student):
        clone_url('{}/{}.git'.format(base_url, student))


def clone_url(url: str, into: str = None):
    if into:
        logging.info('cloning {} into {}'.format(url, into))
        _, output, _ = run(['git', 'clone', '--quiet', url, into])
    else:
        logging.info('cloning {}'.format(url))
        _, output, _ = run(['git', 'clone', '--quiet', url])
    logging.debug(output)
