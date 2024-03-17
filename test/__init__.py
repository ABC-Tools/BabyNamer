import logging
import sys

if 'unittest' in sys.modules.keys():
    log_format = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )

    logging.basicConfig(level=logging.DEBUG)

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(log_format)

    logging.root.handlers = [stdout_handler]
