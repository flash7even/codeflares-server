import time
import json
import requests
from flask import current_app as app

from scrappers.codeforces_scrapper import CodeforcesScrapper
from scrappers.spoj_scrapper import SpojScrapper
from scrappers.uva_scrapper import UvaScrapper
from scrappers.codechef_scrapper import CodechefScrapper
from scrappers.loj_scrapper import LightOJScrapper

from core.problem_services import add_user_problem_status
from core.problem_services import search_problems

_http_headers = {'Content-Type': 'application/json'}


_es_index_user = 'cp_training_users'
_es_type = '_doc'
_es_size = 500

public_fields = ['username', 'first_name', 'last_name', 'full_name', 'skill_value', 'skill_title', 'solve_count']


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


def get_user_details_by_handle_name(username):
    try:
        rs = requests.session()
        query_json = {'query': {'bool': {'must': [{'match': {'username': username}}]}}}
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_user, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        if 'hits' in response:
            for hit in response['hits']['hits']:
                user = hit['_source']
                user['id'] = hit['_id']
                return user
        return None
    except Exception as e:
        raise e


def get_user_details(user_id):
    try:
        rs = requests.session()
        search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index_user, _es_type, user_id)
        response = rs.get(url=search_url, headers=_http_headers).json()
        print('response: ', response)
        if 'found' in response:
            if response['found']:
                data = response['_source']
                app.logger.info('Get user_details method completed')
                return data
        raise Exception('User not found')
    except Exception as e:
        raise e


def update_user_details(user_id, user_data):
    try:
        app.logger.info('update_user_details called ' + str(user_id))
        ignore_fields = ['username', 'password']
        rs = requests.session()

        search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index_user, _es_type, user_id)
        app.logger.debug('Elasticsearch query : ' + str(search_url))
        response = rs.get(url=search_url, headers=_http_headers).json()
        app.logger.debug('Elasticsearch response :' + str(response))

        if 'found' in response:
            if response['found']:
                user = response['_source']
                for key in user_data:
                    if key not in ignore_fields and user_data[key]:
                        user[key] = user_data[key]

                app.logger.debug('Elasticsearch query : ' + str(search_url))
                response = rs.put(url=search_url, json=user, headers=_http_headers).json()
                app.logger.debug('Elasticsearch response :' + str(response))
                if 'result' in response:
                    app.logger.info('Update user API completed')
                    return response['result']
            app.logger.info('User not found')
            return 'not found'
        app.logger.error('Elasticsearch down')
        return response

    except Exception as e:
        return {'message': str(e)}


def get_user_details_public(user_id):
    try:
        rs = requests.session()
        search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index_user, _es_type, user_id)
        response = rs.get(url=search_url, headers=_http_headers).json()
        print('response: ', response)
        if 'found' in response:
            if response['found']:
                data = response['_source']
                public_data = {}
                for f in public_fields:
                    public_data[f] = data.get(f, None)
                public_data['id'] = user_id
                app.logger.info('Get user_details method completed')
                return public_data
        raise Exception('User not found')
    except Exception as e:
        raise e


def sync_problems(user_id, problem_list):
    try:
        for problem in problem_list:
            problem_db = search_problems({'problem_id': problem}, 0, 1)
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
                sync_problems(user_id, problem_stat['solved_problems'])

        if 'codechef' in allowed_judges:
            handle = user_info.get('codechef_handle', None)
            print('codechef: ', handle)
            if handle:
                problem_stat = codechef.get_user_info(handle)
                sync_problems(user_id, problem_stat['solved_problems'])

        if 'uva' in allowed_judges:
            handle = user_info.get('uva_handle', None)
            print('uva: ', handle)
            if handle:
                problem_stat = uva.get_user_info(handle)
                sync_problems(user_id, problem_stat['solved_problems'])

        if 'spoj' in allowed_judges:
            handle = user_info.get('spoj_handle', None)
            print('spoj: ', handle)
            if handle:
                problem_stat = spoj.get_user_info(handle)
                sync_problems(user_id, problem_stat['solved_problems'])

        if 'lightoj' in allowed_judges:
            handle = user_info.get('lightoj_handle', None)
            print('lightoj: ', handle)
            if handle:
                problem_stat = lightoj.get_user_info(handle)
                sync_problems(user_id, problem_stat['solved_problems'])

    except Exception as e:
        raise e


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
