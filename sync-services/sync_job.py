import logging
import os
import re
import time
import json
import unittest
import requests
from datetime import timedelta
from logging.handlers import TimedRotatingFileHandler

from apscheduler.schedulers.background import BackgroundScheduler
from redis import Redis

from config_development import ConfigDevelopment
from config_production import ConfigProduction

from scrappers.codechef_scrapper import CodechefScrapper
from scrappers.loj_scrapper import LightOJScrapper
from scrappers.spoj_scrapper import SpojScrapper
from scrappers.uva_scrapper import UvaScrapper
from scrappers.codeforces_scrapper import CodeforcesScrapper
from models.category_score_model import CategoryScoreGenerator
from models.category_skill_model import CategorySkillGenerator
from models.problem_score_model import ProblemScoreGenerator
from models.skillset import Skill

environ = os.getenv('SCRIPT_ENV', 'dev')
global config

if environ.lower() in ['development', 'dev', 'devel']:
    config = ConfigDevelopment
else:
    config = ConfigProduction

logger = logging.getLogger('sync job logger')
logger.setLevel(logging.DEBUG)
handler = TimedRotatingFileHandler('../logs/sync_job.log', when='midnight', interval=1,  backupCount=30)
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter(
    fmt='[%(asctime)s.%(msecs)03d] [%(levelname)s]: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))
handler.suffix = "%Y%m%d"
handler.extMatch = re.compile(r"^\d{8}$")
logger.addHandler(handler)

redis_client = Redis(config.REDIS_HOST, config.REDIS_PORT, db=0, decode_responses=True)

rs = requests.session()
_http_headers = {'Content-Type': 'application/json'}


ADMIN_USER = os.getenv('ADMIN_USERNAME')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')

access_token = None
login_api = f'{config.SERVER_HOST}/auth/login'
team_training_model_sync_api = f'{config.SERVER_HOST}/team/sync/training-model/'
job_search_url = f'{config.SERVER_HOST}/job/search'
job_url = f'{config.SERVER_HOST}/job/'


_es_index_user = 'cfs_users'
_es_index_problem = 'cfs_problems'
_es_index_category = 'cfs_categories'
_es_index_problem_user = 'cfs_user_problem_edges'
_es_index_user_category = 'cfs_user_category_edges'
_es_index_category_dependency = 'cfs_category_dependencies'
_es_user_user_notification = 'cfs_notifications'
_es_type = '_doc'
_es_size = 2000

_es_max_solved_problem = 2000

SOLVED = 'SOLVED'
UNSOLVED = 'UNSOLVED'
SOLVE_LATER = 'SOLVE_LATER'
FLAGGED = 'FLAGGED'
approved = 'approved'
READ = 'READ'
UNREAD = 'UNREAD'


######################### REDIS SERVICES STARTS #########################


def check_pending_job(user_id):
    redis_user_pending_job_key = f'{config.REDIS_PREFIX_USER_PENDING_JOB}:{user_id}'
    if redis_client.exists(redis_user_pending_job_key):
        return True
    else:
        return False


def add_pending_job(user_id):
    redis_user_pending_job_key = f'{config.REDIS_PREFIX_USER_PENDING_JOB}:{user_id}'
    redis_client.set(redis_user_pending_job_key, 1)


def remove_pending_job(user_id):
    redis_user_pending_job_key = f'{config.REDIS_PREFIX_USER_PENDING_JOB}:{user_id}'
    redis_client.delete(redis_user_pending_job_key)


def add_new_job(user_id):
    redis_user_job_key = f'{config.REDIS_PREFIX_USER_JOB}:{user_id}'
    user_job_limit = int(config.REDIS_PREFIX_USER_JOB_LIMIT)

    if check_pending_job(user_id):
        return False

    if redis_client.exists(redis_user_job_key):
        job_count = int(redis_client.get(redis_user_job_key))
        if job_count < user_job_limit:
            redis_client.incr(redis_user_job_key, 1)
            add_pending_job(user_id)
            return True
        else:
            return False
    else:
        redis_client.set(redis_user_job_key, 1, timedelta(minutes=config.REDIS_PREFIX_USER_JOB_TIMEOUT))
        add_pending_job(user_id)
        return True




######################### AUTH SERVICES #########################


def get_access_token():
    global rs
    login_data = {
        "username": ADMIN_USER,
        "password": ADMIN_PASSWORD
    }
    response = rs.post(url=login_api, json=login_data, headers=_http_headers).json()
    return response['access_token']


def get_header():
    global rs
    global access_token
    if access_token is None:
        access_token = get_access_token()
    auth_headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    return auth_headers




######################### NOTIFICATION SERVICES #########################


def add_notification(data):
    try:
        rs = requests.session()
        data['created_at'] = int(time.time())
        data['updated_at'] = int(time.time())
        data['status'] = UNREAD
        post_url = 'http://{}/{}/{}'.format(config.ES_HOST, _es_user_user_notification, _es_type)
        response = rs.post(url=post_url, json=data, headers=_http_headers).json()
        if 'result' in response and response['result'] == 'created':
            return response['_id'], 201
        logger.error('Elasticsearch down, response: ' + str(response))
        raise Exception('Internal server error')
    except Exception as e:
        raise e




######################### USER SERVICES #########################


def get_user_details(user_id):
    try:
        rs = requests.session()
        search_url = 'http://{}/{}/{}/{}'.format(config.ES_HOST, _es_index_user, _es_type, user_id)
        response = rs.get(url=search_url, headers=_http_headers).json()
        # print('response: ', response)
        if 'found' in response:
            if response['found']:
                data = response['_source']
                data['id'] = response['_id']
                return data
        raise Exception('User not found')
    except Exception as e:
        raise e


def get_solved_problem_count_for_user(user_id):
    try:
        rs = requests.session()
        must = [
            {'term': {'user_id': user_id}},
            {'term': {'status': SOLVED}}
        ]
        query_json = {'query': {'bool': {'must': must}}}
        query_json['size'] = 1
        search_url = 'http://{}/{}/{}/_search'.format(config.ES_HOST, _es_index_problem_user, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        if 'hits' in response:
            return response['hits']['total']['value']
        return 0
    except Exception as e:
        raise e


def generate_skill_value_for_user(user_id):
    logger.info('generate_skill_value_for_user: ' + str(user_id))
    rs = requests.session()
    must = [
        {'term': {'category_root': 'root'}},
        {'term': {'user_id': user_id}},
    ]
    query_json = {'query': {'bool': {'must': must}}}
    query_json['size'] = _es_size

    # logger.info('generate_skill_value_for_user query_json: ' + json.dumps(query_json))
    search_url = 'http://{}/{}/{}/_search'.format(config.ES_HOST, _es_index_user_category, _es_type)
    response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
    logger.info('generate_skill_value_for_user response: ' + str(response))

    if 'hits' not in response:
        raise Exception('Internal server error')

    skill_value = 0
    if 'hits' in response:
        for hit in response['hits']['hits']:
            data = hit['_source']
            skill_value += data['skill_value_by_percentage']

    # logger.info('skill_value found: ' + str(skill_value))
    return skill_value


def sync_overall_stat_for_user(user_id, skill_value = None):
    try:
        solve_count = get_solved_problem_count_for_user(user_id)
        if skill_value is None:
            skill_value = generate_skill_value_for_user(user_id)
        skill_obj = Skill()
        skill_title = skill_obj.get_skill_title(skill_value)
        user_data = {
            'skill_value': skill_value,
            'solve_count': solve_count,
            'skill_title': skill_title,
        }
        update_user_details(user_id, user_data)
    except Exception as e:
        raise e


def update_user_details(user_id, user_data):
    try:
        ignore_fields = ['username', 'password']
        rs = requests.session()

        search_url = 'http://{}/{}/{}/{}'.format(config.ES_HOST, _es_index_user, _es_type, user_id)
        response = rs.get(url=search_url, headers=_http_headers).json()

        if 'found' in response:
            if response['found']:
                user = response['_source']
                for key in user_data:
                    if key not in ignore_fields and user_data[key]:
                        user[key] = user_data[key]

                response = rs.put(url=search_url, json=user, headers=_http_headers).json()
                if 'result' in response:
                    return response['result']
            return 'not found'
        logger.error('Elasticsearch down')
        return response

    except Exception as e:
        return {'message': str(e)}




######################### CATEGORY SERVICES #########################


def get_user_category_data(user_id, category_id):
    try:
        rs = requests.session()
        must = [
            {'term': {'user_id': user_id}},
            {'term': {'category_id': category_id}}
        ]
        query_json = {'query': {'bool': {'must': must}}}
        query_json['size'] = 1
        search_url = 'http://{}/{}/{}/_search'.format(config.ES_HOST, _es_index_user_category, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        if 'hits' in response:
            for hit in response['hits']['hits']:
                edge = hit['_source']
                edge['id'] = hit['_id']
                return edge
        return None
    except Exception as e:
        raise e


def get_category_details(cat_id, user_id = None):
    # logger.info(f'get_category_details function called for cat_id: {cat_id}, user_id: {user_id}')
    try:
        rs = requests.session()
        search_url = 'http://{}/{}/{}/{}'.format(config.ES_HOST, _es_index_category, _es_type, cat_id)
        response = rs.get(url=search_url, headers=_http_headers).json()
        if 'found' in response:
            if response['found']:
                data = response['_source']
                data['category_id'] = response['_id']
                data['problem_count'] = 0
                if user_id:
                    cat_info = get_user_category_data(user_id, data['category_id'])
                    if cat_info:
                        skill_value = float(cat_info.get('skill_value', 0))
                        data['skill_value'] = "{:.2f}".format(skill_value)
                        skill = Skill()
                        data['skill_title'] = skill.get_skill_title(skill_value)
                    else:
                        data['skill_value'] = 0
                        data['skill_title'] = "NA"
                # logger.info('get_category_details completed')
                return data
        return None
    except Exception as e:
        raise e


def find_dependent_category_list(category_id_2):
    try:
        rs = requests.session()
        must = [
            {'term': {'category_id_2': category_id_2}}
        ]
        query_json = {'query': {'bool': {'must': must}}}
        query_json['size'] = _es_size
        search_url = 'http://{}/{}/{}/_search'.format(config.ES_HOST, _es_index_category_dependency, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        item_list = []
        if 'hits' in response:
            for hit in response['hits']['hits']:
                category = hit['_source']
                category.pop('category_id_2', None)
                category['category_info'] = get_category_details(category['category_id_1'])
                category['category_id'] = category['category_id_1']
                category.pop('category_id_1', None)
                item_list.append(category)
            return item_list
        logger.error('Elasticsearch down, response: ' + str(response))
        return item_list
    except Exception as e:
        raise e


def add_user_category_data(user_id, category_id, data):
    try:
        rs = requests.session()
        data['user_id'] = user_id
        data['category_id'] = category_id
        edge = get_user_category_data(user_id, category_id)

        if edge is None:
            data['created_at'] = int(time.time())
            data['updated_at'] = int(time.time())
            url = 'http://{}/{}/{}'.format(config.ES_HOST, _es_index_user_category, _es_type)
            response = rs.post(url=url, json=data, headers=_http_headers).json()
            if 'result' in response:
                return response['_id']
            raise Exception('Internal server error')

        edge_id = edge['id']
        edge.pop('id', None)

        for f in data:
            edge[f] = data[f]

        edge['updated_at'] = int(time.time())
        url = 'http://{}/{}/{}/{}'.format(config.ES_HOST, _es_index_user_category, _es_type, edge_id)
        response = rs.put(url=url, json=edge, headers=_http_headers).json()

        if 'result' in response:
            return response['result']

        raise Exception('Internal server error')

    except Exception as e:
        raise e


def search_categories(param, from_value, size_value, heavy = False):
    try:
        query_json = {'query': {'match_all': {}}}
        rs = requests.session()

        must = []
        keyword_fields = ['category_title', 'category_root']
        user_id = param.get('user_id', None)
        # print('search_categories: body: ', param)
        param.pop('user_id', None)

        minimum_difficulty = 0
        maximum_difficulty = 100

        if 'minimum_difficulty' in param and param['minimum_difficulty']:
            minimum_difficulty = int(param['minimum_difficulty'])

        if 'maximum_difficulty' in param and param['maximum_difficulty']:
            maximum_difficulty = int(param['maximum_difficulty'])

        param.pop('minimum_difficulty', None)
        param.pop('maximum_difficulty', None)

        for f in param:
            if f in keyword_fields:
                if param[f]:
                    must.append({'term': {f: param[f]}})
            else:
                if param[f]:
                    must.append({'match': {f: param[f]}})

        must.append({"range": {"category_difficulty": {"gte": minimum_difficulty, "lte": maximum_difficulty}}})

        if len(must) > 0:
            query_json = {'query': {'bool': {'must': must}}}

        if 'category_root' not in param:
            if 'query' in query_json and 'bool' in query_json['query']:
                query_json['query']['bool']['must_not'] = [{'term': {'category_root': 'root'}}]
            else:
                query_json = {'query': {'bool': {'must_not': [{'term': {'category_root': 'root'}}]}}}

        query_json['from'] = from_value
        query_json['size'] = size_value
        # print('query_json: ', json.dumps(query_json))
        search_url = 'http://{}/{}/{}/_search'.format(config.ES_HOST, _es_index_category, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        # # print('response: ', response)
        item_list = []
        if 'hits' in response:
            for hit in response['hits']['hits']:
                category = hit['_source']
                category['category_id'] = hit['_id']
                category['problem_count'] = 0
                category['solve_count'] = 0
                if user_id:
                    cat_info = get_user_category_data(user_id, category['category_id'])
                    if cat_info is not None:
                        category['solve_count'] = cat_info.get('solve_count', 0)
                item_list.append(category)
            return item_list
        logger.error('Elasticsearch down, response: ' + str(response))
        return item_list
    except Exception as e:
        raise e


def update_root_category_skill_for_user(user_id, root_category_list, root_category_solve_count):
    # logger.info(f'update_root_category_skill_for_user called for: {user_id}')
    rs = requests.session()
    user_skill_sum = 0
    for cat in root_category_list:
        must = [{"term": {"category_root": cat["category_name"]}}, {"term": {"user_id": user_id}}]
        aggs = {
            "skill_value_by_percentage": {"sum": {"field": "skill_value_by_percentage"}}
        }
        query_json = {"size": 0, "query": {"bool": {"must": must}}, "aggs": aggs}
        search_url = 'http://{}/{}/{}/_search'.format(config.ES_HOST, _es_index_user_category, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        if 'aggregations' in response:
            skill_value = response['aggregations']['skill_value_by_percentage']['value']
            category_id = cat['category_id']
            category_name = cat['category_name']
            new_solve_count = root_category_solve_count.get(category_name, 0)
            uc_edge = get_user_category_data(user_id, category_id)
            # logger.info(f'uc_edge from es: {uc_edge}')
            if uc_edge is None:
                uc_edge = {
                    "category_id": category_id,
                    "category_root": 'root',
                    "user_id": user_id,
                    "skill_value": 0,
                    "skill_level": 0,
                    "relevant_score": 0,
                    "solve_count": 0,
                    "skill_value_by_percentage": 0,
                }
            uc_edge['skill_value'] = skill_value
            uc_edge['solve_count'] = int(uc_edge.get('solve_count', 0)) + new_solve_count
            skill_info = Skill()
            uc_edge['skill_title'] = skill_info.get_skill_title(uc_edge['skill_value'])
            uc_edge['skill_level'] = skill_info.get_skill_level_from_skill(uc_edge['skill_value'])
            score_percentage = float(cat['score_percentage'])
            uc_edge['skill_value_by_percentage'] = uc_edge['skill_value'] * score_percentage / 100
            user_skill_sum += uc_edge['skill_value_by_percentage']
            # logger.info(f'add uc_edge: {uc_edge}')
            uc_edge.pop('id', None)
            add_user_category_data(user_id, category_id, uc_edge)
    return user_skill_sum




######################### PROBLEM SERVICES #########################


def generate_query_params(param):
    if 'filter' in param and param['filter']:
        should = []
        nested_should = []
        nested_should.append({'term': {'categories.category_id': param['filter']}})
        nested_should.append({'term': {'categories.category_name': param['filter']}})
        nested_should.append({'term': {'categories.category_root': param['filter']}})
        should.append({'term': {'problem_title': param['filter']}})
        should.append({'match': {'problem_name': param['filter']}})
        should.append({'term': {'oj_name': param['filter']}})
        should.append({'nested': {'path': 'categories', 'query': {'bool': {'should': nested_should}}}})
        query_json = {'query': {'bool': {'should': should}}}
        return query_json
    else:
        must = []
        nested_must = []
        nested_fields = ['category_id', 'category_name', 'category_root']
        keyword_fields = ['problem_title', 'problem_id', 'problem_difficulty', 'oj_name', 'active_status']
        text_fields = ['problem_name']

        if 'category_id' in param:
            nested_must.append({'term': {'categories.category_id': param['category_id']}})
        if 'category_name' in param:
            nested_must.append({'term': {'categories.category_name': param['category_name']}})
        if 'category_root' in param:
            nested_must.append({'term': {'categories.category_root': param['category_root']}})

        minimum_difficulty = 0
        maximum_difficulty = 100

        if 'minimum_difficulty' in param and param['minimum_difficulty']:
            minimum_difficulty = int(param['minimum_difficulty'])

        if 'maximum_difficulty' in param and param['maximum_difficulty']:
            maximum_difficulty = int(param['maximum_difficulty'])

        if minimum_difficulty > 0 or maximum_difficulty < 100:
            must.append({"range": {"problem_difficulty": {"gte": minimum_difficulty, "lte": maximum_difficulty}}})

        if len(nested_must) > 0:
            must.append({'nested': {'path': 'categories', 'query': {'bool': {'must': nested_must}}}})

        for f in keyword_fields:
            if f in param:
                must.append({'term': {f: param[f]}})

        for f in text_fields:
            if f in param:
                must.append({'match': {f: param[f]}})

        query_json = {'query': {'match_all': {}}}
        if len(must) > 0:
            query_json = {'query': {'bool': {'must': must}}}
        return query_json


def search_problems(param, from_value, size_value, heavy = False):
    try:
        rs = requests.session()
        query_json = generate_query_params(param)
        query_json['from'] = from_value
        query_json['size'] = size_value
        search_url = 'http://{}/{}/{}/_search'.format(config.ES_HOST, _es_index_problem, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        item_list = []
        if 'hits' in response:
            for hit in response['hits']['hits']:
                data = hit['_source']
                data['id'] = hit['_id']
                item_list.append(data)
            return item_list
        return item_list
    except Exception as e:
        raise e


def search_problems_filtered_by_categories(categories):
    # logger.info('search_problems_filtered_by_categories called')
    try:
        rs = requests.session()
        should = []
        for category_id in categories:
            uc_edge = categories[category_id]
            dif_level = float(uc_edge['skill_level'])
            level_min = max(0.0, dif_level-1.5)
            level_max = min(10.0, dif_level+1.5)
            must = [
                {'nested': {'path': 'categories', 'query': {'bool': {'must': [{'term': {'categories.category_id': category_id}}]}}}},
                {"range": {"problem_difficulty": {"gte": level_min, "lte": level_max}}}
            ]
            item = {"bool": {"must": must}}
            should.append(item)

        query_json = {'query': {'match_all': {}}}
        if len(should) > 0:
            query_json = {'query': {'bool': {'should': should}}}

        query_json['from'] = 0
        query_json['size'] = _es_size
        search_url = 'http://{}/{}/{}/_search'.format(config.ES_HOST, _es_index_problem, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        item_list = []
        if 'hits' in response:
            for hit in response['hits']['hits']:
                data = hit['_source']
                data['id'] = hit['_id']
                item_list.append(data)
            return item_list
        # logger.error('Elasticsearch down, response: ' + str(response))
        return item_list
    except Exception as e:
        raise e


def get_user_problem_status(user_id, problem_id):
    try:
        rs = requests.session()
        must = [
            {'term': {'user_id': user_id}},
            {'term': {'problem_id': problem_id}}
        ]
        query_json = {'query': {'bool': {'must': must}}}
        query_json['size'] = 1
        search_url = 'http://{}/{}/{}/_search'.format(config.ES_HOST, _es_index_problem_user, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        if 'hits' in response:
            for hit in response['hits']['hits']:
                edge = hit['_source']
                edge['id'] = hit['_id']
                return edge
        return None

    except Exception as e:
        raise e


def add_user_problem_status(user_id, problem_id, data):
    try:
        rs = requests.session()
        edge = get_user_problem_status(user_id, problem_id)

        if edge is None:
            data['created_at'] = int(time.time())
            data['updated_at'] = int(time.time())
            post_url = 'http://{}/{}/{}'.format(config.ES_HOST, _es_index_problem_user, _es_type)
            response = rs.post(url=post_url, json=data, headers=_http_headers).json()
            if 'result' in response:
                return response['_id']
            raise Exception('Internal server error')

        edge_id = edge['id']
        edge.pop('id', None)

        for f in data:
            edge[f] = data[f]

        edge['updated_at'] = int(time.time())

        url = 'http://{}/{}/{}/{}'.format(config.ES_HOST, _es_index_problem_user, _es_type, edge_id)
        response = rs.put(url=url, json=edge, headers=_http_headers).json()

        if 'result' in response:
            return response['result']
        raise Exception('Internal server error')
    except Exception as e:
        raise Exception('Internal server error')


def update_problem_score(user_id, user_skill_level, updated_categories):
    # logger.info(f'update_problem_score called for: {user_id}, with skill: {user_skill_level}')
    problem_score_generator = ProblemScoreGenerator()
    problem_list = search_problems_filtered_by_categories(updated_categories)
    # logger.info(f'problem_list found of size {len(problem_list)}')

    for problem in problem_list:
        problem_id = problem['id']
        up_edge = get_user_problem_status(user_id, problem_id)
        # logger.info(f'initial up_edge {up_edge}')

        if up_edge is None:
            up_edge = {
                "problem_id": problem_id,
                "user_id": user_id,
                "relevant_score": 0,
                "status": "UNSOLVED"
            }

        if up_edge['status'] == "SOLVED":
            continue

        # logger.info(f'after non check, up_edge {up_edge}')
        dcat_list = problem.get('categories', [])
        dcat_level_list = []
        # logger.info(f'dcat_list: {dcat_list}')

        for cat in dcat_list:
            # logger.info(f'cat: {cat}')
            category_id = cat['category_id']
            if category_id in updated_categories:
                uc_edge = updated_categories[category_id]
            else:
                uc_edge = get_user_category_data(user_id, category_id)
                if uc_edge is None:
                    uc_edge = {
                        "category_id": category_id,
                        "category_root": cat['category_root'],
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
                        uc_edge[key] = 0
                updated_categories[category_id] = uc_edge
            # logger.info(f'uc_edge: {uc_edge}')
            dcat_level_list.append(uc_edge['skill_level'])
        # logger.info(f'dcat_level_list: {dcat_level_list}')
        relevant_score = problem_score_generator.generate_score(int(float(problem['problem_difficulty'])), dcat_level_list, user_skill_level)
        up_edge['relevant_score'] = relevant_score['score']
        up_edge.pop('id', None)
        # logger.info(f'final up_edge {up_edge}')
        add_user_problem_status(user_id, problem_id, up_edge)
        # logger.info(f'user problem status added')


def apply_solved_problem_for_user(user_id, problem_id, problem_details, submission_list, updated_categories, root_category_solve_count):
    # logger.info(f'apply_solved_problem_for_user for user_id: {user_id}, problem_id: {problem_id}')
    # logger.info('current updated_categories: ' + json.dumps(updated_categories))
    try:
        skill_info = Skill()
        up_edge = get_user_problem_status(user_id, problem_id)
        if up_edge is not None and up_edge['status'] == SOLVED:
            return
        rs = requests.session()
        data = {
            'user_id': user_id,
            'problem_id': problem_id,
            'submission_list': submission_list,
            'status': SOLVED
        }
        # Insert User Problem Solved Status Here
        post_url = 'http://{}/{}/{}'.format(config.ES_HOST, _es_index_problem_user, _es_type)
        response = rs.post(url=post_url, json=data, headers=_http_headers).json()

        if 'result' not in response:
            raise Exception('Internal server error')

        # Update dependent category skill
        problem_difficulty = problem_details['problem_difficulty']
        # logger.info(f'problem_difficulty: {problem_difficulty}')
        dep_cat_list = problem_details.get('categories', [])
        cat_skill_model = CategorySkillGenerator()
        marked_roots = {}
        for cat in dep_cat_list:
            # logger.info(f'dept cat: {cat}')
            category_id = cat['category_id']
            category_details = get_category_details(category_id)
            category_root = category_details['category_root']
            # logger.info(f'category_root: {category_root}')
            if category_root not in marked_roots:
                if category_root not in root_category_solve_count:
                    root_category_solve_count[category_root] = 0
                root_category_solve_count[category_root] += 1
                marked_roots[category_root] = 1
            if category_id in updated_categories:
                uc_edge = updated_categories[category_id]
            else:
                uc_edge = get_user_category_data(user_id, category_id)
                if uc_edge:
                    uc_edge['old_skill_level'] = uc_edge['skill_level']
                    uc_edge.pop('id', None)
            # logger.info(f'uc_edge from es: {uc_edge}')
            if uc_edge is None:
                uc_edge = {
                    "category_id": category_id,
                    "category_root": category_root,
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
                    uc_edge[key] = 0

            # logger.info(f'current uc_edge: {uc_edge}')
            dif_key = 'scd_' + str(int(problem_difficulty))
            uc_edge[dif_key] += 1
            problem_factor = category_details.get('factor', 1)
            added_skill = cat_skill_model.get_score_for_latest_solved_problem(problem_difficulty, uc_edge[dif_key], problem_factor)
            # logger.info(f'found get_score_for_latest_solved_problem: {added_skill}')
            uc_edge['skill_value'] += added_skill
            uc_edge['solve_count'] += 1
            uc_edge['skill_title'] = skill_info.get_skill_title(uc_edge['skill_value'])
            uc_edge['skill_level'] = skill_info.get_skill_level_from_skill(uc_edge['skill_value'])
            score_percentage = float(category_details['score_percentage'])
            uc_edge['skill_value_by_percentage'] = uc_edge['skill_value']*score_percentage/100
            # logger.info(f'add uc_edge: {uc_edge}')
            updated_categories[category_id] = uc_edge
            # logger.info(f'saved at category_id: {category_id}')
            # logger.info('apply_solved_problem_for_user completed')
    except Exception as e:
        logger.error(f'Exception occurred: {e}')
        raise Exception('Internal server error')




######################### SYNC SERVICES #########################


def sync_problems(user_id, oj_problem_set):
    logger.info(f'sync_problems called for {user_id}')
    try:
        category_score_generator = CategoryScoreGenerator()
        updated_categories = {}
        root_category_solve_count = {}

        for problem_set in oj_problem_set:
            # Change here
            for problem in problem_set['problem_list']:
                problem_stat = problem_set['problem_list'][problem]
                submission_list = problem_stat['submission_list']
                problem_db = search_problems({'problem_id': problem, 'oj_name': problem_set['oj_name'], 'active_status': approved}, 0, 1)
                if len(problem_db) == 0:
                    continue
                problem_id = problem_db[0]['id']
                if len(problem_db) > 1:
                    logger.error('Multiple problem with same id found')
                apply_solved_problem_for_user(user_id, problem_id, problem_db[0], submission_list, updated_categories, root_category_solve_count)

        logger.info('apply_solved_problem_for_user completed for all problems')
        marked_categories = dict(updated_categories)
        logger.info(f'marked_categories: {marked_categories}')

        for category_id in marked_categories:
            # logger.info(f'category id inside marked_categories: {category_id}')
            uc_edge = marked_categories[category_id]
            # logger.info(f'uc_edge 1: {uc_edge}')
            # UPDATE OWN CONTRIBUTION
            old_cont = category_score_generator.get_own_difficulty_based_score(uc_edge['old_skill_level'])
            new_cont = category_score_generator.get_own_difficulty_based_score(uc_edge['skill_level'])
            cont_dx = new_cont - old_cont
            uc_edge['relevant_score'] += cont_dx
            # logger.info(f'uc_edge 2: {uc_edge}')
            updated_categories[category_id] = uc_edge
            # UPDATE DEPENDENT CATEGORY CONTRIBUTION
            dependent_cat_list = find_dependent_category_list(category_id)
            # logger.info(f'dependent_cat_list: {dependent_cat_list}')
            for dcat in dependent_cat_list:
                dcat_id = dcat['category_id']
                dcat_category_root = dcat['category_info']['category_root']
                # logger.info(f'dcat_category_root: {dcat_category_root}')
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

                logger.info(f'dcat_uc_edge: {dcat_uc_edge}')
                updated_categories[dcat_id] = dcat_uc_edge

        logger.info('process of mark categories completed')

        for category_id in updated_categories:
            uc_edge = updated_categories[category_id]
            uc_edge.pop('old_skill_level', None)
            uc_edge.pop('id', None)
            add_user_category_data(user_id, category_id, uc_edge)

        logger.info('updated root categories')
        root_category_list = search_categories({"category_root": "root"}, 0, _es_size)
        logger.info(f'root_category_list: {root_category_list}')
        skill = Skill()
        user_skill = update_root_category_skill_for_user(user_id, root_category_list, root_category_solve_count)
        user_skill_level = skill.get_skill_level_from_skill(user_skill)
        logger.info(f'Final user_skill: {user_skill}, user_skill_level: {user_skill_level}')
        sync_overall_stat_for_user(user_id, user_skill)
        logger.info('sync_overall_stat_for_user completed')
        if len(updated_categories) > 0:
            update_problem_score(user_id, user_skill_level, updated_categories)
        logger.info(f'sync_problems completed for {user_id}')
    except Exception as e:
        raise e


def synch_user_problem(user_id):
    logger.info(f'synch_user_problem for user_id: {user_id}')
    try:
        uva = UvaScrapper()
        codeforces = CodeforcesScrapper()
        spoj = SpojScrapper()
        codechef = CodechefScrapper()
        lightoj = LightOJScrapper()

        user_info = get_user_details(user_id)
        # print('user_info: ', user_info)
        allowed_judges = ['codeforces', 'uva', 'codechef', 'spoj', 'lightoj']

        oj_problem_set = []

        if 'codeforces' in allowed_judges:
            handle = user_info.get('codeforces_handle', None)
            # print('Codeforces: ', handle)
            if handle:
                problem_stat = codeforces.get_user_info_heavy(handle)
                oj_problem_set.append({
                    'problem_list': problem_stat['solved_problems'],
                    'oj_name': 'codeforces'
                })
                logger.info(f'codeforces problem_stat: {problem_stat}')
                # print('problem_stat: ',problem_stat)

        # print('codeforces scrapping completed')

        if 'codechef' in allowed_judges:
            handle = user_info.get('codechef_handle', None)
            # print('codechef: ', handle)
            if handle:
                problem_stat = codechef.get_user_info_heavy(handle)
                oj_problem_set.append({
                    'problem_list': problem_stat['solved_problems'],
                    'oj_name': 'codechef'
                })

        # print('codechef scrapping completed')

        if 'uva' in allowed_judges:
            handle = user_info.get('uva_handle', None)
            # print('uva: ', handle)
            if handle:
                problem_stat = uva.get_user_info_heavy(handle)
                oj_problem_set.append({
                    'problem_list': problem_stat['solved_problems'],
                    'oj_name': 'uva'
                })

        # print('uva scrapping completed')

        if 'spoj' in allowed_judges:
            handle = user_info.get('spoj_handle', None)
            # print('spoj: ', handle)
            if handle:
                problem_stat = spoj.get_user_info_heavy(handle)
                oj_problem_set.append({
                    'problem_list': problem_stat['solved_problems'],
                    'oj_name': 'spoj'
                })

        # print('spoj scrapping completed')

        if 'lightoj' in allowed_judges:
            handle = user_info.get('lightoj_handle', None)
            logger.info(f'lightoj handle: {handle}')
            # print(f'lightoj handle: {handle}')
            if handle:
                credentials = {
                    'username': os.getenv('LIGHTOJ_USERNAME'),
                    'password': os.getenv('LIGHTOJ_PASSWORD')
                }
                problem_stat = lightoj.get_user_info_heavy(handle, credentials)
                # print('problem_stat: ', problem_stat)
                oj_problem_set.append({
                    'problem_list': problem_stat['solved_problems'],
                    'oj_name': 'lightoj'
                })

        # print('lightoj scrapping completed')

        sync_problems(user_id, oj_problem_set)

    except Exception as e:
        raise e


def user_problem_data_sync(user_id):
    synch_user_problem(user_id)

    notification_data = {
        'user_id': user_id,
        'sender_id': 'System',
        'notification_type': 'System Notification',
        'redirect_url': '',
        'notification_text': 'Your problem data has been synced by',
        'status': 'UNREAD',
    }
    add_notification(notification_data)


def user_problem_sync(user_id):
    user_problem_data_sync(user_id)
    remove_pending_job(user_id)


def team_training_model_sync(team_id):
    global rs
    auth_header = get_header()
    logger.debug('team_training_model_sync called for: ' + str(team_id))
    url = team_training_model_sync_api + team_id
    response = rs.put(url=url, json={}, headers=auth_header).json()
    logger.debug('response: ' + str(response))


def search_job():
    global rs
    auth_header = get_header()
    logger.debug('search_job called')
    # print('job_search_url: ', job_search_url)
    # print('auth_header: ', auth_header)
    response = rs.post(url=job_search_url, json={'status': 'PENDING'}, headers=auth_header).json()
    logger.debug('response: ' + str(response))
    # print(response)
    return response['job_list']


def update_job(job_id, status):
    global rs
    auth_header = get_header()
    logger.debug('update_job called')
    url = job_url + job_id
    response = rs.put(url=url, json={'status': status}, headers=auth_header).json()
    logger.debug('response: ' + str(response))


def db_job():
    curtime = int(time.time())
    logger.info('RUN CRON JOB FOR SYNCING DATA AT: ' + str(curtime))
    while(1):
        pending_job_list = search_job()
        if len(pending_job_list) == 0:
            break
        cur_job = pending_job_list[0]
        logger.debug('PROCESS JOB: ' + json.dumps(cur_job))
        update_job(cur_job['id'], 'PROCESSING')
        if cur_job['job_type'] == 'USER_SYNC':
            user_problem_sync(cur_job['job_ref_id'])
        else:
            team_training_model_sync(cur_job['job_ref_id'])

        update_job(cur_job['id'], 'COMPLETED')
        logger.debug('COMPLETED JOB: ' + json.dumps(cur_job))


cron_job = BackgroundScheduler(daemon=True)
cron_job.add_job(db_job, 'interval', seconds=6000)
cron_job.start()


if __name__ == '__main__':
    logger.info('Sync Job Script successfully started running')
    # print('Sync Job Script successfully started running')
    # print('Run initial job')
    db_job()
    while(1):
        pass
