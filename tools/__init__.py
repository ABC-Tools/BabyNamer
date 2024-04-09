import logging
import os
import sys

os.environ["CONTEXT"] = "tools"

log_format = logging.Formatter(
    '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
)

logging.basicConfig(level=logging.DEBUG)

# root_logger = logging.getLogger()

stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setFormatter(log_format)
# root_logger.addHandler(stdout_handler)

logging.root.handlers = [stdout_handler]