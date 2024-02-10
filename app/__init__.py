import logging
from logging import handlers
import sys
import os

context = os.environ.get('CONTEXT', 'flask')

if context != 'worker' and 'unittest' not in sys.modules.keys():
    if os.environ.get('ENV', 'PROD') == 'DEV':
        logging.basicConfig(format='%(asctime)s %(message)s',
                            filename='/var/log/flask.log',
                            level=logging.DEBUG)
    else:
        logging.basicConfig(format='%(asctime)s %(message)s',
                            filename='/var/log/flask.log',
                            level=logging.INFO)

    root_logger = logging.getLogger()
    werkzeug_logger = logging.getLogger("werkzeug")  # grabs underlying WSGI logger

    # handler = logging.FileHandler('/var/log/flask.log')  # creates handler for the log file
    handler = logging.handlers.TimedRotatingFileHandler('/var/log/flask.log', when='D')  # creates handler for the log file
    handler.setFormatter("%(asctime)s %(levelname)s %(message)s")

    werkzeug_logger.addHandler(handler)  # adds handler to the werkzeug WSGI logger
    werkzeug_logger.addHandler(logging.StreamHandler(sys.stdout))
    root_logger.addHandler(handler)
    root_logger.addHandler(logging.StreamHandler(sys.stdout))
