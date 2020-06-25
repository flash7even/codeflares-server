import time
import json
import requests
from flask import current_app as app

from commons.skillset import Skill

_http_headers = {'Content-Type': 'application/json'}

_es_index_user_category = 'cfs_user_category_edges'
_es_type = '_doc'
_es_size = 500


def print_user_root_synced_data(user_id):
    rs = requests.session()
    must = [
        {'term': {'category_root': 'root'}},
        {'term': {'user_id': user_id}},
    ]
    query_json = {'query': {'bool': {'must': must}}}
    query_json['size'] = _es_size

    search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_user_category, _es_type)
    response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()


def get_user_root_synced_data_by_id(data_id):
    rs = requests.session()
    search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index_user_category, _es_type, data_id)
    response = rs.get(url=search_url, headers=_http_headers).json()


def get_user_category_data(user_id, category_id):
    try:
        rs = requests.session()
        must = [
            {'term': {'user_id': user_id}},
            {'term': {'category_id': category_id}}
        ]
        query_json = {'query': {'bool': {'must': must}}}
        query_json['size'] = 1
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_user_category, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        if 'hits' in response:
            for hit in response['hits']['hits']:
                edge = hit['_source']
                edge['id'] = hit['_id']
                return edge
        return None
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
            url = 'http://{}/{}/{}'.format(app.config['ES_HOST'], _es_index_user_category, _es_type)
            response = rs.post(url=url, json=data, headers=_http_headers).json()
            get_user_root_synced_data_by_id(response['_id'])
            print_user_root_synced_data(user_id)
            if 'result' in response:
                return response['_id']
            raise Exception('Internal server error')

        edge_id = edge['id']
        edge.pop('id', None)

        for f in data:
            edge[f] = data[f]

        edge['updated_at'] = int(time.time())
        url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index_user_category, _es_type, edge_id)
        response = rs.put(url=url, json=edge, headers=_http_headers).json()

        if 'result' in response:
            return response['result']

        raise Exception('Internal server error')

    except Exception as e:
        raise e


def update_root_category_skill_for_user(user_id, root_category_list):
    app.logger.info(f'update_root_category_skill_for_user called for: {user_id}')
    rs = requests.session()
    user_skill_sum = 0
    for cat in root_category_list:
        must = [{"term": {"category_root": cat["category_name"]}}, {"term": {"user_id": user_id}}]
        aggs = {
            "skill_value_by_percentage": {"sum": {"field": "skill_value_by_percentage"}},
            "solve_count": {"sum": {"field": "solve_count"}}
        }
        query_json = {"size": 0, "query": {"bool": {"must": must}}, "aggs": aggs}
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_user_category, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        if 'aggregations' in response:
            skill_value = response['aggregations']['skill_value_by_percentage']['value']
            category_id = cat['category_id']
            uc_edge = get_user_category_data(user_id, category_id)
            app.logger.info(f'uc_edge from es: {uc_edge}')
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
            uc_edge['solve_count'] = int(response['aggregations']['solve_count']['value'])
            skill_info = Skill()
            uc_edge['skill_title'] = skill_info.get_skill_title(uc_edge['skill_value'])
            uc_edge['skill_level'] = skill_info.get_skill_level_from_skill(uc_edge['skill_value'])
            score_percentage = float(cat['score_percentage'])
            uc_edge['skill_value_by_percentage'] = uc_edge['skill_value'] * score_percentage / 100
            user_skill_sum += uc_edge['skill_value_by_percentage']
            app.logger.info(f'add uc_edge: {uc_edge}')
            uc_edge.pop('id', None)
            add_user_category_data(user_id, category_id, uc_edge)
    return user_skill_sum


def update_category_relevant_score_for_user(user_id, category_list):
    for cat in category_list:
        pass