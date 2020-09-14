import time
import json
import requests
from bs4 import BeautifulSoup
import re

_http_headers = {'Content-Type': 'application/json'}

class CodechefScrapper:

    def get_user_info_heavy(slef, username, bucket_size):
        try:
            rs = requests.session()
            url = f'https://www.codechef.com/users/{username}'
            profile_page = rs.get(url=url, headers=_http_headers)
            soup = BeautifulSoup(profile_page.text, 'html.parser')

            contentTable = soup.find('article')
            solved_problems = {}

            for link in contentTable.findAll('a', href=True):
                try:
                    problem_name = link.string
                    if problem_name is not None:
                        problem_data = {
                            'problem_id': problem_name,
                            'submission_list': [
                                {
                                    'submission_link': f'https://www.codechef.com{link["href"]}'
                                }
                            ]
                        }
                        solved_problems[problem_name] = problem_data
                        if len(solved_problems) % bucket_size == 0:
                            yield solved_problems
                            solved_problems = {}

                except:
                    print(f'Exception occurred for user: {username}, submission: {link}')
                    continue

            if len(solved_problems) > 0:
                yield solved_problems

        except Exception as e:
            print(f'Error occurred: {e}')
