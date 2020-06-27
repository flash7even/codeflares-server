import time
import json
import requests
from flask import current_app as app
import random

from core.user_services import get_user_details
from core.vote_services import get_vote_count_list

_http_headers = {'Content-Type': 'application/json'}

_es_index_resource = 'cfs_resources'

_es_type = '_doc'
_es_size = 100


def add_resources(data):
    try:
        rs = requests.session()
        data['created_at'] = int(time.time())
        data['updated_at'] = int(time.time())

        post_url = 'http://{}/{}/{}'.format(app.config['ES_HOST'], _es_index_resource, _es_type)
        response = rs.post(url=post_url, json=data, headers=_http_headers).json()
        if 'result' in response and response['result'] == 'created':
            app.logger.info('Create resource method completed')
            return response['_id']
        raise Exception('ES Down')
    except Exception as e:
        raise e


def search_resource(param, from_val, size):
    try:
        rs = requests.session()
        query_json = {'query': {'match_all': {}}}

        must = []
        keyword_fields = ['resource_ref_id', 'resource_type', 'resource_title', 'resource_writer', 'resource_owner']

        for f in param:
            if f in keyword_fields:
                must.append({'term': {f: param[f]}})
            else:
                must.append({'match': {f: param[f]}})

        if len(must) > 0:
            query_json = {'query': {'bool': {'must': must}}}

        query_json['size'] = size
        query_json['from'] = from_val
        query_json['sort'] = [{'created_at': {'order': 'desc'}}]

        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_resource, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        print('response: ', response)
        item_list = []
        if 'hits' in response:
            for hit in response['hits']['hits']:
                data = hit['_source']
                data['id'] = hit['_id']
                user_details = get_user_details(data['resource_writer'])
                data['resource_writer_handle'] = user_details['username']
                data['resource_writer_skill_color'] = user_details['skill_color']
                data['resource_id'] = hit['_id']
                data['updated_at'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data['updated_at']))
                data['vote_count'] = get_vote_count_list(data['resource_id'])
                item_list.append(data)
        print('item_list: ', item_list)
        return item_list

    except Exception as e:
        raise e
