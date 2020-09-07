import time
import json
import requests
from bs4 import BeautifulSoup
import re

_http_headers = {'Content-Type': 'application/json'}

class CodechefScrapper:

    def get_submission_history(self, username):
        rs = requests.session()
        year = 2020
        while year >= 2008:
            url = f'https://www.codechef.com/submissions?sort_by=All&sorting_order=desc&language=All&status=15&year={year}&handle={username}&pcode=&ccode=&Submit=GO'
            submission_page = rs.get(url=url, headers=_http_headers)
            soup = BeautifulSoup(submission_page.text, 'html.parser')
            soup.prettify()
            table = soup.find("table",{"class":"dataTable"})
            for row in table.find_all("tr")[1:]:  # skipping header row
                cells = row.find_all("td")
                print(cells[0].text)
                submission_id = cells[0].text
                submission_date = cells[1].text
                problem_id = cells[3].find('a').text
                verdict = 'unsuccessful'
                verdict_data = str(cells[5])
                if verdict_data.find('accepted') != -1 or verdict_data.find('100pts') != -1:
                    verdict = 'accepted'

                submission_data = {
                    'submission_id': submission_id,
                    'submission_date': submission_date,
                    'problem_id': problem_id,
                    'verdict': verdict,
                }
                print(submission_data)
            year -= 1

    def get_submission_for_problem(self, username, problem_id):
        try:
            rs = requests.session()
            url = f'https://www.codechef.com/status/{problem_id},{username}'
            submission_page = rs.get(url=url, headers=_http_headers)
            soup = BeautifulSoup(submission_page.text, 'html.parser')
            table = soup.find("table",{"class":"dataTable"})
            last_ac_submission = None
            for row in table.find_all("tr")[1:]:  # skipping header row
                cells = row.find_all("td")
                submission_id = cells[0].text
                submission_date = cells[1].text
                problem_id = problem_id
                verdict = 'unsuccessful'
                verdict_data = str(cells[3])
                if verdict_data.find('accepted') != -1 or verdict_data.find('100pts') != -1:
                    verdict = 'accepted'
                    submission_data = {
                        'submission_id': submission_id,
                        'submission_date': submission_date,
                        'problem_id': problem_id,
                        'verdict': verdict,
                    }
                    last_ac_submission = submission_data
            return last_ac_submission
        except Exception as e:
            return None

    def get_user_info(slef, username):
        try:
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
        except Exception as e:
            return {
                'platform': 'codechef',
                'user_name': username,
                'solved_count': 0,
                'solved_problems': []
            }

    def get_user_info_heavy(slef, username):
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
                except:
                    print(f'Exception occurred for user: {username}, submission: {link}')
                    continue

            return {
                'platform': 'codechef',
                'user_name': username,
                'solved_count': len(solved_problems),
                'solved_problems': solved_problems
            }
        except Exception as e:
            return {
                'platform': 'codechef',
                'user_name': username,
                'solved_count': 0,
                'solved_problems': {}
            }

    def get_problem_stat(self, username):
        stat = self.get_user_info(username)
        print(stat)
        solved_problems = stat['solved_problems']
        problem_stat_list = []
        for problem_id in solved_problems:
            print('CHECK FOR: ', problem_id)
            problem_stat = self.get_submission_for_problem(username, problem_id)
            if problem_stat:
                print(problem_stat)
                problem_stat_list.append(problem_stat)
            else:
                print('Problem info could not found for: ', problem_id)
        stat['problem_stat_list'] = problem_stat_list
        return problem_stat_list


if __name__ == '__main__':
    print('START RUNNING CODECHEF SCRAPPER SCRIPT\n')
    codechef_scrapper = CodechefScrapper()
    #resp = codechef_scrapper.get_user_info('tarango_khan')
    #print(json.dumps(resp))
    # codechef_stat = codechef_scrapper.get_problem_stat('tarango_khan')
    problem_stat_list = codechef_scrapper.get_user_info_heavy('tarango_khan')
    print(problem_stat_list)