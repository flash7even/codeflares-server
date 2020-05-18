import time
import json
import requests
from flask import current_app as app
import random
import math

from core.user_services import get_user_details

from core.category_services import search_categories

_http_headers = {'Content-Type': 'application/json'}

_es_index_contest = 'cp_training_contests'

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


def create_problem_set(data, contest_id):
    try:
        contest_level = data['contest_level']
        problem_count = data['problem_count']
        category_params = []
        category_map = {}

        param_list = data.get('param_list', [])
        for param in param_list:
            category_name = param['category_name']
            if category_name in category_map:
                continue

            pdata = {
                'category_name': category_name,
                'minimum_difficulty': param.get('minimum_difficulty', 0),
                'maximum_difficulty': param.get('maximum_difficulty', 0),
                'minimum_problem': param.get('minimum_problem', 0),
                'maximum_problem': param.get('maximum_problem', 0),
            }

            if pdata['minimum_difficulty'] > pdata['maximum_difficulty']:
                raise Exception('Invalid data provided')
            if pdata['minimum_problem'] > pdata['maximum_problem']:
                raise Exception('Invalid data provided')

            category_map[category_name] = 1
            category_params.append(pdata)

        category_by_level = find_category_configs(contest_level)
        for cat in category_by_level:
            category_name = cat['category_name']
            if category_name in category_map:
                continue
            pdata = {
                'category_name': category_name,
                'minimum_difficulty': cat.get('minimum_difficulty', 0),
                'maximum_difficulty': cat.get('maximum_difficulty', 0),
                'minimum_problem': cat.get('minimum_problem', 0),
                'maximum_problem': cat.get('maximum_problem', 0),
            }
            category_map[category_name] = 1
            category_params.append(pdata)

    except Exception as e:
        raise e


def generate_contest(contest_id, problem_count, contest_level, category_params):
    for category in category_params:
        pnum = random.randint(category['minimum_problem'], category['maximum_problem'])
        pnum = min(pnum, problem_count)
        minimum_difficulty = category['minimum_difficulty']
        maximum_difficulty = category['maximum_difficulty']
        mid_difficulty = int(math.ceil((minimum_difficulty + maximum_difficulty)/2))

        while pnum > 0:
            prob = random.randint(1, 100)
            if prob > 50: # Select upper half difficulty
                pass


def find_category_configs(contest_level):
    try:
        rs = requests.session()
        query_json = {'query': {'bool': {'must': {'term': {'contest_level': contest_level}}}}}
        query_json['size'] = _es_size
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_contest, _es_type)
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
