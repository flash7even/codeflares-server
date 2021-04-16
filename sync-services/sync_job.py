import logging
import os
import re
import time
import json
import unittest
import requests
import math
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
_es_index_user_team_edge = 'cfs_user_team_edges'
_es_index_team = 'cfs_teams'
_es_type = '_doc'
_es_size = 10000

_es_max_solved_problem = 10000
_bucket_size = 100

SOLVED = 'SOLVED'
UNSOLVED = 'UNSOLVED'
SOLVE_LATER = 'SOLVE_LATER'
FLAGGED = 'FLAGGED'
approved = 'approved'
READ = 'READ'
UNREAD = 'UNREAD'

uva = UvaScrapper()
codeforces = CodeforcesScrapper()
spoj = SpojScrapper()
codechef = CodechefScrapper()
lightoj = LightOJScrapper()
skill_info = Skill()
category_score_generator = CategoryScoreGenerator()
cat_skill_model = CategorySkillGenerator()


######################### REDIS SERVICES STARTS #########################


def check_pending_job(user_id):
    try:
        redis_user_pending_job_key = f'{config.REDIS_PREFIX_USER_PENDING_JOB}:{user_id}'
        if redis_client.exists(redis_user_pending_job_key):
            return True
        else:
            return False
    except Exception as e:
        raise Exception('Internal server error')


def add_pending_job(user_id):
    try:
        redis_user_pending_job_key = f'{config.REDIS_PREFIX_USER_PENDING_JOB}:{user_id}'
        redis_client.set(redis_user_pending_job_key, 1)
    except Exception as e:
        raise Exception('Internal server error')


def remove_pending_job(user_id):
    try:
        redis_user_pending_job_key = f'{config.REDIS_PREFIX_USER_PENDING_JOB}:{user_id}'
        redis_client.delete(redis_user_pending_job_key)
    except Exception as e:
        raise Exception('Internal server error')


def add_new_job(user_id):
    try:
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
    except Exception as e:
        raise Exception('Internal server error')






######################### AUTH SERVICES #########################


def get_access_token():
    try:
        global rs
        login_data = {
            "username": ADMIN_USER,
            "password": ADMIN_PASSWORD
        }
        response = rs.post(url=login_api, json=login_data, headers=_http_headers).json()
        return response['access_token']
    except Exception as e:
        raise Exception('Internal server error')


def get_header():
    try:
        global rs
        global access_token
        if access_token is None:
            access_token = get_access_token()
        auth_headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }
        return auth_headers
    except Exception as e:
        raise Exception('Internal server error')






######################### NOTIFICATION SERVICES #########################


def add_notification(data):
    try:
        global rs
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




def search_user_ids(param, from_val, size_val):
    try:
        global rs
        must = []
        text_fields = ['username', 'email', 'mobile']
        keyword_fields = ['user_role']

        for k in text_fields:
            if k in param:
                must.append({'match': {k: param[k]}})

        for k in keyword_fields:
            if k in param:
                must.append({'term': {k: param[k]}})

        query_json = {'query': {'match_all': {}}}
        if len(must) > 0:
            query_json = {'query': {'bool': {'must': must}}}

        query_json['_source'] = False
        query_json['from'] = from_val
        query_json['size'] = size_val
        search_url = 'http://{}/{}/{}/_search'.format(config.ES_HOST, _es_index_user, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()

        if 'hits' in response:
            data = []
            for hit in response['hits']['hits']:
                data.append(hit['_id'])
            return data
        logger.error('Elasticsearch down, response : ' + str(response))
        raise Exception('Internal server error')
    except Exception as e:
        raise e


def get_user_details_by_handle_name(username):
    try:
        global rs
        query_json = {'query': {'bool': {'must': [{'match': {'username': username}}]}}}
        search_url = 'http://{}/{}/{}/_search'.format(config.ES_HOST, _es_index_user, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        if 'hits' in response:
            for hit in response['hits']['hits']:
                data = hit['_source']
                data['id'] = hit['_id']
                return data
        return None
    except Exception as e:
        raise e


def get_user_details(user_id):
    try:
        global rs
        search_url = 'http://{}/{}/{}/{}'.format(config.ES_HOST, _es_index_user, _es_type, user_id)
        response = rs.get(url=search_url, headers=_http_headers).json()
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
        global rs
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
    try:
        global rs
        must = [
            {'term': {'category_root': 'root'}},
            {'term': {'user_id': user_id}},
        ]
        query_json = {'query': {'bool': {'must': must}}}
        query_json['size'] = _es_size
        search_url = 'http://{}/{}/{}/_search'.format(config.ES_HOST, _es_index_user_category, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        if 'hits' not in response:
            raise Exception('Internal server error')
        skill_value = 0
        if 'hits' in response:
            for hit in response['hits']['hits']:
                data = hit['_source']
                skill_value += float(data['skill_value_by_percentage'])
        return skill_value
    except Exception as e:
        raise e


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
        global rs
        ignore_fields = ['username', 'password']
        search_url = 'http://{}/{}/{}/{}'.format(config.ES_HOST, _es_index_user, _es_type, user_id)
        response = rs.get(url=search_url, headers=_http_headers).json()
        if 'found' in response:
            if response['found']:
                user = response['_source']
                for key in user_data:
                    if key not in ignore_fields:
                        user[key] = user_data[key]
                response = rs.put(url=search_url, json=user, headers=_http_headers).json()
                if 'result' in response:
                    return response['result']
        logger.error('Elasticsearch down')
        return response
    except Exception as e:
        raise e






######################### CATEGORY SERVICES #########################




def find_category_dependency_list_for_multiple_categories(category_list):
    try:
        dependent_categories = []
        for category in category_list:
            dep_list = find_category_dependency_list(category)
            for category_data in dep_list:
                category_id = category_data['category_id']
                if category_id not in dependent_categories:
                    dependent_categories.append(category_id)
        return dependent_categories
    except Exception as e:
        raise e


def get_user_category_data(user_id, category_id):
    try:
        global rs
        must = [
            {'term': {'user_id': user_id}},
            {'term': {'category_id': category_id}}
        ]
        query_json = {'query': {'bool': {'must': must}}}
        query_json['size'] = 1
        search_url = 'http://{}/{}/{}/_search'.format(config.ES_HOST, _es_index_user_category, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        if 'hits' in response:
            if response['hits']['total']['value'] > 1:
                logger.error(f'Abnormal user category edges: {response}')
                raise Exception('Abnormal user category edges')
            for hit in response['hits']['hits']:
                edge = hit['_source']
                edge['id'] = hit['_id']
                return edge
        return None
    except Exception as e:
        raise e


def get_category_details(cat_id):
    try:
        global rs
        search_url = 'http://{}/{}/{}/{}'.format(config.ES_HOST, _es_index_category, _es_type, cat_id)
        response = rs.get(url=search_url, headers=_http_headers).json()
        if 'found' in response:
            if response['found']:
                data = response['_source']
                data['category_id'] = response['_id']
                data['problem_count'] = 0
                return data
        return None
    except Exception as e:
        raise e


def find_category_dependency_list(category_id_1):
    try:
        global rs
        must = [
            {'term': {'category_id_1': category_id_1}}
        ]
        query_json = {'query': {'bool': {'must': must}}}
        query_json['size'] = _es_size
        search_url = 'http://{}/{}/{}/_search'.format(config.ES_HOST, _es_index_category_dependency, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        item_list = []
        if 'hits' in response:
            for hit in response['hits']['hits']:
                category = hit['_source']
                category.pop('category_id_1', None)
                category['category_info'] = get_category_details(category['category_id_2'])
                category['category_id'] = category['category_id_2']
                category.pop('category_id_2', None)
                item_list.append(category)
            return item_list
        logger.error('Elasticsearch down, response: ' + str(response))
        return item_list
    except Exception as e:
        raise e


def find_dependent_category_list(category_id_2):
    try:
        global rs
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
        global rs
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


def clean_user_category_history(user_id):
    try:
        logger.info(f'clean_user_problem_history for: user_id: {user_id}')
        global rs
        must = [
            {'term': {'user_id': user_id}}
        ]
        query_json = {'query': {'bool': {'must': must}}}
        search_url = 'http://{}/{}/_delete_by_query'.format(config.ES_HOST, _es_index_user_category)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        if 'deleted' not in response:
            logger.error('ES Down')
            raise Exception(str(response))
    except Exception as e:
        raise e


def search_categories(param, from_value, size_value):
    try:
        global rs
        must = []
        keyword_fields = ['category_title', 'category_root']

        for f in param:
            if f in keyword_fields:
                if param[f]:
                    must.append({'term': {f: param[f]}})
            else:
                if param[f]:
                    must.append({'match': {f: param[f]}})

        query_json = {'query': {'match_all': {}}}
        if len(must) > 0:
            query_json = {'query': {'bool': {'must': must}}}

        if 'category_root' not in param:
            if 'query' in query_json and 'bool' in query_json['query']:
                query_json['query']['bool']['must_not'] = [{'term': {'category_root': 'root'}}]
            else:
                query_json = {'query': {'bool': {'must_not': [{'term': {'category_root': 'root'}}]}}}

        query_json['from'] = from_value
        query_json['size'] = size_value
        search_url = 'http://{}/{}/{}/_search'.format(config.ES_HOST, _es_index_category, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        item_list = []
        if 'hits' in response:
            for hit in response['hits']['hits']:
                category = hit['_source']
                category['category_id'] = hit['_id']
                category['problem_count'] = 0
                category['solve_count'] = 0
                item_list.append(category)
            return item_list
        logger.error('Elasticsearch down, response: ' + str(response))
        return item_list
    except Exception as e:
        raise e


def update_root_category_skill_for_user(user_id, root_category_list, root_category_solve_count):
    # logger.info(f'update_root_category_skill_for_user called for: {user_id}')
    try:
        global rs
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
                new_solve_count = root_category_solve_count.get(cat['category_name'], 0)
                uc_edge = get_user_category_data(user_id, cat['category_id'])
                if uc_edge is None:
                    uc_edge = {
                        "category_id": cat['category_id'],
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
                uc_edge['skill_title'] = skill_info.get_skill_title(uc_edge['skill_value'])
                uc_edge['skill_level'] = skill_info.get_skill_level_from_skill(uc_edge['skill_value'])
                uc_edge['skill_value_by_percentage'] = uc_edge['skill_value'] * float(cat['score_percentage']) / 100.0
                user_skill_sum += uc_edge['skill_value_by_percentage']
                uc_edge.pop('id', None)
                add_user_category_data(user_id, cat['category_id'], uc_edge)
        return user_skill_sum
    except Exception as e:
        raise Exception('Internal server error')






######################### PROBLEM SERVICES #########################



def available_problems_for_user(user_id):
    try:
        param = {
            'active_status': approved
        }
        problem_list = search_problems(param, 0, _es_size)
        available_list = []
        for problem in problem_list:
            edge = get_user_problem_status(user_id, problem['id'])
            if edge is None:
                available_list.append(problem)
            else:
                status = edge.get('status', None)
                if status == UNSOLVED:
                    available_list.append(problem)
        return available_list
    except Exception as e:
        raise e


def find_problem_dependency_list(problem_id):
    try:
        global rs
        search_url = 'http://{}/{}/{}/{}'.format(config.ES_HOST, _es_index_problem, _es_type, problem_id)
        response = rs.get(url=search_url, headers=_http_headers).json()
        item_list = []
        if 'found' in response:
            if response['found']:
                data = response['_source']
                categories = data.get('categories', [])
                for category in categories:
                    category['category_info'] = get_category_details(category['category_id'])
                    item_list.append(category)
        return item_list
    except Exception as e:
        raise e


def generate_query_params_for_problem_index(param):
    try:
        must = []
        nested_must = []
        keyword_fields = ['problem_title', 'problem_id', 'problem_difficulty', 'oj_name', 'active_status']
        text_fields = ['problem_name']

        if 'category_id' in param:
            nested_must.append({'term': {'categories.category_id': param['category_id']}})
        if 'category_name' in param:
            nested_must.append({'term': {'categories.category_name': param['category_name']}})
        if 'category_root' in param:
            nested_must.append({'term': {'categories.category_root': param['category_root']}})

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
    except Exception as e:
        raise e


def search_problems(param, from_value, size_value):
    try:
        global rs
        query_json = generate_query_params_for_problem_index(param)
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


def search_problems_filtered_by_categories_for_users(uc_edge_list):
    try:
        global rs
        should = []
        for category_id in uc_edge_list:
            uc_edge = uc_edge_list[category_id]
            dif_level = float(uc_edge['skill_level'])
            level_min = max(0.0, dif_level-2)
            level_max = min(10.0, dif_level+2)
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
        return item_list
    except Exception as e:
        raise e


def get_user_problem_status(user_id, problem_id):
    try:
        global rs
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
        global rs
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


def clean_user_problem_history(user_id):
    try:
        logger.info(f'clean_user_problem_history for: user_id: {user_id}')
        global rs
        must = [
            {'term': {'user_id': user_id}}
        ]
        query_json = {'query': {'bool': {'must': must}}}
        search_url = 'http://{}/{}/_delete_by_query'.format(config.ES_HOST, _es_index_problem_user)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        if 'deleted' not in response:
            logger.error('ES Down')
            raise Exception(str(response))
    except Exception as e:
        raise e


def update_user_problem_score(user_id, user_skill_level, updated_categories):
    # logger.info(f'update_user_problem_score called for: {user_id}, with skill: {user_skill_level}')
    try:
        problem_score_generator = ProblemScoreGenerator()
        problem_list = search_problems_filtered_by_categories_for_users(updated_categories)

        for problem in problem_list:
            problem_id = problem['id']
            up_edge = get_user_problem_status(user_id, problem_id)

            if up_edge is None:
                up_edge = {
                    "problem_id": problem_id,
                    "user_id": user_id,
                    "relevant_score": 0,
                    "status": "UNSOLVED"
                }

            if up_edge['status'] == SOLVED:
                continue

            dcat_list = problem.get('categories', [])
            dcat_level_list = []

            for cat in dcat_list:
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
                dcat_level_list.append(uc_edge['skill_level'])
            relevant_score = problem_score_generator.generate_score(int(float(problem['problem_difficulty'])), dcat_level_list, user_skill_level)
            up_edge['relevant_score'] = relevant_score['score']
            up_edge.pop('id', None)
            # logger.info(f'final up_edge {up_edge}')
            add_user_problem_status(user_id, problem_id, up_edge)
            # logger.info(f'user problem status added')
    except Exception as e:
        raise Exception('Internal server error')


def apply_solved_problem_for_user(user_id, problem_id, problem_details, submission_list, updated_categories, root_category_solve_count):
    # logger.info(f'apply_solved_problem_for_user for user_id: {user_id}, problem_id: {problem_id}')
    try:
        up_edge = get_user_problem_status(user_id, problem_id)
        if up_edge is not None and up_edge['status'] == SOLVED:
            return
        global rs
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

        problem_difficulty = int(math.ceil(float(problem_details['problem_difficulty'])))
        dep_cat_list = problem_details.get('categories', [])

        # Update skill values for problem dependent categories
        for dcat in dep_cat_list:
            dcat_id = dcat['category_id']
            category_details = get_category_details(dcat_id)
            category_root = category_details['category_root']
            if category_root not in root_category_solve_count:
                root_category_solve_count[category_root] = 0
            root_category_solve_count[category_root] += 1
            if dcat_id in updated_categories:
                uc_edge = updated_categories[dcat_id]
            else:
                uc_edge = get_user_category_data(user_id, dcat_id)
                if uc_edge:
                    uc_edge['old_skill_level'] = uc_edge['skill_level']
                    uc_edge.pop('id', None)

            if uc_edge is None:
                uc_edge = {
                    "category_id": dcat_id,
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

            dif_key = 'scd_' + str(problem_difficulty)
            uc_edge[dif_key] += 1
            problem_factor = category_details.get('factor', 1)
            added_skill = cat_skill_model.get_score_for_latest_solved_problem(problem_difficulty, uc_edge[dif_key], problem_factor)
            uc_edge['skill_value'] += added_skill
            uc_edge['solve_count'] += 1
            uc_edge['skill_title'] = skill_info.get_skill_title(uc_edge['skill_value'])
            uc_edge['skill_level'] = skill_info.get_skill_level_from_skill(uc_edge['skill_value'])
            score_percentage = float(category_details['score_percentage'])
            uc_edge['skill_value_by_percentage'] = uc_edge['skill_value']*score_percentage/100
            updated_categories[dcat_id] = uc_edge
        # logger.info('apply_solved_problem_for_user completed')
    except Exception as e:
        logger.error(f'Exception occurred: {e}')
        raise Exception('Internal server error')





######################### USER SYNC SERVICES #########################



def sync_problem_bucket(user_id, oj_problem_set):
    # logger.info(f'sync_problem_bucket called for {user_id}')
    try:
        updated_categories = {}
        root_category_solve_count = {}

        # First process all the new solved problems:
        for problem_set in oj_problem_set:
            for problem_id in problem_set['problem_list']:
                submission_list = problem_set['problem_list'][problem_id]['submission_list']
                problem_db = search_problems({'problem_id': problem_id, 'oj_name': problem_set['oj_name'], 'active_status': approved}, 0, 1)
                if len(problem_db) != 1:
                    logger.error(f'Abnormal data for problem: {problem_id}, len: {len(problem_set["problem_list"])}')
                    continue
                es_problem_id = problem_db[0]['id']
                # Apply after effects for new solved problem
                apply_solved_problem_for_user(user_id, es_problem_id, problem_db[0], submission_list, updated_categories, root_category_solve_count)

        marked_categories = dict(updated_categories)
        for category_id in marked_categories:
            uc_edge = marked_categories[category_id]
            # UPDATE OWN CONTRIBUTION
            old_contribution = category_score_generator.get_own_difficulty_based_score(uc_edge['old_skill_level'])
            new_contribution = category_score_generator.get_own_difficulty_based_score(uc_edge['skill_level'])
            cont_dx = new_contribution - old_contribution
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
                old_contribution = category_score_generator.get_dependent_score(uc_edge['old_skill_level'], dependency_percentage)
                new_contribution = category_score_generator.get_dependent_score(uc_edge['skill_level'], dependency_percentage)
                cont_dx = new_contribution - old_contribution
                dcat_uc_edge['relevant_score'] += cont_dx
                updated_categories[dcat_id] = dcat_uc_edge

        for category_id in updated_categories:
            uc_edge = updated_categories[category_id]
            uc_edge.pop('old_skill_level', None)
            uc_edge.pop('id', None)
            add_user_category_data(user_id, category_id, uc_edge)

        root_category_list = search_categories({"category_root": "root"}, 0, _es_size)
        user_skill = update_root_category_skill_for_user(user_id, root_category_list, root_category_solve_count)
        user_skill_level = skill_info.get_skill_level_from_skill(user_skill)
        sync_overall_stat_for_user(user_id, user_skill)
        if len(updated_categories) > 0:
            update_user_problem_score(user_id, user_skill_level, updated_categories)
        # logger.info(f'sync_problem_bucket completed for {user_id}')
    except Exception as e:
        raise e


def synch_user_problem_data_from_ojs(user_id):
    logger.info(f'synch_user_problem_data_from_ojs for user_id: {user_id}')
    try:
        user_info = get_user_details(user_id)
        allowed_judges = ['codeforces', 'uva', 'codechef', 'spoj', 'lightoj']

        oj_problem_set = []

        logger.info('Scrap codeforces Problems')
        if 'codeforces' in allowed_judges:
            handle = user_info.get('codeforces_handle', None)
            if handle:
                solved_problems = codeforces.get_user_info_heavy(handle)
                oj_problem_set.append({
                    'problem_list': solved_problems,
                    'oj_name': 'codeforces'
                })
        logger.info('Scrap codeforces Completed')

        logger.info('Scrap codechef Problems')
        if 'codechef' in allowed_judges:
            handle = user_info.get('codechef_handle', None)
            if handle:
                solved_problems = codechef.get_user_info_heavy(handle)
                oj_problem_set.append({
                    'problem_list': solved_problems,
                    'oj_name': 'codechef'
                })
        logger.info('Scrap codechef Completed')

        logger.info('Scrap uva Problems')
        if 'uva' in allowed_judges:
            handle = user_info.get('uva_handle', None)
            if handle:
                solved_problems = uva.get_user_info_heavy(handle)
                oj_problem_set.append({
                    'problem_list': solved_problems,
                    'oj_name': 'uva'
                })
        logger.info('Scrap uva Completed')

        logger.info('Scrap spoj Problems')
        if 'spoj' in allowed_judges:
            handle = user_info.get('spoj_handle', None)
            if handle:
                solved_problems = spoj.get_user_info_heavy(handle)
                oj_problem_set.append({
                    'problem_list': solved_problems,
                    'oj_name': 'spoj'
                })
        logger.info('Scrap spoj Completed')

        logger.info('Scrap lightoj Problems')
        if 'lightoj' in allowed_judges:
            handle = user_info.get('lightoj_handle', None)
            if handle:
                credentials = {
                    'username': os.getenv('LIGHTOJ_USERNAME'),
                    'password': os.getenv('LIGHTOJ_PASSWORD')
                }
                solved_problems = lightoj.get_user_info_heavy(handle, credentials)
                # print('problem_stat: ', problem_stat)
                oj_problem_set.append({
                    'problem_list': solved_problems,
                    'oj_name': 'lightoj'
                })
        logger.info('Scrap lightoj Completed')

        sync_problem_bucket(user_id, oj_problem_set)

    except Exception as e:
        raise e


def user_problem_data_sync_process(user_id):
    try:
        synch_user_problem_data_from_ojs(user_id)

        notification_data = {
            'user_id': user_id,
            'sender_id': 'System',
            'notification_type': 'System Notification',
            'redirect_url': '',
            'notification_text': 'Your problem data has been synced by',
            'status': 'UNREAD',
        }
        add_notification(notification_data)
    except Exception as e:
        raise Exception('Internal server error')






######################### TEAM SERVICES #########################



def search_team_ids(param, from_val, size_val):
    try:
        global rs
        must = []
        keyword_fields = ['team_leader_id', 'team_type']

        for f in param:
            if f in keyword_fields:
                must.append({'term': {f: param[f]}})
            else:
                must.append({'match': {f: param[f]}})

        query_json = {'query': {'match_all': {}}}
        if len(must) > 0:
            query_json = {'query': {'bool': {'must': must}}}

        query_json['from'] = from_val
        query_json['size'] = size_val
        query_json['_source'] = False
        search_url = 'http://{}/{}/{}/_search'.format(config.ES_HOST, _es_index_team, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        if 'hits' in response:
            item_list = []
            for hit in response['hits']['hits']:
                item_list.append(hit['_id'])
            return item_list
        logger.error('Elasticsearch down, response: ' + str(response))
        raise Exception('Internal server error')

    except Exception as e:
        raise e


def update_team_details(team_id, post_data):
    try:
        global rs
        search_url = 'http://{}/{}/{}/{}'.format(config.ES_HOST, _es_index_team, _es_type, team_id)
        response = rs.get(url=search_url, headers=_http_headers).json()
        if 'found' in response:
            if response['found']:
                data = response['_source']
                for key, value in post_data.items():
                    data[key] = value
                data['updated_at'] = int(time.time())
                response = rs.put(url=search_url, json=data, headers=_http_headers).json()
                if 'result' in response:
                    return response['result']
                else:
                    logger.error('Elasticsearch down, response: ' + str(response))
                    return response
            return {'message': 'not found'}
        logger.error('Elasticsearch down, response: ' + str(response))
        return response

    except Exception as e:
        raise e


def get_all_users_from_team(team_id):
    try:
        global rs
        must = [
            {'term': {'team_id': team_id}},
        ]
        query_json = {'query': {'bool': {'must': must}}}
        query_json['size'] = _es_size
        search_url = 'http://{}/{}/{}/_search'.format(config.ES_HOST, _es_index_user_team_edge, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        item_list = []
        if 'hits' in response:
            for hit in response['hits']['hits']:
                data = hit['_source']
                data['id'] = hit['_id']
                item_list.append(data)
        return item_list
    except Exception as e:
        raise e


def get_team_details(team_id):
    try:
        global rs
        search_url = 'http://{}/{}/{}/{}'.format(config.ES_HOST, _es_index_team, _es_type, team_id)
        response = rs.get(url=search_url, headers=_http_headers).json()

        if 'found' in response:
            if response['found']:
                data = response['_source']
                data['id'] = response['_id']
                data['member_list'] = get_all_users_from_team(team_id)
                return data
            raise Exception('Team not found')
        logger.error('Elasticsearch down, response: ' + str(response))
        raise Exception('Internal server error')

    except Exception as e:
        raise e






######################### TEAM SYNC SERVICES #########################



def find_problems_for_user_by_status_filtered(status, user_id):
    try:
        global rs
        should = []
        for s in status:
            should.append({'term': {'status': s}})

        must = [
            {'term': {'user_id': user_id}},
            {"bool": {"should": should}}
        ]
        query_json = {'query': {'bool': {'must': must}}}
        query_json['size'] = _es_max_solved_problem
        search_url = 'http://{}/{}/{}/_search'.format(config.ES_HOST, _es_index_problem_user, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()

        problem_list = []
        if 'hits' in response:
            for hit in response['hits']['hits']:
                edge = hit['_source']
                problem_list.append(edge['problem_id'])
        return problem_list
    except Exception as e:
        raise e


def category_wise_problem_solve_for_users(user_list):
    try:
        solved_problems = []
        for user_id in user_list:
            cur_list = find_problems_for_user_by_status_filtered(['SOLVED'], user_id)
            for problem in cur_list:
                if problem not in solved_problems:
                    solved_problems.append(problem)

        cnt_dict = {}
        category_list = search_categories({}, 0, _es_size)
        for category in category_list:
            category_id = category['category_id']
            param = {
                "category_id": category_id,
                'active_status': approved
            }
            problem_list = search_problems(param, 0, _es_size)
            for problem in problem_list:
                problem_id = problem['id']
                problem_diff = int(float(problem['problem_difficulty']))
                if category_id not in cnt_dict:
                    cnt_dict[category_id] = {
                        'total_count': 0,
                        'difficulty_wise_count': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
                    }
                if problem_id in solved_problems:
                    cnt_dict[category_id]['difficulty_wise_count'][problem_diff] += 1
                    cnt_dict[category_id]['total_count'] += 1
        for cat in category_list:
            cat_id = cat['category_id']
            cat['solved_stat'] = cnt_dict.get(cat_id, {'total_count': 0, 'difficulty_wise_count': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]})
        return category_list
    except Exception as e:
        raise e


def generate_sync_data_for_category(user_id, category):
    try:
        category_skill_generator = CategorySkillGenerator()
        factor = float(category.get('factor', 1))
        skill_stat = category_skill_generator.generate_skill(category['solved_stat']['difficulty_wise_count'], factor)

        dependent_skill_level = []
        dependent_categories = find_category_dependency_list(category['category_id'])
        for dcat in dependent_categories:
            category_details = get_user_category_data(user_id, dcat['category_id'])
            category_level = 0
            if category_details:
                category_level = category_details.get('skill_level', 0)
            dependent_skill_level.append(category_level)

        category_score_generator = CategoryScoreGenerator()
        cat_score = category_score_generator.generate_score(dependent_skill_level, skill_stat['level'])
        skill_obj = Skill()

        category_percentage = float(category.get('score_percentage', 100))

        data = {
            'relevant_score': cat_score['score'],
            'skill_value': skill_stat['skill'],
            'skill_value_by_percentage': float(skill_stat['skill'])*category_percentage/100.0,
            'skill_level': skill_stat['level'],
            'skill_title': skill_obj.get_skill_title(skill_stat['skill']),
            'solve_count': category['solved_stat']['total_count'],
            'category_root': category['category_root'],
        }
        return data
    except Exception as e:
        raise e


def sync_category_score_for_team(team_id):
    try:
        team_details = get_team_details(team_id)
        user_list = []
        for member in team_details['member_list']:
            user_details = get_user_details_by_handle_name(member['user_handle'])
            if user_details is None:
                continue
            user_list.append(user_details['id'])

        category_list = category_wise_problem_solve_for_users(user_list)
        for category in category_list:
            if category['category_root'] == 'root':
                continue
            data = generate_sync_data_for_category(team_id, category)
            add_user_category_data(team_id, category['category_id'], data)
    except Exception as e:
        raise e


def root_category_solved_count_by_solved_problem_list(solve_problems):
    try:
        root_solved_count = {}
        for problem in solve_problems:
            dependent_categories = find_problem_dependency_list(problem)
            for category in dependent_categories:
                if 'category_info' in category and category['category_info']:
                    category_root = category['category_info']['category_root']
                    if category_root not in root_solved_count:
                        root_solved_count[category_root] = 0
                    root_solved_count[category_root] += 1
        return root_solved_count
    except Exception as e:
        raise e


def generate_sync_data_for_root_category(user_id, category, root_solved_count):
    try:
        global rs
        skill_obj = Skill()
        must = [
            {'term': {'category_root': category['category_name']}},
            {'term': {'user_id': user_id}}
        ]
        query_json = {'query': {'bool': {'must': must}}}
        aggregate = {
            "skill_value_by_percentage": {"sum": {"field": "skill_value_by_percentage"}}
        }
        query_json['aggs'] = aggregate
        query_json['size'] = 0

        search_url = 'http://{}/{}/{}/_search'.format(config.ES_HOST, _es_index_user_category, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()

        if 'aggregations' not in response:
            raise Exception('Internal server error')

        skill_value = response['aggregations']['skill_value_by_percentage']['value']
        root_category_percentage = float(category.get('score_percentage', 100))
        skill_value_by_percentage_sum = skill_value*root_category_percentage/100
        skill_level = skill_obj.get_skill_level_from_skill(skill_value)

        data = {
            'relevant_score': -1,
            'skill_value': skill_value,
            'skill_value_by_percentage': skill_value_by_percentage_sum,
            'skill_level': skill_level,
            'skill_title': skill_obj.get_skill_title(skill_level),
            'solve_count': root_solved_count.get(category['category_name'], 0),
            'category_root': 'root',
        }
        return data
    except Exception as e:
        raise e


def sync_root_category_score_for_team(team_id):
    try:
        team_details = get_team_details(team_id)
        solved_problems = []
        for member in team_details['member_list']:
            user_details = get_user_details_by_handle_name(member['user_handle'])
            if user_details is None:
                continue
            user_id = user_details['id']
            problem_list = find_problems_for_user_by_status_filtered(['SOLVED'], user_id)
            for problem in problem_list:
                if problem not in solved_problems:
                    solved_problems.append(problem)

        root_solved_count = root_category_solved_count_by_solved_problem_list(solved_problems)
        category_list = search_categories({'category_root': 'root'}, 0, 100)
        skill_value = 0
        for category in category_list:
            data = generate_sync_data_for_root_category(team_id, category, root_solved_count)
            add_user_category_data(team_id, category['category_id'], data)
            skill_value += data['skill_value_by_percentage']

        return skill_value
    except Exception as e:
        raise e


def sync_overall_stat_for_team(team_id, skill_value = None):
    try:
        team_details = get_team_details(team_id)
        mark_problem = {}
        solve_count = 0
        for member in team_details['member_list']:
            user_details = get_user_details_by_handle_name(member['user_handle'])
            if user_details is None:
                continue
            user_id = user_details['id']
            problem_list = find_problems_for_user_by_status_filtered(['SOLVED'], user_id)
            for problem in problem_list:
                if problem not in mark_problem:
                    mark_problem[problem] = 1
                    solve_count += 1

        if skill_value is None:
            skill_value = generate_skill_value_for_user(team_id)
        skill_obj = Skill()
        skill_title = skill_obj.get_skill_title(skill_value)
        skill_data = {
            'skill_value': int(skill_value),
            'solve_count': int(solve_count),
            'skill_title': skill_title,
        }
        logger.info('Team final stat to update: ' + json.dumps(skill_data))
        update_team_details(team_id, skill_data)
    except Exception as e:
        raise e


def generate_sync_data_for_problem(user_id, user_skill_level, problem):
    try:
        dependent_categories = find_problem_dependency_list(problem['id'])
        problem_score_generator = ProblemScoreGenerator()
        problem_type = problem.get('problem_type', None)
        if problem_type == 'classical':
            dependent_category_id_list = []
            for category in dependent_categories:
                category_id = category['category_id']
                dependent_category_id_list.append(category_id)
            dependent_dependent_category_list = find_category_dependency_list_for_multiple_categories(dependent_category_id_list)
            category_level_list = []
            for category_id in dependent_dependent_category_list:
                category_details = get_user_category_data(user_id, category_id)
                category_level = 0
                if category_details:
                    category_level = category_details.get('skill_level', 0)
                category_level_list.append(category_level)
            relevant_score = problem_score_generator.generate_score(int(float(problem['problem_difficulty'])),
                                                                    category_level_list, user_skill_level)
        else:
            category_level_list = []
            for category in dependent_categories:
                category_id = category['category_id']
                category_details = get_user_category_data(user_id, category_id)
                category_level = 0
                if category_details:
                    category_level = category_details.get('skill_level', 0)
                category_level_list.append(category_level)
            relevant_score = problem_score_generator.generate_score(int(float(problem['problem_difficulty'])),
                                                                    category_level_list, user_skill_level)
        data = {
            'problem_id': problem['id'],
            'relevant_score': relevant_score['score'],
            'user_id': user_id,
            'status': 'UNSOLVED'
        }
        return data
    except Exception as e:
        raise e


def sync_problem_score_for_team(team_id, user_skill_level):
    try:
        team_details = get_team_details(team_id)
        marked_list = {}
        for member in team_details['member_list']:
            user_details = get_user_details_by_handle_name(member['user_handle'])
            if user_details is None:
                continue
            user_id = user_details['id']
            problem_list = available_problems_for_user(user_id)
            for problem in problem_list:
                problem_id = problem['id']
                if problem_id in marked_list:
                    continue
                marked_list[problem_id] = 1
                data = generate_sync_data_for_problem(team_id, user_skill_level, problem)
                add_user_problem_status(team_id, problem['id'], data)
    except Exception as e:
        raise e


def team_training_model_sync(team_id):
    try:
        logger.info(f'team_training_model_sync service called for team: {team_id}')
        logger.info('sync sync_category_score_for_team')
        sync_category_score_for_team(team_id)
        logger.info('sync sync_root_category_score_for_team')
        skill_value = sync_root_category_score_for_team(team_id)
        logger.info('sync sync_overall_stat_for_team')
        sync_overall_stat_for_team(team_id, skill_value)
        skill = Skill()
        user_skill_level = skill.get_skill_level_from_skill(skill_value)
        logger.info('sync get_skill_level_from_skill done')
        sync_problem_score_for_team(team_id, user_skill_level)
        logger.info('sync sync_problem_score_for_team done')

        team_details = get_team_details(team_id)
        logger.info(f' end team_details{team_details}')
        member_list = team_details.get('member_list', [])
        for member in member_list:
            member_details = get_user_details_by_handle_name(member['user_handle'])
            logger.info(f' member_details {member_details}')
            notification_data = {
                'user_id': member_details['id'],
                'sender_id': 'System',
                'notification_type': 'System Notification',
                'redirect_url': '',
                'notification_text': 'Training model for your team ' + team_details['team_name'] + ' has been synced by',
                'status': 'UNREAD',
            }
            logger.info(f' add_notification {notification_data}')
            add_notification(notification_data)
        logger.info(f'team_training_model_sync service completed')
    except Exception as e:
        raise Exception('Internal server error')


def clean_user_sync_history(user_id):
    try:
        logger.info((f'clean_user_sync_data for user: {user_id}'))
        skill = Skill()
        user_data = {}
        user_data['updated_at'] = int(time.time())
        user_data['skill_value'] = 0
        user_data['skill_title'] = skill.get_skill_title(0)
        user_data['decreased_skill_value'] = 0
        user_data['total_score'] = 0
        user_data['target_score'] = 0
        user_data['solve_count'] = 0
        update_user_details(user_id, user_data)
        clean_user_problem_history(user_id)
        clean_user_category_history(user_id)
        logger.info((f'clean_user_sync_data completed for user: {user_id}'))
    except Exception as e:
        raise Exception('Internal server error')


def clean_team_sync_history(team_id):
    try:
        logger.info((f'clean_team_sync_history for team: {team_id}'))
        skill = Skill()
        data = {}
        data['created_at'] = int(time.time())
        data['updated_at'] = int(time.time())
        data['skill_value'] = 0
        data['skill_title'] = skill.get_skill_title(0)
        data['decreased_skill_value'] = 0
        data['total_score'] = 0
        data['target_score'] = 0
        data['solve_count'] = 0
        update_team_details(team_id, data)
        logger.info((f'clean_user_sync_data clean_team_sync_history for user: {team_id}'))
    except Exception as e:
        raise Exception('Internal server error')


def sync_all_users(restore_sync=False):
    try:
        logger.info(f'sync_all_users called')
        print(f'sync_all_users called')
        user_size = 20
        page = 0
        while 1:
            user_list = search_user_ids({}, page*user_size, user_size)
            if len(user_list) == 0:
                break
            for user_id in user_list:
                print('restore: ', user_id)
                job_data = {
                    'job_ref_id': user_id,
                    'job_type': 'USER_SYNC'
                }
                if restore_sync:
                    job_data['job_type'] = 'USER_SYNC_RESTORE'
                create_job(job_data)
            page += 1
        logger.info(f'sync_all_users completed')
    except Exception as e:
        raise Exception('Internal server error')


def sync_all_teams(restore_sync = False):
    try:
        logger.info(f'sync_all_teams called')
        user_size = 20
        page = 0
        while 1:
            team_list = search_team_ids({}, page*user_size, user_size)
            if len(team_list) == 0:
                break

            for team_id in team_list:
                if restore_sync:
                    clean_team_sync_history(team_id)
                team_problem_sync(team_id)

            page += 1
        logger.info(f'sync_all_teams completed')
    except Exception as e:
        raise Exception('Internal server error')


######################### CORE SERVICES #########################



def user_problem_sync(user_id):
    try:
        logger.info(f'user_problem_sync called for user_id: {user_id}')
        print(f'user_problem_sync called for user_id: {user_id}')
        user_problem_data_sync_process(user_id)
        remove_pending_job(user_id)
        logger.info(f'user_problem_sync completed for user_id: {user_id}')
        print(f'user_problem_sync completed for user_id: {user_id}')
    except Exception as e:
        raise Exception('Internal server error')


def team_problem_sync(team_id):
    try:
        logger.info(f'team_problem_sync called for team_id: {team_id}')
        print(f'team_problem_sync called for team_id: {team_id}')
        team_training_model_sync(team_id)
        remove_pending_job(team_id)
        logger.info(f'team_problem_sync completed for team_id: {team_id}')
        print(f'team_problem_sync completed for team_id: {team_id}')
    except Exception as e:
        raise Exception('Internal server error')


def search_job():
    try:
        global rs
        auth_header = get_header()
        logger.debug('search_job called')
        search_param = {
            'status': 'PENDING',
            'sort_order': 'asc',
        }
        response = rs.post(url=job_search_url, json=search_param, headers=auth_header).json()
        logger.debug('response: ' + str(response))
        return response['job_list']
    except Exception as e:
        raise Exception('Internal server error')


def update_job(job_id, status):
    try:
        global rs
        auth_header = get_header()
        logger.debug('update_job called')
        url = job_url + job_id
        response = rs.put(url=url, json={'status': status}, headers=auth_header).json()
        logger.debug('response: ' + str(response))
    except Exception as e:
        raise Exception('Internal server error')


def create_job(job_data):
    try:
        global rs
        auth_header = get_header()
        logger.debug('create_job called')
        response = rs.post(url=job_url, json=job_data, headers=auth_header).json()
        logger.debug('response: ' + str(response))
    except Exception as e:
        raise Exception('Internal server error')


def db_job():
    curtime = int(time.time())
    logger.info('RUN CRON JOB FOR SYNCING DATA AT: ' + str(curtime))
    while(1):
        try:
            pending_job_list = search_job()
            if len(pending_job_list) == 0:
                break
            for cur_job in pending_job_list:
                logger.debug('PROCESS JOB: ' + json.dumps(cur_job))
                print('PROCESS JOB: ' + json.dumps(cur_job))
                update_job(cur_job['id'], 'PROCESSING')
                job_ref_id = cur_job['job_ref_id']

                if cur_job['job_type'] == 'USER_SYNC':
                    user_problem_sync(job_ref_id)
                elif cur_job['job_type'] == 'TEAM_SYNC':
                    team_problem_sync(job_ref_id)
                elif cur_job['job_type'] == 'USER_SYNC_RESTORE':
                    clean_user_sync_history(job_ref_id)
                    user_problem_sync(job_ref_id)
                elif cur_job['job_type'] == 'TEAM_SYNC_RESTORE':
                    clean_team_sync_history(job_ref_id)
                    team_problem_sync(job_ref_id)
                elif cur_job['job_type'] == 'SYNC_ALL_USERS':
                    sync_all_users(restore_sync=False)
                elif cur_job['job_type'] == 'RESTORE_ALL_USERS':
                    sync_all_users(restore_sync=True)
                elif cur_job['job_type'] == 'SYNC_ALL_TEAMS':
                    sync_all_teams(restore_sync=False)
                elif cur_job['job_type'] == 'RESTORE_ALL_TEAMS':
                    sync_all_teams(restore_sync=True)

                update_job(cur_job['id'], 'COMPLETED')
                logger.debug('COMPLETED JOB: ' + json.dumps(cur_job))
                print('COMPLETED JOB: ' + json.dumps(cur_job))
        except Exception as e:
            logger.info(f'Exception occurred while running cron job: {e}')


cron_job = BackgroundScheduler(daemon=True)
cron_job.add_job(db_job, 'interval', seconds=120)
cron_job.start()


if __name__ == '__main__':
    logger.info('Sync Job Script successfully started running')
    print('Sync Job Script successfully started running')
    print('Run initial job')
    db_job()
    while(1):
        pass
