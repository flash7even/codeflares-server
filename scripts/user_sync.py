import logging
import os
import re, json
from logging.handlers import TimedRotatingFileHandler
import requests


logger = logging.getLogger('user sync logger')
logger.setLevel(logging.DEBUG)
handler = TimedRotatingFileHandler('../logs/user_sync.log', when='midnight', interval=1,  backupCount=30)
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
login_api = "http://localhost:5056/api/auth/login"


def get_access_token():
    login_data = {
        "username": ADMIN_USER,
        "password": ADMIN_PASSWORD
    }
    response = rs.post(url=login_api, json=login_data, headers=_http_headers).json()
    return response['access_token']


def get_all_users():
    logger.info('get_all_users called')
    access_token = get_access_token()
    auth_headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    s_url = "http://localhost:5056/api/user/search"
    response = rs.post(url=s_url, json={}, headers=auth_headers).json()
    user_list = response.get('user_list', [])
    logger.debug( f'user_list: {json.dumps(user_list)}')
    return user_list


def sync_user_data(user_id):
    logger.info(f'problem_sync: {user_id}')
    access_token = get_access_token()
    auth_headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    url = f'http://localhost:5056/api/user/sync/{user_id}'
    response = rs.put(url=url, json={}, headers=auth_headers).json()
    logger.debug(f'response: {json.dumps(response)}')


def sync_all_users():
    logger.info('Add all the users')
    user_list = get_all_users()
    for user in user_list:
        user_id = user['id']
        sync_user_data(user_id)


if __name__ == '__main__':
    logger.info('START RUNNING USER SYNC UPLOADER SCRIPT\n')
    sync_all_users()
    logger.info('FINISHED USER SYNC UPLOADER SCRIPT\n')
