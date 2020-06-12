import time
import json
import requests
from bs4 import BeautifulSoup
import re

_http_headers = {'Content-Type': 'application/json'}


class CodeforcesScrapper:

    rating_history_url = 'https://codeforces.com/api/user.rating?handle='

    def get_user_info(self, username):
        try:
            rs = requests.session()
            url = f'http://codeforces.com/api/user.status?handle={username}&from=1&count=1000000'
            submission_list = rs.get(url=url, headers=_http_headers).json()
            submission_list = submission_list['result']

            solved_problems = []

            for submission in submission_list:
                if submission['verdict'] == 'OK' and submission['testset'] == 'TESTS':
                    problem = str(submission['problem']['contestId']) + '/' + str(submission['problem']['index'])
                    if problem not in solved_problems:
                        solved_problems.append(problem)

            return {
                'platform': 'codeforces',
                'user_name': username,
                'solved_count': len(solved_problems),
                'solved_problems': solved_problems
            }
        except Exception as e:
            return {
                'platform': 'codeforces',
                'user_name': username,
                'solved_count': 0,
                'solved_problems': []
            }

    def get_submission_stat(self, username):
        try:
            rs = requests.session()
            url = f'http://codeforces.com/api/user.status?handle={username}&from=1&count=1000'
            submission_list = rs.get(url=url, headers=_http_headers).json()
            submission_list = submission_list['result']

            solved_problems = []
            submission_stat = []

            for submission in submission_list:
                if submission['verdict'] == 'OK' and submission['testset'] == 'TESTS':
                    problem = str(submission['problem']['contestId']) + '/' + str(submission['problem']['index'])
                    if problem not in solved_problems:
                        solved_problems.append(problem)
                        submission_data = {
                            'problem_id': problem,
                            'submission_link': f'https://codeforces.com/contest/{submission["contestId"]}/submission/{submission["id"]}',
                            'verdict': 'accepted',
                            'submission_date': submission['creationTimeSeconds'],
                        }
                        submission_stat.append(submission_data)
            return {
                'platform': 'codeforces',
                'user_name': username,
                'solved_count': len(solved_problems),
                'solved_problems': solved_problems,
                'submission_stat': submission_stat,
            }
        except Exception as e:
            return {
                'platform': 'codeforces',
                'user_name': username,
                'solved_count': 0,
                'solved_problems': [],
                'submission_stat': [],
            }

    def get_user_rating_history(self, username):
        try:
            rs = requests.session()
            url = self.rating_history_url + username
            rating_history = rs.get(url=url, headers=_http_headers).json()
            return rating_history['result']
        except Exception as e:
            return []


if __name__ == '__main__':
    print('START RUNNING CODEFORCES SCRAPPER SCRIPT\n')
    codeforces_scrapper = CodeforcesScrapper()
    resp = codeforces_scrapper.get_submission_stat('flash_7')
    print(json.dumps(resp))
