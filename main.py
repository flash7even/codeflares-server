import logging
import os
import re
import time
import json
import unittest
from logging.handlers import TimedRotatingFileHandler

from flask_script import Manager

from apis import Config, create_app

app = create_app(os.getenv('FLASK_ENV', 'development'))

app.app_context().push()
manager = Manager(app)

handler = TimedRotatingFileHandler('./logs/cfs_server.log', when='midnight', interval=1,  backupCount=30)
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter(
    fmt='[%(asctime)s.%(msecs)03d] [%(levelname)s]: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))
handler.suffix = "%Y%m%d"
handler.extMatch = re.compile(r"^\d{8}$")
app.logger.addHandler(handler)


@manager.command
def run():
    app.run(host='0.0.0.0', port=5056)


@manager.command
def test():
    tests = unittest.TestLoader().discover(f'{Config.BASEDIR}/test', pattern='test*.py')
    result = unittest.TextTestRunner(verbosity=2).run(tests)
    if result.wasSuccessful():
        return 0
    return 1


if __name__ == '__main__':
    app.logger.info('Server successfully started running')
    manager.run()
