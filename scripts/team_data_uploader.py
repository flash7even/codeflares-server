import logging
import os
import re, json
from logging.handlers import TimedRotatingFileHandler
import requests


logger = logging.getLogger('contestant uploader logger')
logger.setLevel(logging.DEBUG)
handler = TimedRotatingFileHandler('../logs/team_uploader.log', when='midnight', interval=1,  backupCount=30)
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


team_list = [
    {
        'id': 100,
        'data': {
            'team_name': 'nsu_vendetta',
            'institution_name': 'NSU',
            'team_purpose': 'ICPC',
            'team_type': 'team',
            'member_list': [
                {
                    'user_handle': 'flash_7'
                },
                {
                    'user_handle': 'Labib666'
                },
                {
                    'user_handle': 'hasib'
                }
            ]
        }
    },
    {
        'id': 101,
        'data': {
            'team_name': 'nsu_aristocrats',
            'institution_name': 'NSU',
            'team_purpose': 'ICPC',
            'team_type': 'team',
            'member_list': [
                {
                    'user_handle': 'flash_7'
                },
                {
                    'user_handle': 'Labib666'
                },
                {
                    'user_handle': 'forthright48'
                }
            ]
        }
    }
]


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


def add_single_team(data):
    logger.info('add_single_team: ' + json.dumps(data))
    access_token = get_access_token()
    auth_headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    s_url = "http://localhost:5056/api/team/"
    response = rs.post(url=s_url, json=data, headers=auth_headers).json()
    logger.info(response)


def add_teams():
    logger.info('Add all the teams')
    for team in team_list:
        add_single_team(team['data'])


if __name__ == '__main__':
    logger.info('START RUNNING CONTESTANT UPLOADER SCRIPT\n')
    add_teams()
    logger.info('FINISHED CONTESTANT UPLOADER SCRIPT\n')
