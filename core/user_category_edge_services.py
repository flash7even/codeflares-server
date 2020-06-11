import time
import json
import requests
from flask import current_app as app

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
