import logging
import sys
import os

context = os.environ.get('CONTEXT', 'flask')

if context != 'worker' and 'unittest' not in sys.modules.keys():
    log_format = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )

    if os.environ.get('ENV', 'PROD') == 'DEV':
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    # root_logger = logging.getLogger()
    # werkzeug_logger = logging.getLogger("werkzeug")  # grabs underlying WSGI logger

    file_handler = logging.FileHandler('/var/log/flask.log')  # creates handler for the log file
    # file_handler = logging.handlers.TimedRotatingFileHandler('/var/log/flask.log', when='D')
    file_handler.setFormatter(log_format)
    # werkzeug_logger.addHandler(file_handler)  # adds handler to the werkzeug WSGI logger
    # root_logger.addHandler(file_handler)

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(log_format)
    # werkzeug_logger.addHandler(stdout_handler)
    # root_logger.addHandler(stdout_handler)

    logging.root.handlers = [stdout_handler, file_handler]
