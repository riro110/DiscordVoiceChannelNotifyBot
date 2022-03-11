import argparse
import logging

from . import notifybot


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--loglevel', choices=('DEBUG',
                                               'INFO', 'WARNING', 'ERROR', 'CRITICAL'), default='INFO')
    args = parser.parse_args()
    return args


args = parse_args()
logger = logging.getLogger(__name__)

loglevel = getattr(logging, args.loglevel)

FORMAT = "[%(asctime)s] %(name)s %(levelname)s: %(message)s"
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
logging.basicConfig(level=loglevel, format=FORMAT, datefmt=DATE_FORMAT)

notifybot.main()
