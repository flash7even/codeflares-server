import json

from flask import current_app as app

from core.problem_services import search_problems, add_user_problem_status, apply_solved_problem_for_user
from core.user_services import get_user_details
from scrappers.codechef_scrapper import CodechefScrapper
from scrappers.codeforces_scrapper import CodeforcesScrapper
from scrappers.loj_scrapper import LightOJScrapper
from scrappers.spoj_scrapper import SpojScrapper
from scrappers.uva_scrapper import UvaScrapper
from core.category_services import search_categories
from core.user_category_edge_services import update_root_category_skill_for_user

_es_size = 1000


def sync_problems(user_id, problem_list, oj_name):
    try:
        updated_categories = []
        for problem in problem_list:
            problem_db = search_problems({'problem_id': problem, 'oj_name': oj_name}, 0, 1)
            app.logger.info(f'lightoj problem in es db: {problem_db}')
            if len(problem_db) == 0:
                continue
            problem_id = problem_db[0]['id']
            if len(problem_db) > 1:
                app.logger.error('Multiple problem with same id found')
            rsp = apply_solved_problem_for_user(user_id, problem_id, problem_db[0])
            modified_list = rsp['updated_categories']
            for cat in modified_list:
                if cat not in updated_categories:
                    updated_categories.append(cat)

            root_category_list = search_categories({"category_root": "root"}, 0, _es_size)
            user_skill = update_root_category_skill_for_user(user_id, root_category_list)
            app.logger.info(f'user_skill: {user_skill}')
    except Exception as e:
        raise e


def synch_user_problem(user_id):
    try:
        uva = UvaScrapper()
        codeforces = CodeforcesScrapper()
        spoj = SpojScrapper()
        codechef = CodechefScrapper()
        lightoj = LightOJScrapper()

        user_info = get_user_details(user_id)
        print('user_info: ', user_info)
        allowed_judges = ['codeforces', 'uva', 'codechef', 'spoj']

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
            app.logger.info(f'lightoj handle: {handle}')
            if handle:
                problem_stat = lightoj.get_user_info(handle)
                app.logger.info(f'lightoj problem_stat: {json.dumps(problem_stat)}')
                sync_problems(user_id, problem_stat['solved_problems'], 'lightoj')

    except Exception as e:
        raise e
