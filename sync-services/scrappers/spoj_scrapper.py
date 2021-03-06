import time
import json
import requests
from bs4 import BeautifulSoup
import re

_http_headers = {'Content-Type': 'application/json'}


class SpojScrapper:

    def get_user_info_heavy(self, username):
        try:
            rs = requests.session()
            url = f'http://www.spoj.com/users/{username}'
            profile_page = rs.get(url=url, headers=_http_headers)
            soup = BeautifulSoup(profile_page.text, 'html.parser')
            solved_problems = {}
            contentTable = soup.find('table', {"class": "table-condensed"})
            for link in contentTable.findAll('a'):
                try:
                    problem_name = link.string
                    if problem_name is not None:
                        problem_data = {
                            'problem_id': problem_name,
                            'submission_list': [
                                {
                                    'submission_link': f'https://www.spoj.com/status/{problem_name},{username}/'
                                }
                            ]
                        }
                        solved_problems[problem_name] = problem_data
                except Exception as e:
                    print(f'Exception occurred while parsing uva data for user: {username}, submission: {sub}, exception: {e}')
                    continue
            return solved_problems
        except Exception as e:
            print(f'Error occurred: {e}')
            return {}
