import logging
import os
import re
import time
import json
import unittest
from logging.handlers import TimedRotatingFileHandler

from apscheduler.schedulers.background import BackgroundScheduler
from flask_script import Manager

from apis import Config, create_app

from core.job_services import search_jobs, update_pending_job
from core.job_services import COMPLETED, PROCESSING, PENDING
from core.sync_services import user_problem_data_sync, user_training_model_sync, team_training_model_sync


def db_job():
    curtime = int(time.time())
    with app.app_context():
        app.logger.info('RUN CRON JOB FOR SYNCING DATA AT: ' + str(curtime))
        while(1):
            pending_job_list = search_jobs(PENDING, 1)
            if len(pending_job_list) == 0:
                break
            cur_job = pending_job_list[0]
            app.logger.debug('PROCESS JOB: ' + json.dumps(cur_job))
            update_pending_job(cur_job['id'], PROCESSING)
            if cur_job['job_type'] == 'USER_SYNC':
                user_problem_data_sync(cur_job['job_ref_id'])
                user_training_model_sync(cur_job['job_ref_id'])
            else:
                team_training_model_sync(cur_job['job_ref_id'])
                team_training_model_sync(cur_job['job_ref_id'])

            update_pending_job(cur_job['id'], COMPLETED)
            app.logger.debug('COMPLETED JOB: ' + json.dumps(cur_job))


cron_job = BackgroundScheduler(daemon=True)
cron_job.add_job(db_job, 'interval', seconds=45)
cron_job.start()

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
