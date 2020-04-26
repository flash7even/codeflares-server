import logging
import re, json
from logging.handlers import TimedRotatingFileHandler

import pandas as pd
import numpy as np
import requests

logger = logging.getLogger('category dependency uploader logger')
logger.setLevel(logging.DEBUG)
handler = TimedRotatingFileHandler('category_dependency_uploader.log', when='midnight', interval=1,  backupCount=30)
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


def add_category_dependency(data):
    url = "http://192.168.0.30:5056/training/category/dependency"
    response = rs.post(url=url, json=data, headers=_http_headers).json()
    logger.debug('response: ' + json.dumps(response))


def category_dependency_extract():
    data = pd.read_csv("../datasets/category-list - algorithm-links.csv")
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
    logger.info('FINISHED RUNNING CATEGORY DEPENDENCY UPLOADER SCRIPT\n')





