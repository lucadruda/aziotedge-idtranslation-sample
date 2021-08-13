from os import getenv
from colorama import init # for Windows

MODULE_NAME = 'PROVISIONING MODULE'
RESET = '\033[0m'  # white (normal)
R = '\033[31m'  # red
G = '\033[32m'  # green
Y = '\033[33m'  # yellow
B = '\033[34m'  # blue
P = '\033[35m'  # purple

LOG_LEVEL = getenv('RuntimeLogLevel', 'info')

init() # no-op for non-Windows OS


def info(msg: str):
    print('[{}]-[INFO] - {}'.format(MODULE_NAME, msg))


def warn(msg: str):
    print(Y+'[{}]-[WARN] - {}'.format(MODULE_NAME, msg)+RESET)


def debug(msg: str):
    if LOG_LEVEL == 'debug':
        print(B+'[{}]-[DEBUG] - {}'.format(MODULE_NAME, msg), RESET)


def error(msg: str):
    print(R+'[{}]-[ERR] - {}'.format(MODULE_NAME, msg)+RESET)
