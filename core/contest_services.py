import time
import json
import requests
from flask import current_app as app
import random

from core.problem_services import find_problems_by_status_filtered_for_user_list, get_problem_details
from core.team_services import get_team_details
from models.contest_model import ContestModel

_http_headers = {'Content-Type': 'application/json'}

_es_index_contest = 'cfs_contests'
_es_index_contest_configs = 'cfs_contest_configs'
_es_index_contest_problem_edges = 'cfs_contest_problem_edges'

_es_type = '_doc'
_es_size = 100


def create_contest(data):
    try:
        rs = requests.session()
        data['created_at'] = int(time.time())
        data['updated_at'] = int(time.time())
        post_url = 'http://{}/{}/{}'.format(app.config['ES_HOST'], _es_index_contest, _es_type)
        response = rs.post(url=post_url, json=data, headers=_http_headers).json()
        if 'result' in response and response['result'] == 'created':
            return response['_id']
        raise Exception('ES Down')
    except Exception as e:
        raise e


def add_problem_for_contest(problem_id, contest_id):
    try:
        rs = requests.session()
        data = {
            'problem_id': problem_id,
            'contest_id': contest_id,
            'created_at': int(time.time()),
            'updated_at': int(time.time())
        }
        post_url = 'http://{}/{}/{}'.format(app.config['ES_HOST'], _es_index_contest_problem_edges, _es_type)
        response = rs.post(url=post_url, json=data, headers=_http_headers).json()
        if 'result' in response and response['result'] == 'created':
            return response['_id']
        raise Exception('ES Down')
    except Exception as e:
        raise e


def find_problem_set_for_contest(contest_id):
    try:
        rs = requests.session()
        query_json = {'query': {'bool': {'must': [{'term': {'contest_id': contest_id}}]}}}
        query_json['size'] = _es_size
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_contest_problem_edges, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        item_list = []
        if 'hits' in response:
            for hit in response['hits']['hits']:
                data = hit['_source']
                problem_details = get_problem_details(data['problem_id'])
                item_list.append(problem_details)
        app.logger.error('Elasticsearch down, response: ' + str(response))
        return item_list
    except Exception as e:
        raise e


def create_problem_set(data, contest_id):
    try:
        contest_type = data['contest_type']
        user_list = []
        if contest_type != 'individual':
            team_details = get_team_details(data['contest_ref_id'])
            for member in team_details['member_list']:
                user_list.append(member['id'])
        else:
            user_list.append(data['contest_ref_id'])
        solved_problem_list = find_problems_by_status_filtered_for_user_list(['SOLVED'], user_list)
        print('solved_problem_list done')
        print('solved_problem_list length: ', len(solved_problem_list))
        param_list = data.get('param_list', [])
        category_configs_by_level = find_contest_configs(data['contest_level'])
        print('category_configs_by_level done: ', category_configs_by_level)
        contest_mdoel = ContestModel()
        problem_set = contest_mdoel.create_problem_set_for_contest(param_list, category_configs_by_level, data['problem_count'], solved_problem_list)
        for problem in problem_set:
            add_problem_for_contest(problem, contest_id)
        return problem_set
    except Exception as e:
        raise e


def find_contest_configs(contest_level):
    try:
        rs = requests.session()
        query_json = {'query': {'bool': {'must': {'term': {'contest_level': contest_level}}}}}
        query_json['size'] = _es_size
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_contest_configs, _es_type)
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


def search_contests(param, from_value, size_value):
    try:
        query_json = {'query': {'match_all': {}}}
        rs = requests.session()

        must = []
        keyword_fields = ['setter_id', 'contest_ref_id', 'contest_type', 'contest_level']

        minimum_level = 0
        maximum_level = 100

        if 'minimum_level' in param and param['minimum_level']:
            minimum_level = int(param['minimum_level'])

        if 'maximum_level' in param and param['maximum_level']:
            maximum_level = int(param['maximum_level'])

        param.pop('minimum_level', None)
        param.pop('maximum_level', None)

        for f in param:
            if f in keyword_fields:
                if param[f]:
                    must.append({'term': {f: param[f]}})
            else:
                if param[f]:
                    must.append({'match': {f: param[f]}})

        must.append({"range": {"contest_level": {"gte": minimum_level, "lte": maximum_level}}})

        if len(must) > 0:
            query_json = {'query': {'bool': {'must': must}}}

        if 'category_root' not in param:
            if 'query' in query_json and 'bool' in query_json['query']:
                query_json['query']['bool']['must_not'] = [{'term': {'category_root': 'root'}}]
            else:
                query_json = {'query': {'bool': {'must_not': [{'term': {'category_root': 'root'}}]}}}

        query_json['from'] = from_value
        query_json['size'] = size_value
        print('query_json: ', json.dumps(query_json))
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_contest, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        item_list = []
        if 'hits' in response:
            for hit in response['hits']['hits']:
                data = hit['_source']
                data['id'] = hit['_id']
                item_list.append(data)
            app.logger.info('Contest search method completed')
            return item_list
        app.logger.error('Elasticsearch down, response: ' + str(response))
        return item_list
    except Exception as e:
        raise e
