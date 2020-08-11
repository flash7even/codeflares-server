import logging
import re, json
import os
from logging.handlers import TimedRotatingFileHandler

import pandas as pd
import numpy as np
import requests

logger = logging.getLogger('category dependency uploader logger')
logger.setLevel(logging.DEBUG)
handler = TimedRotatingFileHandler('../logs/category_dependency_uploader.log', when='midnight', interval=1,  backupCount=30)
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


def add_category_dependency(data):
    auth_header = get_header()
    url = "http://localhost:5056/api/category/dependency"
    response = rs.post(url=url, json=data, headers=auth_header).json()
    logger.debug('response: ' + json.dumps(response))


def category_post_process():
    auth_header = get_header()
    url = "http://localhost:5056/api/category/post-process"
    response = rs.post(url=url, json={}, headers=auth_header).json()
    logger.debug('response: ' + json.dumps(response))


def category_dependency_extract():
    data = pd.read_csv("../datasets/categories/algorithm-links - algorithm-links.csv")
    data = data.replace({np.nan: None})
    for i in range(0, len(data)):
        category_name = data['category_name'][i]
        print(category_name)
        current_row = data.iloc[i,1:-1]
        category_dependency_list = []
        row_len = 0
        for r in current_row:
            if r:
                row_len+=1
                name, factor = r.split(',')
                dependency_data = {
                    "category_name": name,
                    "factor": factor
                }
                #print(dependency_data)
                category_dependency_list.append(dependency_data)
        if row_len == 0:
            logger.warning('No dependency found for category :' + str(category_name))
            continue
        json_data = {
            "category_name": category_name,
            "category_dependency_list": category_dependency_list
        }
        #print(json_data)
        add_category_dependency(json_data)
    #print(len(data))
    #print(data)


if __name__ == '__main__':
    logger.info('START RUNNING CATEGORY DEPENDENCY UPLOADER SCRIPT\n')
    category_dependency_extract()
    category_post_process()
    logger.info('FINISHED RUNNING CATEGORY DEPENDENCY UPLOADER SCRIPT\n')





