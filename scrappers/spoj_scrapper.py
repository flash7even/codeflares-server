import time
import json
import requests
from bs4 import BeautifulSoup
import re

_http_headers = {'Content-Type': 'application/json'}


class SpojScrapper:

    def get_user_info(self, username):
        try:
            rs = requests.session()
            url = f'http://www.spoj.com/users/{username}'
            profile_page = rs.get(url=url, headers=_http_headers)
            soup = BeautifulSoup(profile_page.text, 'html.parser')

            problems = []
            contentTable = soup.find('table', {"class": "table-condensed"})

            for link in contentTable.findAll('a'):
                problem_name = link.string
                if problem_name is not None:
                    problems.append(problem_name)

            return {
                'platform': 'spoj',
                'user_name': username,
                'solved_count': len(problems),
                'solved_problems': problems
            }
        except Exception as e:
            return {
                'platform': 'spoj',
                'user_name': username,
                'solved_count': 0,
                'solved_problems': []
            }


if __name__ == '__main__':
    print('START RUNNING SPOJ SCRAPPER SCRIPT\n')
    spoj_scrapper = SpojScrapper()
    resp = spoj_scrapper.get_user_info('tarango_khan')
    print(json.dumps(resp))
