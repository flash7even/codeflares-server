import logging
import os
import re
import time
import json
import unittest
import requests
from logging.handlers import TimedRotatingFileHandler

from apscheduler.schedulers.background import BackgroundScheduler


logger = logging.getLogger('sync job logger')
logger.setLevel(logging.DEBUG)
handler = TimedRotatingFileHandler('../logs/sync_job.log', when='midnight', interval=1,  backupCount=30)
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter(
    fmt='[%(asctime)s.%(msecs)03d] [%(levelname)s]: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))
handler.suffix = "%Y%m%d"
handler.extMatch = re.compile(r"^\d{8}$")
logger.addHandler(handler)

rs = requests.session()
_http_headers = {'Content-Type': 'application/json'}


ADMIN_USER = 'flash_7'
ADMIN_PASSWORD = '123456'
access_token = None
login_api = "http://localhost:5056/api/auth/login"
user_probem_sync_api = "http://localhost:5056/api/user/sync/problem-data/"
user_training_model_sync_api = "http://localhost:5056/api/user/sync/training-model/"
team_training_model_sync_api = "http://localhost:5056/api/team/sync/training-model/"
job_search_url = "http://localhost:5056/api/job/search"
job_url = "http://localhost:5056/api/job/"


def get_access_token():
    login_data = {
        "username": ADMIN_USER,
        "password": ADMIN_PASSWORD
    }
    response = rs.post(url=login_api, json=login_data, headers=_http_headers).json()
    return response['access_token']


def get_header():
    global access_token
    if access_token is None:
        access_token = get_access_token()
    auth_headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    return auth_headers


def user_problem_sync(user_id):
    logging.debug('user_problem_sync called for: ' + str(user_id))
    url = user_probem_sync_api + user_id
    response = rs.put(url=url, json={}, headers=get_header()).json()
    logging.debug('response: ' + str(response))


def user_training_model_sync(user_id):
    logging.debug('user_training_model_sync called for: ' + str(user_id))
    url = user_training_model_sync_api + user_id
    response = rs.put(url=url, json={}, headers=get_header()).json()
    logging.debug('response: ' + str(response))


def team_training_model_sync(team_id):
    logging.debug('team_training_model_sync called for: ' + str(team_id))
    url = team_training_model_sync_api + team_id
    response = rs.put(url=url, json={}, headers=get_header()).json()
    logging.debug('response: ' + str(response))


def search_job():
    logging.debug('search_job called')
    response = rs.post(url=job_search_url, json={'status': 'PENDING'}, headers=get_header()).json()
    logging.debug('response: ' + str(response))
    return response['job_list']


def update_job(job_id, status):
    logging.debug('update_job called')
    url = job_url + job_id
    response = rs.put(url=url, json={'status': status}, headers=get_header()).json()
    logging.debug('response: ' + str(response))


def db_job():
    curtime = int(time.time())
    logging.info('RUN CRON JOB FOR SYNCING DATA AT: ' + str(curtime))
    while(1):
        pending_job_list = search_job()
        if len(pending_job_list) == 0:
            break
        cur_job = pending_job_list[0]
        logging.debug('PROCESS JOB: ' + json.dumps(cur_job))
        update_job(cur_job['id'], 'PROCESSING')
        if cur_job['job_type'] == 'USER_SYNC':
            user_problem_sync(cur_job['job_ref_id'])
            user_training_model_sync(cur_job['job_ref_id'])
        else:
            team_training_model_sync(cur_job['job_ref_id'])

        update_job(cur_job['id'], 'COMPLETED')
        logging.debug('COMPLETED JOB: ' + json.dumps(cur_job))


cron_job = BackgroundScheduler(daemon=True)
cron_job.add_job(db_job, 'interval', seconds=30)
cron_job.start()


if __name__ == '__main__':
    logging.info('Sync Job Script successfully started running')
    print('Sync Job Script successfully started running')
    while(1):
        x = 1