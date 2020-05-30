import logging
import re, json
from logging.handlers import TimedRotatingFileHandler
import requests


logger = logging.getLogger('team sync logger')
logger.setLevel(logging.DEBUG)
handler = TimedRotatingFileHandler('../logs/team_sync.log', when='midnight', interval=1,  backupCount=30)
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
login_api = "http://localhost:5056/api/auth/login"


def get_access_token():
    login_data = {
        "username": ADMIN_USER,
        "password": ADMIN_PASSWORD
    }
    response = rs.post(url=login_api, json=login_data, headers=_http_headers).json()
    return response['access_token']


def get_all_teams():
    logger.info('get_all_teams called')
    access_token = get_access_token()
    auth_headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    s_url = "http://localhost:5056/api/team/search"
    response = rs.post(url=s_url, json={}, headers=auth_headers).json()
    team_list = response.get('team_list', [])
    logger.debug( f'team_list: {json.dumps(team_list)}')
    return team_list


def sync_team_data(team_id):
    logger.info(f'training_model_sync: {team_id}')
    access_token = get_access_token()
    auth_headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    url = f'http://localhost:5056/api/team/sync/{team_id}'
    response = rs.put(url=url, json={}, headers=auth_headers).json()
    logger.debug(f'response: {json.dumps(response)}')


def sync_all_teams():
    logger.info('Add all the teams')
    team_list = get_all_teams()
    for team in team_list:
        team_id = team['id']
        sync_team_data(team_id)


if __name__ == '__main__':
    logger.info('START RUNNING USER SYNC UPLOADER SCRIPT\n')
    sync_all_teams()
    logger.info('FINISHED USER SYNC UPLOADER SCRIPT\n')
