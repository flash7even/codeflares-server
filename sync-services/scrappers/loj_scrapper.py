from bs4 import BeautifulSoup
import json
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options

login_url = 'http://www.lightoj.com/login_main.php'
user_details_url = 'http://www.lightoj.com/volume_userstat.php?user_id='


class LightOJScrapper:

    def get_user_info(self, username, credentials):
        # print(f'get_user_info called for: {username}')
        try:
            options = Options()
            options.headless = True
            driver = webdriver.Firefox(options=options)
            driver.get(login_url)
            # print('go to login page')

            elem = driver.find_element_by_name("myuserid")
            elem.clear()
            elem.send_keys(credentials['username'])

            elem = driver.find_element_by_name("mypassword")
            elem.clear()
            elem.send_keys(credentials['password'])

            elem.send_keys(Keys.ENTER)
            # print('login completed')

            url = user_details_url + username

            driver.get(url)
            page_source = driver.page_source
            # print('received problem statistics for user')
            soup = BeautifulSoup(page_source, 'html.parser')

            tables = soup.findAll("table")

            count = 0
            problem_list_table = None

            for table in tables:
                table_data = str(table)
                if table_data.find("Solved List") != -1:
                    problem_list_table = table
                    break

            problems = []

            for link in problem_list_table.findAll('a'):
                problem_href = str(link['href'])
                mlist = problem_href.split('=')
                problem = mlist[len(mlist) - 1]
                if problem is not None:
                    problems.append(problem)

            # print(f'solved problem list: {json.dumps(problems)}')
            driver.quit()

            return {
                'platform': 'lightoj',
                'user_name': username,
                'solved_count': len(problems),
                'solved_problems': problems
            }
        except Exception as e:
            print(f'Exception occurred, could not manage to get user statistics from lightoj')
            print(f'Exception: {str(e)}')
            data = {
                'platform': 'lightoj',
                'user_name': username,
                'solved_count': 0,
                'solved_problems': []
            }
            print(f'Return data: {json.dumps(data)}')
            return data

    def get_user_info_heavy(self, username, credentials):
        # print(f'get_user_info called for: {username}')
        try:
            options = Options()
            options.headless = True
            driver = webdriver.Firefox(options=options)
            driver.get(login_url)
            # print('go to login page')

            elem = driver.find_element_by_name("myuserid")
            elem.clear()
            elem.send_keys(credentials['username'])

            elem = driver.find_element_by_name("mypassword")
            elem.clear()
            elem.send_keys(credentials['password'])

            elem.send_keys(Keys.ENTER)
            # print('login completed')

            url = user_details_url + username

            driver.get(url)
            page_source = driver.page_source
            # print('received problem statistics for user')
            soup = BeautifulSoup(page_source, 'html.parser')

            tables = soup.findAll("table")

            count = 0
            problem_list_table = None

            for table in tables:
                table_data = str(table)
                if table_data.find("Solved List") != -1:
                    problem_list_table = table
                    break

            solved_problems = {}

            for link in problem_list_table.findAll('a'):
                problem_href = str(link['href'])
                mlist = problem_href.split('=')
                problem = mlist[len(mlist) - 1]
                if problem is not None:
                    problem_data = {
                        'problem_id': problem,
                        'submission_list': [
                            {
                                'submission_link': f'http://lightoj.com/volume_submissions.php'
                            }
                        ]
                    }
                    solved_problems[problem] = problem_data

            # print(f'solved problem list: {json.dumps(solved_problems)}')
            driver.quit()

            return {
                'platform': 'lightoj',
                'user_name': username,
                'solved_count': len(solved_problems),
                'solved_problems': solved_problems
            }
        except Exception as e:
            print(f'Exception occurred, could not manage to get user statistics from lightoj')
            print(f'Exception: {str(e)}')
            data = {
                'platform': 'lightoj',
                'user_name': username,
                'solved_count': 0,
                'solved_problems': {}
            }
            print(f'Return data: {json.dumps(data)}')
            return data
