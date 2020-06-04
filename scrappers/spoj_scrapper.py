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

    def get_submission_stat(self, username):
        rs = requests.session()
        submission_list = []
        start = 0
        solved_problems = []
        while start < 1000:
            url = f'https://www.spoj.com/status/{username}/all/start={start}'
            submission_page = rs.get(url=url, headers=_http_headers)
            soup = BeautifulSoup(submission_page.text, 'html.parser')
            table = soup.find("table",{"class":"newstatus"})
            for row in table.find_all("tr")[1:]:  # skipping header row
                cells = row.find_all("td")
                submission_id = re.sub('\s+', '', str(cells[0].text))
                submission_date = re.sub('\s+', '', str(cells[1].text))
                problem_id = re.sub('\s+', '', str(cells[2].find('a').get('title')))
                verdict = re.sub('\s+', '', str(cells[3].text))
                if verdict == 'accepted' and problem_id not in solved_problems:
                    solved_problems.append(problem_id)
                    submission_data = {
                        'submission_id': submission_id,
                        'submission_link': '',
                        'submission_date': submission_date,
                        'problem_id': problem_id,
                        'verdict': verdict,
                    }
                    submission_list.append(submission_data)
            start += 20

        return {
            'platform': 'spoj',
            'user_name': username,
            'solved_count': len(solved_problems),
            'solved_problems': solved_problems,
            'submission_stat': submission_list
        }


if __name__ == '__main__':
    print('START RUNNING SPOJ SCRAPPER SCRIPT\n')
    spoj_scrapper = SpojScrapper()
    # resp = spoj_scrapper.get_user_info('tarango_khan')
    submission_list = spoj_scrapper.get_submission_stat('tarango_khan')
    print(submission_list)