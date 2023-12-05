import logging


werkzeug_logger = logging.getLogger("werkzeug")  # grabs underlying WSGI logger
# root_logger = logging.getLogger()

handler = logging.FileHandler('/var/log/flask.log')  # creates handler for the log file
handler.setFormatter("%(asctime)s %(levelname)s %(message)s")

werkzeug_logger.addHandler(handler)  # adds handler to the werkzeug WSGI logger
# root_logger.addHandler(handler)
