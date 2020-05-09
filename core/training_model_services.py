import time
import json
import requests
from flask import current_app as app

_http_headers = {'Content-Type': 'application/json'}

from core.category_services import search_categories
from core.problem_services import get_problem_details


_es_index_category_problem = 'cp_training_problem_category_edges'
_es_index_problem_category = 'cp_training_problem_category_edges'
_es_index_problem_user = 'cp_training_user_problem_edges'
_es_index_problem = 'cp_training_problems'
_es_type = '_doc'
_es_size = 500
_es_max_solved_problem = 1000
_bulk_size = 2

SOLVED = 'SOLVED'
SOLVE_LATER = 'SOLVE_LATER'
SKIP = 'SKIP'


def search_problems_for_user(param, user_id, heavy=False):
    try:
        app.logger.info('find_solved_problems_of_user method called')
        rs = requests.session()
        must = [
            {'term': {'user_id': user_id}}
        ]

        for f in param:
            if f == 'status' and len(param[f]) > 0:
                should = []
                for s in param[f]:
                    should.append({'term': {'status': s}})
                must.append({"bool": {"should": should}})
            else:
                if param[f]:
                    must.append({'term': {f: param[f]}})

        query_json = {'query': {'bool': {'must': must}}}
        query_json['size'] = _es_max_solved_problem
        print('query_json: ', query_json)
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_problem_user, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()

        problem_list = []
        if 'hits' in response:
            for hit in response['hits']['hits']:
                edge = hit['_source']
                if heavy:
                    problem = get_problem_details(edge['problem_id'])
                    problem_list.append(problem)
                else:
                    problem_list.append(edge['problem_id'])
        return problem_list
    except Exception as e:
        raise e

"""
def process_bulk_query(bulk_list, cnt_dict, problem_solved_list):
    app.logger.info('process_bulk_query called')
    app.logger.info('bulk_list: ' + json.dumps(bulk_list))
    try:
        rs = requests.session()
        bulk_query = ""
        for cat in bulk_list:
            current_query = {"from": 0, "size": 200, "query": { "bool": { "must": [ { "term": { "category_id": cat["category_id"]}}]}}}
            query_str = "{}" + "\n" + str(current_query) + "\n"
            bulk_query += str(query_str)

        bulk_query += "\n"
        app.logger.debug('body: ' + json.dumps(bulk_query))
        url = 'http://{}/{}/_msearch'.format(app.config['ES_HOST'], _es_index_category_problem)
        response_list = rs.post(url=url, json=bulk_query, headers=_http_headers).json()
        app.logger.debug('response_list: ' + json.dumps(response_list))

        if 'responses' in response_list:
            for idx, response in enumerate(response_list['responses']):
                for hit in response['hits']['hits']:
                    edge = hit['_source']
                    problem_id = edge['problem_id']
                    cat_id = edge['problem_id']
                    if cat_id not in cnt_dict:
                        cnt_dict[cat_id] = 0
                    if problem_id in problem_solved_list:
                        cnt_dict[cat_id] += 1
        raise Exception('Internal server error')
    except Exception as e:
        raise e
"""


def category_wise_problem_solve_for_user(user_id):
    try:
        category_list = search_categories({}, 0, _es_size)
        problem_solved_list = search_problems_for_user({}, user_id)
        cnt_dict = {}
        for category in category_list:
            rs = requests.session()
            query = {"from": 0, "size": 200, "query": { "bool": { "must": [ { "term": { "category_id": category["category_id"]}}]}}}
            url = 'http://{}/{}/_search'.format(app.config['ES_HOST'], _es_index_category_problem)
            response = rs.post(url=url, json=query, headers=_http_headers).json()
            if 'hits' in response:
                for hit in response['hits']['hits']:
                    edge = hit['_source']
                    problem_id = edge['problem_id']
                    cat_id = edge['category_id']
                    if cat_id not in cnt_dict:
                        cnt_dict[cat_id] = 0
                    if problem_id in problem_solved_list:
                        cnt_dict[cat_id] += 1

        for cat in category_list:
            cat_id = cat['category_id']
            cat['solved_count'] = cnt_dict.get(cat_id, 0)

        return category_list

    except Exception as e:
        raise e
