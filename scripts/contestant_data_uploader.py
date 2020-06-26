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
          "user_role" : "admin"
        }
    },
    {
        "id": "102",
        "data": {
          "username" : "Labib666",
          "full_name" : "Labib Rashid",
          "email" : "ewmahadicd@gmail.com",
          "password" : "123456",
          "codeforces_handle" : "Labib666",
          "codechef_handle" : "labib666",
          "spoj_handle" : "labib666",
          "uva_handle" : "Labib666",
          "lightoj_handle" : "3278",
          "user_role" : "admin"
        }
    },
    {
        "id": "103",
        "data": {
          "username" : "hasib",
          "full_name" : "Hasib Al Muhaimin",
          "email" : "himuhasib@gmail.com",
          "password" : "123456",
          "codeforces_handle" : "hasib",
          "codechef_handle" : "hasib_mo",
          "spoj_handle" : "hasib",
          "uva_handle" : "php",
          "lightoj_handle" : "4144",
          "user_role" : "admin"
        }
    },
    {
        "id": "104",
        "data": {
          "username" : "96koushikroy",
          "full_name" : "Koushik Roy",
          "email" : "96koushikroy@gmail.com",
          "password" : "123456",
          "codeforces_handle" : "96koushikroy",
          "codechef_handle" : "koushikroy96",
          "spoj_handle" : "koushikroy96",
          "uva_handle" : "96koushikroy",
          "lightoj_handle" : "27704",
          "user_role" : "admin"
        }
    },
    {
        "id": "105",
        "data": {
          "username" : "aminul",
          "full_name" : "Aminul Haq",
          "email" : "aminulhaq785@gmail.com",
          "password" : "123456",
          "codeforces_handle" : "aminul",
          "codechef_handle" : "aminul_haq",
          "spoj_handle" : "aminul",
          "uva_handle" : "Aminul.Haq",
          "lightoj_handle" : "23051",
          "user_role" : "admin"
        }
    },
    {
        "id": "106",
        "data": {
          "username" : "kimbbakar",
          "full_name" : "Chowdhury Osman",
          "email" : "chowdhuryosman04@gmail.com",
          "password" : "123456",
          "codeforces_handle" : "kimbbakar",
          "codechef_handle" : "kimbbakar",
          "spoj_handle" : "kimbbakar",
          "uva_handle" : "kimbbakar",
          "lightoj_handle" : "9021",
          "user_role" : "admin"
        }
    },
    {
        "id": "107",
        "data": {
          "username" : "discofighter47",
          "full_name" : "Chowdhury Osman",
          "email" : "mdzahidh119@gmail.com",
          "password" : "123456",
          "codeforces_handle" : "DiscoFighter47",
          "codechef_handle" : "discofighter47",
          "spoj_handle" : "discofighter47",
          "uva_handle" : "DiscoFighter47",
          "lightoj_handle" : "30174",
          "user_role" : "admin"
        }
    },
    {
        "id": "108",
        "data": {
          "username" : "anirudha_ani",
          "full_name" : "Anirudha Ani",
          "email" : "anirudhaprasun@gmail.com",
          "password" : "123456",
          "codeforces_handle" : "anirudha",
          "codechef_handle" : "anirudha_ani",
          "spoj_handle" : "anirudha_ani",
          "uva_handle" : "anirudha_paul",
          "lightoj_handle" : "15329",
          "user_role" : "admin"
        }
    },
    {
        "id": "109",
        "data": {
          "username" : "nur_islam",
          "full_name" : "Nur Islam",
          "email" : "nurislam0333@gmail.com",
          "password" : "123456",
          "codeforces_handle" : "nur_islam",
          "codechef_handle" : "nurislam",
          "spoj_handle" : "nurislam",
          "uva_handle" : "nur_islam",
          "lightoj_handle" : "23006",
          "user_role" : "admin"
        }
    },
    {
        "id": "110",
        "data": {
          "username" : "Sherlock221b",
          "full_name" : "Imran Hasan",
          "email" : "imran221b@gmail.com",
          "password" : "123456",
          "codeforces_handle" : "Sherlock221b",
          "codechef_handle" : "imran221b",
          "spoj_handle" : "Sherlock221b",
          "uva_handle" : "Sherlock221b",
          "lightoj_handle" : "8211",
          "user_role" : "admin"
        }
    },
    {
        "id": "111",
        "data": {
          "username" : "Alvee9",
          "full_name" : "Alvee Imam",
          "email" : "abdullah.alvee@gmail.com",
          "password" : "123456",
          "codeforces_handle" : "Alvee9",
          "codechef_handle" : "Alvee9",
          "spoj_handle" : "alvee9",
          "uva_handle" : "Alvee",
          "lightoj_handle" : "28734",
          "user_role" : "admin"
        }
    },
    {
        "id": "112",
        "data": {
          "username" : "nuronial_block",
          "full_name" : "Ahnaf Tahmid Chowdhury",
          "email" : "ahnaf93@gmail.com",
          "password" : "123456",
          "codeforces_handle" : "nuronial_block",
          "codechef_handle" : "leom10",
          "spoj_handle" : "nuronial_block",
          "uva_handle" : "nuronial_block",
          "user_role" : "admin"
        }
    }
]

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


def add_single_user(data):
    logger.info('add_single_user: ' + json.dumps(data))
    s_url = "http://localhost:5056/api/user/"
    response = rs.post(url=s_url, json=data, headers=_http_headers).json()
    logger.info(response)


def add_users():
    logger.info('Add all the users')
    for user in user_list:
        add_single_user(user['data'])


if __name__ == '__main__':
    logger.info('START RUNNING CONTESTANT UPLOADER SCRIPT\n')
    add_users()
    logger.info('FINISHED CONTESTANT UPLOADER SCRIPT\n')
