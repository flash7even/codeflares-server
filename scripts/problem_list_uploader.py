import logging
import os
import re, json
from logging.handlers import TimedRotatingFileHandler

import pandas as pd
import numpy as np
import requests

logger = logging.getLogger('problem list uploader logger')
logger.setLevel(logging.DEBUG)
handler = TimedRotatingFileHandler('../logs/problem_list_uploader.log', when='midnight', interval=1,  backupCount=30)
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

approved = 'approved'


def check_existance(problem_id, oj_name):
    try:
        json_data = {}
        json_data["problem_id"] = problem_id
        json_data["oj_name"] = oj_name
        s_url = "http://localhost:5056/api/problem/search/raw/0"
        response = rs.post(url=s_url, json=json_data, headers=_http_headers).json()
        if 'problem_list' in response:
            problem_list = response['problem_list']
            if len(problem_list) > 0:
                return True
        return False
    except Exception as e:
        raise e


def add_problem_list(data, filename):
    try:
        if check_existance(data['problem_id'], data['oj_name']):
            logger.error('PROBLEM ALREADY EXISTS: ' + json.dumps(data) + ' filename: ' + str(filename))
            return

        url = "http://localhost:5056/api/problem/"
        response = rs.post(url=url, json=data, headers=_http_headers).json()
        logger.debug('response: ' + json.dumps(response))
    except Exception as e:
        raise e


def problem_list_extract(data, filename):
    try:
        logger.info('problem_list_extract called for filename: ' + str(filename))
        data = data.replace({np.nan: None})
        for i in range(0, len(data)):
            problem_name = data['problem_name'][i]
            problem_type = data['problem_type'][i]
            problem_id = data['problem_id'][i]
            problem_difficulty = data['problem_difficulty'][i]
            oj_name = data['oj_name'][i]
            source_link = data['source_link'][i]
            if data['problem_significance'][i] is None:
                problem_significance = 1
            else:
                problem_significance = data['problem_significance'][i]
            current_row = data.iloc[i,8:-1]
            category_dependency_list = []
            for category in current_row:
                if category is None:
                    continue
                if category:
                    category = category.replace(" ", "")
                    split_list = category.split(',')
                    if len(split_list) != 2:
                        logger.error('Inconsistent category dependency found for: ' + str(problem_name) + " oj_name: " + str(oj_name) + ' filename: ' + str(filename))
                        continue
                    dependency_data = {
                        "category_name": split_list[0],
                        "factor": split_list[1]
                    }
                    category_dependency_list.append(dependency_data)
                else:
                    logger.error('Category dependency not found for: ' + str(problem_name) + " oj_name: " + str(oj_name) + ' filename: ' + str(filename))
            json_data = {
                "problem_name": str(problem_name),
                "problem_type": str(problem_type),
                "problem_difficulty": float(str(problem_difficulty)),
                "problem_significance": float(str(problem_significance)),
                "source_link": str(source_link),
                "problem_id": str(problem_id),
                "oj_name": str(oj_name),
                "active_status": approved,
                "category_dependency_list": category_dependency_list
            }

            source_link = json_data['source_link']

            if 'spoj' in source_link:
                json_data['oj_name'] = 'spoj'
            elif 'codeforces' in source_link:
                json_data['oj_name'] = 'codeforces'
            elif 'codechef' in source_link:
                json_data['oj_name'] = 'codechef'
            elif 'lightoj' in source_link:
                json_data['oj_name'] = 'lightoj'
            else:
                json_data['oj_name'] = 'uva'

            add_problem_list(json_data, filename)
    except Exception as e:
        raise e


def upload_problem_datasets():
    try:
        dirpath = '../datasets/problems/'
        for dirpath, dirnames, filenames in os.walk(dirpath):
            for filename in filenames:
                full_filepath = os.path.join(dirpath, filename)
                data = pd.read_csv(full_filepath)
                problem_list_extract(data, filename)
    except Exception as e:
        raise e


if __name__ == '__main__':
    try:
        logger.info('START RUNNING CATEGORY DEPENDENCY UPLOADER SCRIPT\n')
        upload_problem_datasets()
        logger.info('FINISHED RUNNING CATEGORY DEPENDENCY UPLOADER SCRIPT\n')
    except Exception as e:
        logger.error('Error occurred: ' + str(e))
