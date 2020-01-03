""" We'll create a logger. """

import logging


__all__ = ('LoggingMixin',)


class LoggingMixin:
    """ Logging mixer. """
    def __init__(self, *args, **kwargs):
        # Set up logger
        self.logger = logging.getLogger('discord')
        super().__init__(*args, **kwargs)

    def log_and_print(self, level, msg, *args, **kwargs):
        self.logger.log(level, msg, *args, **kwargs)
        if level >= self.logger.level:
            print(msg % args)

    def log_info(self, msg, *args, **kwargs):
        self.log_and_print(logging.INFO, msg, *args, **kwargs)

    def log_debug(self, msg, *args, **kwargs):
        self.log_and_print(logging.DEBUG, msg, *args, **kwargs)

    def log_warning(self, msg, *args, **kwargs):
        self.log_and_print(logging.WARNING, msg, *args, **kwargs)

    def log_error(self, msg, *args, **kwargs):
        self.log_and_print(logging.ERROR, msg, *args, **kwargs)

    def log_critical(self, msg, *args, **kwargs):
        self.log_and_print(logging.CRITICAL, msg, *args, **kwargs)

    def log_tb(self, ctx, exc):
        self.log_and_print(
            logging.ERROR,
            f'Ignoring exception in command {ctx.command}:',
            exc_info=(exc.__class__, exc, exc.__traceback__)
        )
