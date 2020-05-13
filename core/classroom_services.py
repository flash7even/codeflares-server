import time
import json
import requests
from flask import current_app as app

from core.user_services import get_user_details

_http_headers = {'Content-Type': 'application/json'}

_es_index_classroom_tasks = 'cp_training_classroom_tasks'
_es_index_classroom_classes = 'cp_training_classroom_classes'

_es_type = '_doc'
_es_size = 100


DELETED = 'DELETED'
EXPIRED = 'EXPIRED'


def search_task_lists(param, from_val, size_val):
    try:
        app.logger.info('search_task_lists method called')
        rs = requests.session()
        query_json = {'query': {'match_all': {}}}

        must = []
        keyword_fields = ['classroom_id']

        for f in param:
            if f in keyword_fields:
                must.append({'term': {f: param[f]}})
            else:
                must.append({'match': {f: param[f]}})

        if len(must) > 0:
            query_json = {'query': {'bool': {'must': must}}}

        query_json['from'] = from_val
        query_json['size'] = size_val
        query_json['sort'] = [{'updated_at': {'order': 'desc'}}]
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_classroom_tasks, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        item_list = []
        if 'hits' in response:
            for hit in response['hits']['hits']:
                data = hit['_source']
                data['id'] = hit['_id']
                user_details = get_user_details(data['task_added_by'])
                data['task_added_by_user_handle'] = user_details['username']
                item_list.append(data)
        return item_list

    except Exception as e:
        raise e


def search_class_lists(param, from_val, size_val):
    try:
        app.logger.info('search_class_lists method called')
        rs = requests.session()
        query_json = {'query': {'match_all': {}}}

        must = []
        keyword_fields = ['classroom_id']

        for f in param:
            if f in keyword_fields:
                must.append({'term': {f: param[f]}})
            else:
                must.append({'match': {f: param[f]}})

        if len(must) > 0:
            query_json = {'query': {'bool': {'must': must}}}

        query_json['from'] = from_val
        query_json['size'] = size_val
        query_json['sort'] = [{'updated_at': {'order': 'desc'}}]
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_classroom_classes, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        item_list = []
        if 'hits' in response:
            for hit in response['hits']['hits']:
                data = hit['_source']
                data['id'] = hit['_id']
                user_details = get_user_details(data['class_moderator_id'])
                data['class_moderator_id_user_handle'] = user_details['username']
                item_list.append(data)
        return item_list

    except Exception as e:
        raise e
