import logging
import os
import sys

context = os.environ.get('CONTEXT', 'flask')

if context == 'worker':
    log_format = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )

    if os.environ.get('ENV', 'PROD') == 'DEV':
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    # root_logger = logging.getLogger()

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(log_format)
    # root_logger.addHandler(stdout_handler)

    logging.root.handlers = [stdout_handler]
