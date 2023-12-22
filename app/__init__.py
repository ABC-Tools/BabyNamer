import logging
import sys


logging.basicConfig(format='%(asctime)s %(message)s',
                    filename='/var/log/flask.log',
                    level=logging.DEBUG)

root_logger = logging.getLogger()
werkzeug_logger = logging.getLogger("werkzeug")  # grabs underlying WSGI logger


handler = logging.FileHandler('/var/log/flask.log')  # creates handler for the log file
# handler.setFormatter("%(asctime)s %(levelname)s %(message)s")

werkzeug_logger.addHandler(handler)  # adds handler to the werkzeug WSGI logger
werkzeug_logger.addHandler(logging.StreamHandler(sys.stdout))
root_logger.addHandler(handler)
root_logger.addHandler(logging.StreamHandler(sys.stdout))
