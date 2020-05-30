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

from core.user_services import search_user, get_user_details
from core.team_services import search_teams, get_team_details
from core.sync_services import user_problem_data_sync, user_training_model_sync, team_training_model_sync
from core.rating_services import add_user_ratings


def user_list_sync():
    user_list = search_user({}, 0, 500)
    for user in user_list:
        user_id = user['id']
        user_problem_data_sync(user_id)
        user_training_model_sync(user_id)
        user_details = get_user_details(user_id)
        skill_value = user_details.get('skill_value', 0)
        solve_count = user_details.get('solve_count', 0)
        add_user_ratings(user_id, skill_value, solve_count)


def team_list_sync():
    team_list = search_teams({}, 0, 500)
    for team in team_list:
        team_id = team['id']
        team_training_model_sync(team_id)
        team_details = get_team_details(team_id)
        skill_value = team_details.get('skill_value', 0)
        solve_count = team_details.get('solve_count', 0)
        add_user_ratings(team_id, skill_value, solve_count)


def db_job():
    curtime = int(time.time())
    with app.app_context():
        app.logger.info('RUN CRON JOB FOR SYNCING DATA AT: ' + str(curtime))
        user_list_sync()
        team_list_sync()


cron_job = BackgroundScheduler(daemon=True)
cron_job.add_job(db_job, 'interval', seconds=3600)
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
