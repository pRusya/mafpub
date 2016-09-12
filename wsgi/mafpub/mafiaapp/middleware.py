from django.conf import settings
import logging
import urllib


class CustomLogger(object):
    def __init__(self):
        self.logger = logging.getLogger('custom_logger')
        self.logger.setLevel(logging.INFO)
        filename = settings.CUSTOM_LOGGER_FILENAME or 'custom_logger.log'
        fh = logging.FileHandler(filename=filename)
        fh.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s %(message)s', datefmt='%H:%M:%S')
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)
        self.logger.info('CustomLogger initialized')

    def process_request(self, request):
        message = 'from[{}] method[{}] url[{}] user[{}] agent[{}] data[{}]'.\
            format(request.META['REMOTE_ADDR'], request.method, request.path,
                   request.user, request.META['HTTP_USER_AGENT'], urllib.parse.unquote(request.body.decode('utf-8')))
        self.logger.info(message)
        return None
