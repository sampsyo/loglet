import sys
import logging
sys.path.append('/home/dotcloud/current')
from loglet import app as application
application.logger.addHandler(logging.FileHandler('errors.log'))
application.logger.setLevel(logging.DEBUG)
