import logging
import os

context = os.environ.get('CONTEXT', 'flask')

if context == 'worker':
    if os.environ.get('ENV', 'PROD') == 'DEV':
        logging.basicConfig(format='%(asctime)s %(message)s',
                            level=logging.DEBUG)
    else:
        logging.basicConfig(format='%(asctime)s %(message)s',
                            level=logging.INFO)
