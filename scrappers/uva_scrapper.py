import time
import json
import requests
from bs4 import BeautifulSoup
import re

_http_headers = {'Content-Type': 'application/json'}


class UvaScrapper:

    def problem_id_name_map(self):
        try:
            rs = requests.session()
            url = f'https://uhunt.onlinejudge.org/api/p'
            data = rs.get(url=url, headers=_http_headers).json()
            map = {}
            for problem in data:
                map[problem[0]] = problem[1]
            return map
        except Exception as e:
            raise e

    def get_user_info(self, username):
        try:
            rs = requests.session()
            url = f'https://uhunt.onlinejudge.org/api/uname2uid/{username}'
            userid = rs.get(url=url, headers=_http_headers).json()

            profile_url = f'https://uhunt.onlinejudge.org/api/subs-user/{userid}'
            problem_map = self.problem_id_name_map()

            profile_data = rs.get(url=profile_url, headers=_http_headers).json()

            problems = []

            all_submissions = profile_data['subs']
            for sub in all_submissions:
                problem_id = problem_map[sub[1]]
                verdict = sub[2]
                if verdict == 90:
                    if problem_id not in problems:
                        problems.append(problem_id)

            return {
                'platform': 'uva',
                'user_name': username,
                'solved_count': len(problems),
                'solved_problems': problems
            }
        except Exception as e:
            return {
                'platform': 'uva',
                'user_name': username,
                'solved_count': 0,
                'solved_problems': []
            }

    def get_user_info_heavy(self, username):
        try:
            rs = requests.session()
            url = f'https://uhunt.onlinejudge.org/api/uname2uid/{username}'
            userid = rs.get(url=url, headers=_http_headers).json()

            profile_url = f'https://uhunt.onlinejudge.org/api/subs-user/{userid}'
            problem_map = self.problem_id_name_map()

            profile_data = rs.get(url=profile_url, headers=_http_headers).json()

            solved_problems = {}

            all_submissions = profile_data['subs']
            for sub in all_submissions:
                problem_id = problem_map[sub[1]]
                verdict = sub[2]
                submission_time = sub[4]
                if verdict == 90:
                    if problem_id not in solved_problems:
                        problem_data = {
                            'problem_id': problem_id,
                            'submission_list': [
                                {
                                    'submission_link': f'https://uhunt.onlinejudge.org/id/{userid}',
                                    'submission_time': submission_time
                                }
                            ]
                        }
                        solved_problems[problem_id] = problem_data

            return {
                'platform': 'uva',
                'user_name': username,
                'solved_count': len(solved_problems),
                'solved_problems': solved_problems
            }
        except Exception as e:
            return {
                'platform': 'uva',
                'user_name': username,
                'solved_count': 0,
                'solved_problems': {}
            }


if __name__ == '__main__':
    print('START RUNNING UVA SCRAPPER SCRIPT\n')
    uva_scrapper = UvaScrapper()
    resp = uva_scrapper.get_user_info_heavy('flash_7')
    print(json.dumps(resp))
