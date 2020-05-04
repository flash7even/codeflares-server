import time
import json
import requests
from flask import current_app as app

from scrappers.codeforces_scrapper import CodeforcesScrapper
from scrappers.spoj_scrapper import SpojScrapper
from scrappers.uva_scrapper import UvaScrapper
from scrappers.codechef_scrapper import CodechefScrapper

from core.problem_services import add_user_problem_status
from core.problem_services import search_problems_light

_http_headers = {'Content-Type': 'application/json'}


_es_index_user = 'cp_training_users'
_es_type = '_doc'
_es_size = 500


def get_user_rating_history(user_id):
    return [
        {
            "date": {
                "year": 2013, "month": 1, "day": 16
            },
            "rating": 1408
        },
        {
            "date": {
                "year": 2013, "month": 3, "day": 4
            },
            "rating": 1520
        },
        {
            "date": {
                "year": 2013, "month": 5, "day": 8
            },
            "rating": 1780
        },
        {
            "date": {
                "year": 2013, "month": 9, "day": 22
            },
            "rating": 1710
        },
        {
            "date": {
                "year": 2013, "month": 12, "day": 5
            },
            "rating": 1812
        },
        {
            "date": {
                "year": 2014, "month": 2, "day": 6
            },
            "rating": 1730
        },
        {
            "date": {
                "year": 2014, "month": 3, "day": 18
            },
            "rating": 1905
        },
        {
            "date": {
                "year": 2014, "month": 4, "day": 22
            },
            "rating": 2070
        }
    ]


def get_user_details(user_id):
    try:
        rs = requests.session()
        search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index_user, _es_type, user_id)
        response = rs.get(url=search_url, headers=_http_headers).json()
        if 'found' in response:
            if response['found']:
                data = response['_source']
                app.logger.info('Get user_details method completed')
                return data
        raise Exception('User not found')
    except Exception as e:
        raise Exception(e)


def sync_problems(user_id, problem_list):
    try:
        for problem in problem_list:
            problem_db = search_problems_light({'problem_id': problem}, 0, 1)
            if len(problem_db) == 0:
                continue
            problem_id = problem_db[0]['id']
            add_user_problem_status(user_id, problem_id, 'SOLVED')

    except Exception as e:
        raise Exception(e)


def synch_user_problem(user_id):
    try:
        uva = UvaScrapper()
        codeforces = CodeforcesScrapper()
        spoj = SpojScrapper()
        codechef = CodechefScrapper()

        user_info = get_user_details(user_id)
        allowed_judges = ['codeforces', 'uva', 'codechef', 'spoj']

        if 'codeforces' in allowed_judges:
            handle = user_info.get('codeforces_handle', None)
            if handle:
                problem_stat = codeforces.get_user_info(handle)
                sync_problems(user_id, problem_stat['solved_problems'])

        if 'codechef' in allowed_judges:
            handle = user_info.get('codechef_handle', None)
            if handle:
                problem_stat = codechef.get_user_info(handle)
                sync_problems(user_id, problem_stat['solved_problems'])

        if 'uva' in allowed_judges:
            handle = user_info.get('uva_handle', None)
            if handle:
                problem_stat = uva.get_user_info(handle)
                sync_problems(user_id, problem_stat['solved_problems'])

        if 'spoj' in allowed_judges:
            handle = user_info.get('spoj_handle', None)
            if handle:
                problem_stat = spoj.get_user_info(handle)
                sync_problems(user_id, problem_stat['solved_problems'])

    except Exception as e:
        raise Exception(e)


def search_user(param, from_val, to_val):
    try:
        must = []

        text_fields = ['username', 'email', 'mobile']
        keyword_fields = ['user_role']

        for k in text_fields:
            if k in param:
                must.append({'match': {k: param[k]}})

        for k in keyword_fields:
            if k in param:
                must.append({'term': {k: param[k]}})

        query_json = {'query': {'bool': {'must': must}}}

        query_json['from'] = from_val
        query_json['size'] = to_val
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_user, _es_type)
        response = requests.session().post(url=search_url, json=query_json, headers=_http_headers).json()

        if 'hits' in response:
            data = []
            for hit in response['hits']['hits']:
                user = hit['_source']
                user['id'] = hit['_id']

                user['rating'] = 1988
                user['title'] = 'Candidate Master'
                user['max_rating'] = 1988
                user['solve_count'] = 890
                user['follower'] = 921
                user['following'] = 530
                user['rating_history'] = get_user_rating_history(user['id'])

                data.append(user)
            app.logger.info('Search user API completed')
            return data
        app.logger.error('Elasticsearch down, response : ' + str(response))
        raise Exception('Internal server error')

    except Exception as e:
        raise e
