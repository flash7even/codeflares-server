import logging
import re, json
from logging.handlers import TimedRotatingFileHandler
import requests


logger = logging.getLogger('admin uploader logger')
logger.setLevel(logging.DEBUG)
handler = TimedRotatingFileHandler('../logs/admin_uploader.log', when='midnight', interval=1,  backupCount=30)
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
        "id": "100",
        "data": {
          "username" : "flash_7",
          "full_name" : "Tarango Khan",
          "email" : "tarangokhan77@gmail.com",
          "password" : "123456",
          "codeforces_handle" : "flash_7",
          "codechef_handle" : "tarango_khan",
          "spoj_handle" : "tarango_khan",
          "uva_handle" : "flash_7",
          "lightoj_handle" : "14826",
          "user_role" : "contestant"
        }
    }
]


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
    logger.info('START RUNNING ADMIN UPLOADER SCRIPT\n')
    add_users()
