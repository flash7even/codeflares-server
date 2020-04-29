import time
import json
import requests
from bs4 import BeautifulSoup
import re

_http_headers = {'Content-Type': 'application/json'}


class CodechefScrapper:

    def get_user_info(slef, username):
        rs = requests.session()
        url = f'https://www.codechef.com/users/{username}'
        profile_page = rs.get(url=url, headers=_http_headers)
        soup = BeautifulSoup(profile_page.text, 'html.parser')

        problems = []
        contentTable = soup.find('article')

        for link in contentTable.findAll('a'):
            problem_name = link.string
            if problem_name is not None:
                problems.append(problem_name)

        return {
            'platform': 'codechef',
            'user_name': username,
            'solved_count': len(problems),
            'solved_problems': problems
        }


if __name__ == '__main__':
    print('START RUNNING CODECHEF SCRAPPER SCRIPT\n')
    codechef_scrapper = CodechefScrapper()
    resp = codechef_scrapper.get_user_info('tarango_khan')
    print(json.dumps(resp))
