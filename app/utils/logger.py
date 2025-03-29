import logging
import os
from colorama import Fore

COLORS = [
    Fore.LIGHTRED_EX,
    Fore.LIGHTGREEN_EX,
    Fore.LIGHTYELLOW_EX,
    Fore.LIGHTBLUE_EX,
    Fore.LIGHTMAGENTA_EX,
    Fore.LIGHTCYAN_EX,
    Fore.LIGHTWHITE_EX,
    Fore.LIGHTBLACK_EX,
]


class Logger:
    def __init__(self, name):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        self.pid = os.getpid()
        color = COLORS[self.pid % len(COLORS)]
        formatter = logging.Formatter(
            f"{color}[%(asctime)s] {self.pid} {Fore.GREEN}%(levelname)s {Fore.WHITE}%(name)s {Fore.YELLOW}%(message)s"
        )
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        self.logger.addHandler(stream_handler)

    def log(self, level, msg, details=None):
        self.logger.setLevel(level)
        if details:
            self.logger.log(level, f"{msg} | Details: {details}")
        else:
            self.logger.log(level, msg)

    def info(self, msg, details=None):
        self.log(logging.INFO, msg, details)

    def debug(self, msg, details=None):
        self.log(logging.DEBUG, msg, details)

    def warning(self, msg, details=None):
        self.log(logging.WARNING, msg, details)

    def error(self, msg, details=None):
        self.log(logging.ERROR, msg, details)

    def critical(self, msg, details=None):
        self.log(logging.CRITICAL, msg, details)

    def get_logger(self):
        return self.logger
