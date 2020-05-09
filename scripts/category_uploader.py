import logging
import re
import json
from logging.handlers import TimedRotatingFileHandler

import pandas as pd
import numpy as np
import requests

logger = logging.getLogger('category uploader logger')
logger.setLevel(logging.DEBUG)
handler = TimedRotatingFileHandler('category_uploader.log', when='midnight', interval=1,  backupCount=30)
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

ES_HOST = 'localhost:9200'


def capitalize_text(name):
    words = name.split('_')
    cap_words = []
    for word in words:
        cap_words.append(word.capitalize())
    cap_words = ' '.join(cap_words)
    return cap_words


def add_category(data):
    url = "http://localhost:5056/training/category/"
    response = rs.post(url=url, json=data, headers=_http_headers).json()
    logger.debug('response: ' + json.dumps(response))


def category_extract():
    data = pd.read_csv("../datasets/categories/category-list - algorithms.csv")
    data = data.replace({np.nan: None})
    for i in range(0, len(data)):
        if data['category_root'][i]:
            category_root = data['category_root'][i]
            root_json = {
                "category_name": category_root,
                "category_title": capitalize_text(category_root),
                "category_root": 'root',
                "category_root_title": 'Root',
                "category_difficulty": 0,
                "category_importance": 10
            }
            add_category(root_json)
        json_data = {
            "category_name": data['category_name'][i],
            "category_title": capitalize_text(data['category_name'][i]),
            "category_root": category_root,
            "category_root_title": capitalize_text(category_root),
            "category_difficulty": data['category_difficulty'][i],
            "category_importance": data['category_importance'][i]
        }
        add_category(json_data)

    print(len(data))
    print()

if __name__ == '__main__':
    logger.info('START RUNNING CATEGORY UPLOADER SCRIPT\n')
    category_extract()
    logger.info('FINISHED RUNNING CATEGORY UPLOADER SCRIPT\n')







