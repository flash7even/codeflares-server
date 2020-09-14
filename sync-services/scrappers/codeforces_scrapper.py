import time
import json
import requests
from bs4 import BeautifulSoup
import re

_http_headers = {'Content-Type': 'application/json'}


class CodeforcesScrapper:

    rating_history_url = 'https://codeforces.com/api/user.rating?handle='

    def get_user_info_heavy(self, username):
        try:
            rs = requests.session()
            url = f'http://codeforces.com/api/user.status?handle={username}&from=1&count=1000000'
            submission_list = rs.get(url=url, headers=_http_headers).json()
            submission_list = submission_list['result']
            cf_solved_problems = {}

            for submission in submission_list:
                try:
                    if 'verdict' not in submission or 'testset' not in submission:
                        continue
                    if submission['verdict'] == 'OK' and submission['testset'] == 'TESTS':
                        problem = str(submission['problem']['contestId']) + '/' + str(submission['problem']['index'])
                        if problem not in cf_solved_problems:
                            problem_data = {
                                'problem_id': problem,
                                'submission_list': []
                            }
                            cf_solved_problems[problem] = problem_data

                        sublink = {
                            'submission_time': int(submission['creationTimeSeconds']),
                            'submission_link': f'https://codeforces.com/contest/{submission["contestId"]}/submission/{submission["id"]}',
                            'submission_id': submission["id"]
                        }
                        cf_solved_problems[problem]['submission_list'].append(sublink)
                except Exception as e:
                    print(f'Exception occurred while parsing uva data for user: {username}, submission: {submission}, exception: {e}')
                    continue
            return cf_solved_problems
        except Exception as e:
            print(f'Error occurred: {e}')
            return {}
