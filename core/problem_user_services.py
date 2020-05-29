from flask import current_app as app

from core.problem_services import search_problems, add_user_problem_status
from core.user_services import get_user_details
from scrappers.codechef_scrapper import CodechefScrapper
from scrappers.codeforces_scrapper import CodeforcesScrapper
from scrappers.loj_scrapper import LightOJScrapper
from scrappers.spoj_scrapper import SpojScrapper
from scrappers.uva_scrapper import UvaScrapper


def sync_problems(user_id, problem_list, oj_name):
    try:
        for problem in problem_list:
            problem_db = search_problems({'problem_id': problem, 'oj_name': oj_name}, 0, 1)
            if len(problem_db) == 0:
                continue
            problem_id = problem_db[0]['id']
            if len(problem_db) > 1:
                app.logger.error('Multiple problem with same id found')
            data = {
                'user_id': user_id,
                'problem_id': problem_id,
                'status': 'SOLVED'
            }
            add_user_problem_status(user_id, problem_id, data)
    except Exception as e:
        raise e


def synch_user_problem(user_id):
    app.logger.info('synch_user_problem called: ' + str(user_id))
    try:
        uva = UvaScrapper()
        codeforces = CodeforcesScrapper()
        spoj = SpojScrapper()
        codechef = CodechefScrapper()
        lightoj = LightOJScrapper()

        user_info = get_user_details(user_id)
        print('user_info: ', user_info)
        allowed_judges = ['codeforces', 'uva', 'codechef', 'spoj', 'lightoj']

        if 'codeforces' in allowed_judges:
            handle = user_info.get('codeforces_handle', None)
            print('Codeforces: ', handle)
            if handle:
                problem_stat = codeforces.get_user_info(handle)
                sync_problems(user_id, problem_stat['solved_problems'], 'codeforces')

        if 'codechef' in allowed_judges:
            handle = user_info.get('codechef_handle', None)
            print('codechef: ', handle)
            if handle:
                problem_stat = codechef.get_user_info(handle)
                sync_problems(user_id, problem_stat['solved_problems'], 'codechef')

        if 'uva' in allowed_judges:
            handle = user_info.get('uva_handle', None)
            print('uva: ', handle)
            if handle:
                problem_stat = uva.get_user_info(handle)
                sync_problems(user_id, problem_stat['solved_problems'], 'uva')

        if 'spoj' in allowed_judges:
            handle = user_info.get('spoj_handle', None)
            print('spoj: ', handle)
            if handle:
                problem_stat = spoj.get_user_info(handle)
                sync_problems(user_id, problem_stat['solved_problems'], 'spoj')

        if 'lightoj' in allowed_judges:
            handle = user_info.get('lightoj_handle', None)
            print('lightoj: ', handle)
            if handle:
                problem_stat = lightoj.get_user_info(handle)
                sync_problems(user_id, problem_stat['solved_problems'], 'lightoj')

    except Exception as e:
        raise e