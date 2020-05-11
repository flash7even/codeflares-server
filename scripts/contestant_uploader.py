import logging
import re, json
from logging.handlers import TimedRotatingFileHandler
import requests


logger = logging.getLogger('contestant uploader logger')
logger.setLevel(logging.DEBUG)
handler = TimedRotatingFileHandler('../logs/contestant_uploader.log', when='midnight', interval=1,  backupCount=30)
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

user_list = [
    {
        "id": "101",
        "data": {
          "username" : "forthright48",
          "full_name" : "Mohammad Samiul Islam",
          "email" : "forthright48@gmail.com",
          "password" : "123456",
          "codeforces_handle" : "forthright48",
          "codechef_handle" : "forthright",
          "spoj_handle" : "forthright48",
          "uva_handle" : "forthright48",
          "lightoj_handle" : "3158",
          "user_role" : "contestant"
        }
    },
    {
        "id": "102",
        "data": {
          "username" : "Labib666",
          "full_name" : "Labib Rashid",
          "email" : "labib@gmail.com",
          "password" : "123456",
          "codeforces_handle" : "Labib666",
          "codechef_handle" : "labib666",
          "spoj_handle" : "labib666",
          "uva_handle" : "Labib666",
          "lightoj_handle" : "3278",
          "user_role" : "contestant"
        }
    },
    {
        "id": "103",
        "data": {
          "username" : "hasib",
          "full_name" : "Hasib Al Muhaimin",
          "email" : "hasib@gmail.com",
          "password" : "123456",
          "codeforces_handle" : "hasib",
          "codechef_handle" : "hasib_mo",
          "spoj_handle" : "hasib",
          "uva_handle" : "php",
          "lightoj_handle" : "4144",
          "user_role" : "contestant"
        }
    }
]

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
                    'user_handle': 'flash_7',
                    'remarks': 'contestant'
                },
                {
                    'user_handle': 'Labib666',
                    'remarks': 'contestant'
                },
                {
                    'user_handle': 'hasib',
                    'remarks': 'contestant'
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
                    'user_handle': 'flash_7',
                    'remarks': 'contestant'
                },
                {
                    'user_handle': 'Labib666',
                    'remarks': 'contestant'
                },
                {
                    'user_handle': 'forthright48',
                    'remarks': 'contestant'
                }
            ]
        }
    }
]

ADMIN_USER = 'flash_7'
ADMIN_PASSWORD = '123456'
login_api = "http://localhost:5056/training/auth/login"


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
    s_url = "http://localhost:5056/training/team/"
    response = rs.post(url=s_url, json=data, headers=auth_headers).json()
    logger.info(response)


def add_teams():
    logger.info('Add all the teams')
    for team in team_list:
        add_single_team(team['data'])


def add_single_user(data):
    logger.info('add_single_user: ' + json.dumps(data))
    s_url = "http://localhost:5056/training/user/"
    response = rs.post(url=s_url, json=data, headers=_http_headers).json()
    logger.info(response)


def add_users():
    logger.info('Add all the users')
    for user in user_list:
        add_single_user(user['data'])


if __name__ == '__main__':
    logger.info('START RUNNING CONTESTANT UPLOADER SCRIPT\n')
    add_users()
    add_teams()
    logger.info('FINISHED CONTESTANT UPLOADER SCRIPT\n')
