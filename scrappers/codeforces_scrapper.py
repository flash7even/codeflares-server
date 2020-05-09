import time
import json
import requests
from bs4 import BeautifulSoup
import re

_http_headers = {'Content-Type': 'application/json'}


class CodeforcesScrapper:

    rating_history_url = 'https://codeforces.com/api/user.rating?handle='

    def get_user_info(self, username):
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

    def get_user_rating_history(self, username):
        rs = requests.session()
        url = self.rating_history_url + username
        rating_history = rs.get(url=url, headers=_http_headers).json()
        return rating_history['result']


if __name__ == '__main__':
    print('START RUNNING CODEFORCES SCRAPPER SCRIPT\n')
    codeforces_scrapper = CodeforcesScrapper()
    resp = codeforces_scrapper.get_user_info('flash_7')
    print(json.dumps(resp))
