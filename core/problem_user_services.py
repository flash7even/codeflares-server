import json
from flask import current_app as app

from core.problem_services import search_problems, apply_solved_problem_for_user, search_problems_filtered_by_categories, get_user_problem_status, add_user_problem_status
from core.user_services import get_user_details
from scrappers.codechef_scrapper import CodechefScrapper
from scrappers.codeforces_scrapper import CodeforcesScrapper
from scrappers.loj_scrapper import LightOJScrapper
from scrappers.spoj_scrapper import SpojScrapper
from scrappers.uva_scrapper import UvaScrapper
from core.category_services import search_categories, find_dependent_category_list
from core.user_category_edge_services import update_root_category_skill_for_user, get_user_category_data, add_user_category_data
from models.category_score_model import CategoryScoreGenerator
from models.problem_score_model import ProblemScoreGenerator
from commons.skillset import Skill
from core.training_model_services import sync_overall_stat_for_user

_es_size = 5000


def update_problem_score(user_id, user_skill_level, updated_categories):
    app.logger.info(f'update_problem_score called for: {user_id}, with skill: {user_skill_level}')
    problem_score_generator = ProblemScoreGenerator()
    problem_list = search_problems_filtered_by_categories(updated_categories)

    for problem in problem_list:
        problem_id = problem['id']
        up_edge = get_user_problem_status(user_id, problem_id)
        if up_edge is not None and up_edge['status'] == "SOLVED":
            continue

        if up_edge is None:
            up_edge = {
                "problem_id": problem_id,
                "user_id": user_id,
                "relevant_score": 0,
                "status": "UNSOLVED"
            }

        dcat_list = problem.get('categories', [])
        dcat_level_list = []

        for cat in dcat_list:
            category_id = cat['category_id']
            if category_id in updated_categories:
                uc_edge = updated_categories[category_id]
            else:
                uc_edge = get_user_category_data(user_id, category_id)
                updated_categories[category_id] = uc_edge
            dcat_level_list.append(uc_edge['skill_level'])
        relevant_score = problem_score_generator.generate_score(int(float(problem['problem_difficulty'])), dcat_level_list, user_skill_level)
        up_edge['relevant_score'] = relevant_score['score']
        add_user_problem_status(user_id, problem_id, up_edge)


def sync_problems(user_id, oj_problem_set):
    try:
        category_score_generator = CategoryScoreGenerator()
        updated_categories = {}

        for problem_set in oj_problem_set:
            for problem in problem_set['problem_list']:
                problem_db = search_problems({'problem_id': problem, 'oj_name': problem_set['oj_name']}, 0, 1)
                if len(problem_db) == 0:
                    continue
                problem_id = problem_db[0]['id']
                if len(problem_db) > 1:
                    app.logger.error('Multiple problem with same id found')
                apply_solved_problem_for_user(user_id, problem_id, problem_db[0], updated_categories)

        marked_categories = dict(updated_categories)

        for category_id in marked_categories:
            uc_edge = marked_categories[category_id]
            # UPDATE OWN CONTRIBUTION
            old_cont = category_score_generator.get_own_difficulty_based_score(uc_edge['old_skill_level'])
            new_cont = category_score_generator.get_own_difficulty_based_score(uc_edge['skill_level'])
            cont_dx = new_cont - old_cont
            uc_edge['relevant_score'] += cont_dx
            updated_categories[category_id] = uc_edge
            # UPDATE DEPENDENT CATEGORY CONTRIBUTION
            dependent_cat_list = find_dependent_category_list(category_id)
            for dcat in dependent_cat_list:
                dcat_id = dcat['category_id']
                dcat_category_root = dcat['category_info']['category_root']
                if dcat_id in updated_categories:
                    dcat_uc_edge = updated_categories[dcat_id]
                else:
                    dcat_uc_edge = get_user_category_data(user_id, dcat_id)

                if dcat_uc_edge is None:
                    dcat_uc_edge = {
                        "category_id": dcat_id,
                        "category_root": dcat_category_root,
                        "user_id": user_id,
                        "skill_value": 0,
                        "skill_level": 0,
                        "old_skill_level": 0,
                        "relevant_score": 0,
                        "solve_count": 0,
                        "skill_value_by_percentage": 0,
                    }
                    for d in range(1, 11):
                        key = 'scd_' + str(d)
                        dcat_uc_edge[key] = 0

                dependency_percentage = float(dcat['dependency_percentage'])
                old_cont = category_score_generator.get_dependent_score(uc_edge['old_skill_level'], dependency_percentage)
                new_cont = category_score_generator.get_dependent_score(uc_edge['skill_level'], dependency_percentage)
                cont_dx = new_cont - old_cont
                dcat_uc_edge['relevant_score'] += cont_dx
                dcat_uc_edge['solve_count'] += 1
                updated_categories[dcat_id] = dcat_uc_edge

        for category_id in updated_categories:
            uc_edge = updated_categories[category_id]
            uc_edge.pop('old_skill_level', None)
            uc_edge.pop('id', None)
            add_user_category_data(user_id, category_id, uc_edge)

        root_category_list = search_categories({"category_root": "root"}, 0, _es_size)
        skill = Skill()
        user_skill = update_root_category_skill_for_user(user_id, root_category_list)
        user_skill_level = skill.get_skill_level_from_skill(user_skill)
        sync_overall_stat_for_user(user_id, user_skill)
        update_problem_score(user_id, user_skill_level, updated_categories)
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
        allowed_judges = ['codeforces', 'uva', 'codechef', 'spoj', 'lightoj']

        oj_problem_set = []

        if 'codeforces' in allowed_judges:
            handle = user_info.get('codeforces_handle', None)
            print('Codeforces: ', handle)
            if handle:
                problem_stat = codeforces.get_user_info(handle)
                oj_problem_set.append({
                    'problem_list': problem_stat['solved_problems'],
                    'oj_name': 'codeforces'
                })

        if 'codechef' in allowed_judges:
            handle = user_info.get('codechef_handle', None)
            print('codechef: ', handle)
            if handle:
                problem_stat = codechef.get_user_info(handle)
                oj_problem_set.append({
                    'problem_list': problem_stat['solved_problems'],
                    'oj_name': 'codechef'
                })

        if 'uva' in allowed_judges:
            handle = user_info.get('uva_handle', None)
            print('uva: ', handle)
            if handle:
                problem_stat = uva.get_user_info(handle)
                oj_problem_set.append({
                    'problem_list': problem_stat['solved_problems'],
                    'oj_name': 'uva'
                })

        if 'spoj' in allowed_judges:
            handle = user_info.get('spoj_handle', None)
            print('spoj: ', handle)
            if handle:
                problem_stat = spoj.get_user_info(handle)
                oj_problem_set.append({
                    'problem_list': problem_stat['solved_problems'],
                    'oj_name': 'spoj'
                })

        if 'lightoj' in allowed_judges:
            handle = user_info.get('lightoj_handle', None)
            app.logger.info(f'lightoj handle: {handle}')
            if handle:
                problem_stat = lightoj.get_user_info(handle)
                oj_problem_set.append({
                    'problem_list': problem_stat['solved_problems'],
                    'oj_name': 'lightoj'
                })

        sync_problems(user_id, oj_problem_set)

    except Exception as e:
        raise e
