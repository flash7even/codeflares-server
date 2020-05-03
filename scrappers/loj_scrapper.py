from bs4 import BeautifulSoup
import json
from selenium import webdriver
from selenium.webdriver.common.keys import Keys

login_url = 'http://www.lightoj.com/login_main.php'
user_details_url = 'http://www.lightoj.com/volume_userstat.php?user_id='


class LightOJScrapper:

    def get_user_info(self, username, credentials):

        driver = webdriver.Firefox()
        driver.get(login_url)

        elem = driver.find_element_by_name("myuserid")
        elem.clear()
        elem.send_keys(credentials['username'])

        elem = driver.find_element_by_name("mypassword")
        elem.clear()
        elem.send_keys(credentials['password'])

        elem.send_keys(Keys.ENTER)

        url = user_details_url + username

        driver.get(url)
        page_source = driver.page_source
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

        driver.quit()

        return {
            'platform': 'lightoj',
            'user_name': username,
            'solved_count': len(problems),
            'solved_problems': problems
        }


if __name__ == '__main__':
    print('START RUNNING SPOJ SCRAPPER SCRIPT\n')
    loj_scrapper = LightOJScrapper()
    credentials = {
        'username': 'tarangokhan77@gmail.com',
        'password': 'HeLLo@WoRLD2014'
    }
    resp = loj_scrapper.get_user_info('14826', credentials)
    print(json.dumps(resp))
