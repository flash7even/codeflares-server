import argparse
import logging
import os
import json
import time
import re
import pandas as pd
import numpy as np
from hashlib import md5
import requests

import logging
from logging.handlers import TimedRotatingFileHandler

logger = logging.getLogger('contest con fig logger')
logger.setLevel(logging.DEBUG)
handler = TimedRotatingFileHandler('../logs/contest_config.log', when='midnight', interval=1, backupCount=30)
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

_es_index = 'cfs_contest_configs'
_es_type = '_doc'


def post_data(data):
    print(data)
    url = f'http://{ES_HOST}/{_es_index}/_doc'
    response = rs.post(url=url, json=data, headers=_http_headers).json()
    logger.debug(f'Create response: {response}')
    print(response)


def upload_configs(full_filepath):
    data = pd.read_csv(full_filepath)
    data = data.replace({np.nan: None})
    for i in range(0, len(data)):
        category_name = data['category_name'][i]

        for x in range(1, 11):
            level = str(x)
            if x < 10:
                level = '0' + str(x)
            dif_title = 'dif_' + level
            cnt_title = 'cnt_' + level

            dif_range = data[dif_title][i]
            dif_range = dif_range.split('-')
            cnt_range = data[cnt_title][i]
            cnt_range = cnt_range.split('-')

            cat_level_data = {
                'contest_level': int(x),
                'category_name': str(category_name),
                'minimum_difficulty': float(dif_range[0]),
                'maximum_difficulty': float(dif_range[1]),
                'minimum_problem': int(cnt_range[0]),
                'maximum_problem': int(cnt_range[1]),
            }
            post_data(cat_level_data)


if __name__ == '__main__':
    logger.info('START RUNNING CONTEST CONFIG SCRIPT\n')
    upload_configs('../datasets/contest-config - levels.csv')
    logger.info('FINISH CONTEST CONFIG SCRIPT\n')
