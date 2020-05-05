import logging
import re, json
from logging.handlers import TimedRotatingFileHandler

import pandas as pd
import numpy as np
import requests

logger = logging.getLogger('problem list uploader logger')
logger.setLevel(logging.DEBUG)
handler = TimedRotatingFileHandler('problem_list_uploader.log', when='midnight', interval=1,  backupCount=30)
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

problem_list_names = ["problem-list - ad_hoc.csv", "problem-list - basic_math.csv", "problem-list - implementation.csv", "problem-list - misc.csv",
                      "problem-list - number_theory.csv", "problem-list - number_theory.csv"]


def add_problem_list(data):
    url = "http://localhost:5056/training/problem/"
    response = rs.post(url=url, json=data, headers=_http_headers).json()
    logger.debug('response: ' + json.dumps(response))


def problem_list_extract(data):
    data = data.replace({np.nan: None})
    for i in range(0, len(data)):
        problem_name = data['problem_name'][i]
        problem_id = data['problem_id'][i]
        problem_difficulty = data['problem_difficulty'][i]
        oj_name = data['oj_name'][i]
        source_link = data['source_link'][i]
        if data['problem_significance'][i] is None:
            problem_significance = 1
        else:
            problem_significance = data['problem_significance'][i]
        current_row = data.iloc[i,6:-1]
        #print(current_row)
        #print(problem_name)
        category_dependency_list = []
        for r in current_row:
            if r:
                name, factor = r.split(',')
                dependency_data = {
                    "category_name": name,
                    "factor": factor
                }
                #print(dependency_data)
                category_dependency_list.append(dependency_data)
        json_data = {
            "problem_name": problem_name,
            "problem_difficulty": problem_difficulty,
            "problem_significance": problem_significance,
            "source_link": source_link,
            "problem_id": problem_id,
            "oj_name": oj_name,
            "category_dependency_list": category_dependency_list
        }
        #print(json_data)
        add_problem_list(json_data)


def problem_datasets():
    for file in problem_list_names:
        data = pd.read_csv("../datasets/" + str(file))
        problem_list_extract(data)


if __name__ == '__main__':
    logger.info('START RUNNING CATEGORY DEPENDENCY UPLOADER SCRIPT\n')
    problem_datasets()
    logger.info('FINISHED RUNNING CATEGORY DEPENDENCY UPLOADER SCRIPT\n')





