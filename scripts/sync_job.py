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


ADMIN_USER = os.getenv('ADMIN_USERNAME')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')

access_token = None
login_api = "http://localhost:5056/api/auth/login"
user_probem_sync_api = "http://localhost:5056/api/user/sync/problem-data/"
user_training_model_sync_api = "http://localhost:5056/api/user/sync/training-model/"
team_training_model_sync_api = "http://localhost:5056/api/team/sync/training-model/"
job_search_url = "http://localhost:5056/api/job/search"
job_url = "http://localhost:5056/api/job/"


def get_access_token():
    global rs
    login_data = {
        "username": ADMIN_USER,
        "password": ADMIN_PASSWORD
    }
    response = rs.post(url=login_api, json=login_data, headers=_http_headers).json()
    return response['access_token']


def get_header():
    global rs
    global access_token
    if access_token is None:
        access_token = get_access_token()
    auth_headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    return auth_headers


def user_problem_sync(user_id):
    global rs
    auth_header = get_header()
    logger.debug('user_problem_sync called for: ' + str(user_id))
    url = user_probem_sync_api + user_id
    response = rs.put(url=url, json={}, headers=auth_header).json()
    logger.debug('response: ' + str(response))


def user_training_model_sync(user_id):
    global rs
    auth_header = get_header()
    logger.debug('user_training_model_sync called for: ' + str(user_id))
    url = user_training_model_sync_api + user_id
    response = rs.put(url=url, json={}, headers=auth_header).json()
    logger.debug('response: ' + str(response))


def team_training_model_sync(team_id):
    global rs
    auth_header = get_header()
    logger.debug('team_training_model_sync called for: ' + str(team_id))
    url = team_training_model_sync_api + team_id
    response = rs.put(url=url, json={}, headers=auth_header).json()
    logger.debug('response: ' + str(response))


def search_job():
    global rs
    auth_header = get_header()
    logger.debug('search_job called')
    print('job_search_url: ', job_search_url)
    print('auth_header: ', auth_header)
    response = rs.post(url=job_search_url, json={'status': 'PENDING'}, headers=auth_header).json()
    logger.debug('response: ' + str(response))
    print(response)
    return response['job_list']


def update_job(job_id, status):
    global rs
    auth_header = get_header()
    logger.debug('update_job called')
    url = job_url + job_id
    response = rs.put(url=url, json={'status': status}, headers=auth_header).json()
    logger.debug('response: ' + str(response))


def db_job():
    curtime = int(time.time())
    logger.info('RUN CRON JOB FOR SYNCING DATA AT: ' + str(curtime))
    while(1):
        pending_job_list = search_job()
        if len(pending_job_list) == 0:
            break
        cur_job = pending_job_list[0]
        logger.debug('PROCESS JOB: ' + json.dumps(cur_job))
        update_job(cur_job['id'], 'PROCESSING')
        if cur_job['job_type'] == 'USER_SYNC':
            user_problem_sync(cur_job['job_ref_id'])
            # user_training_model_sync(cur_job['job_ref_id'])
        else:
            team_training_model_sync(cur_job['job_ref_id'])

        update_job(cur_job['id'], 'COMPLETED')
        logger.debug('COMPLETED JOB: ' + json.dumps(cur_job))


cron_job = BackgroundScheduler(daemon=True)
cron_job.add_job(db_job, 'interval', seconds=15)
cron_job.start()


if __name__ == '__main__':
    logger.info('Sync Job Script successfully started running')
    while(1):
        pass
