import time
import json
import requests
import os
from bs4 import BeautifulSoup
import re

rs = requests.session()
_http_headers = {'Content-Type': 'application/json'}


ADMIN_USER = os.getenv('ADMIN_USERNAME')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')
SERVER_HOST = 'http://localhost:5056/api'

access_token = None
login_api = f'{SERVER_HOST}/auth/login'
add_problem_url = f'{SERVER_HOST}/problem/'


def get_access_token():
    try:
        global rs
        login_data = {
            "username": ADMIN_USER,
            "password": ADMIN_PASSWORD
        }
        response = rs.post(url=login_api, json=login_data, headers=_http_headers).json()
        return response['access_token']
    except Exception as e:
        raise Exception('Internal server error')


def get_header():
    try:
        global rs
        global access_token
        if access_token is None:
            access_token = get_access_token()
        auth_headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }
        return auth_headers
    except Exception as e:
        raise Exception('Internal server error')


def add_problem(problem_data):
    try:
        global rs
        auth_header = get_header()
        response = rs.post(url=add_problem_url, json=problem_data, headers=auth_header).json()
        print('response: ', response)
    except Exception as e:
        print(f'Exception: {e}')



oj_map = {
    "SPOJ": "spoj",
    "CodeChef": "codechef",
    "Codeforces": "codeforces"
}


def update_difficulties(problem_list, min_diff):
    total = len(problem_list)
    diff_range = 10.0 - float(min_diff)
    dx = diff_range/total

    cur_diff = min_diff
    for problem in problem_list:
        problem['problem_difficulty'] = cur_diff
        cur_diff += dx
        if cur_diff > 10:
            cur_diff = 10


def get_problem_id(source_link, oj_name):
    if source_link.endswith('/') is False:
        source_link += '/'

    words = source_link.split("/")
    if oj_name == 'codeforces':
        problem_id = words[len(words)-3] + '/' + words[len(words)-2]
    else:
        problem_id = words[len(words)-2]
    return problem_id


class A2ojScrapper:

    def upload_problem_history(self, algorithm_id, algorithm_name, min_diff):
        print(f'upload_problem_history called, algorithm_name: {algorithm_name}, min_diff: {min_diff}')
        rs = requests.session()
        url = f'https://a2oj.com/category?ID={algorithm_id}'
        submission_page = rs.get(url=url, headers=_http_headers)
        soup = BeautifulSoup(submission_page.text, 'html.parser')
        soup.prettify()

        problem_list = []
        table = soup.find("table",{"class":"tablesorter"})

        for row in table.find_all("tr")[1:]:  # skipping header row
            cells = row.find_all("td")
            problem_name = cells[1].text
            oj_name = cells[3].text
            problem_difficulty = cells[6].text
            source_link = cells[1].find('a').get('href')

            if oj_name not in oj_map:
                continue

            oj_name = oj_map[oj_name]

            if oj_name == "codeforces":
                if "gym" in source_link:
                    continue

            problem_id = get_problem_id(source_link, oj_name)

            problem_data = {
                "problem_name": problem_name,
                "problem_id": problem_id,
                "problem_description": "NA",
                "problem_difficulty": problem_difficulty,
                "problem_significance": 1,
                "source_link": str(source_link),
                "category_dependency_list": [],
                "oj_name": oj_name,
                "active_status": "pending"
            }

            problem_data['category_dependency_list'].append(
                {
                    'category_name': algorithm_name,
                    'factor': 7.5
                }
            )
            problem_list.append(problem_data)

        update_difficulties(problem_list, min_diff)

        for problem in problem_list:
            add_problem(problem)

        return {
            "problem_list": problem_list
        }


if __name__ == '__main__':
    print('START RUNNING CODECHEF SCRAPPER SCRIPT\n')
    a2oj_scrapper = A2ojScrapper()
    a2oj_scrapper.upload_problem_history(25, 'segment_tree', 4.0)
