import logging
import re
import os
import json
from logging.handlers import TimedRotatingFileHandler

import pandas as pd
import numpy as np
import requests

logger = logging.getLogger('category uploader logger')
logger.setLevel(logging.DEBUG)
handler = TimedRotatingFileHandler('../logs/category_uploader.log', when='midnight', interval=1,  backupCount=30)
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

login_api = "http://localhost:5056/api/auth/login"
ADMIN_USER = os.getenv('ADMIN_USERNAME')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')

ES_HOST = 'localhost:9200'
total_cnt = 0

access_token = None


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


def capitalize_text(name):
    name = str(name)
    words = name.split('_')
    cap_words = []
    for word in words:
        cap_words.append(word.capitalize())
    cap_words = ' '.join(cap_words)
    return cap_words


def add_category(data):
    auth_header = get_header()
    url = "http://localhost:5056/api/category/"
    response = rs.post(url=url, json=data, headers=auth_header).json()
    print('response: ' + json.dumps(response))


def category_extract(data):
    global total_cnt
    data = data.replace({np.nan: None})
    category_cnt = 0
    for i in range(0, len(data)):
        json_data = {
            "category_name": data['category_name'][i],
            "category_title": capitalize_text(data['category_name'][i]),
            "category_root": data['category_root'][i],
            "category_root_title": capitalize_text(data['category_root'][i]),
            "category_difficulty": data['category_difficulty'][i],
            "category_importance": data['category_importance'][i],
            "factor": data['factor'][i],
            "short_name": data['short_name'][i],
            "score_percentage": data['score_percentage'][i]
        }

        for f in json_data:
            json_data[f] = str(json_data[f])

        if json_data['category_root'] != 'sum':
            add_category(json_data)
            category_cnt += 1
            total_cnt += 1

    logger.debug('Category uploaded: ' + str(category_cnt))
    logger.debug('Total count now: ' + str(total_cnt))


def upload_category_datasets():
    dirpath = '../datasets/categories/category-list/'
    for dirpath, dirnames, filenames in os.walk(dirpath):
        for filename in filenames:
            full_filepath = os.path.join(dirpath, filename)
            print('full_filepath: ', full_filepath)
            logger.debug('Category file path: ' + str(full_filepath))
            data = pd.read_csv(full_filepath)
            category_extract(data)


if __name__ == '__main__':
    logger.info('START RUNNING CATEGORY UPLOADER SCRIPT\n')
    upload_category_datasets()
    logger.info('FINISHED RUNNING CATEGORY UPLOADER SCRIPT\n')




