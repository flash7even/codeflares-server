import time
import json
import requests
from flask import current_app as app

from core.user_services import get_user_details

_http_headers = {'Content-Type': 'application/json'}

_es_user_user_notification = 'cp_training_notifications'

_es_type = '_doc'
_es_size = 100


READ = 'READ'
UNREAD = 'UNREAD'


def add_notification(data):
    try:
        app.logger.info('add_notification method called')
        rs = requests.session()
        data['created_at'] = int(time.time())
        data['updated_at'] = int(time.time())
        data['status'] = UNREAD
        post_url = 'http://{}/{}/{}'.format(app.config['ES_HOST'], _es_user_user_notification, _es_type)
        response = rs.post(url=post_url, json=data, headers=_http_headers).json()
        if 'result' in response and response['result'] == 'created':
            app.logger.info('add_notification method completed')
            return response['_id'], 201
        app.logger.error('Elasticsearch down, response: ' + str(response))
        raise Exception('Internal server error')
    except Exception as e:
        raise e


def update_notification(notification_id, data):
    try:
        app.logger.info('update_notification called ' + str(notification_id))
        rs = requests.session()
        search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_user_user_notification, _es_type, notification_id)
        response = rs.get(url=search_url, headers=_http_headers).json()

        if 'found' in response:
            if response['found']:
                es_data = response['_source']
                for key in data:
                    es_data[key] = data[key]
                response = rs.put(url=search_url, json=es_data, headers=_http_headers).json()
                app.logger.debug('Elasticsearch response :' + str(response))
                if 'result' in response:
                    app.logger.info('update_notification completed')
                    return response['result']
            app.logger.info('User not found')
            return {'message': 'Not found'}
        app.logger.error('Elasticsearch down')
        return response

    except Exception as e:
        return {'message': str(e)}


def search_notification(param, size):
    try:
        app.logger.info('search_task_lists method called')
        rs = requests.session()
        query_json = {'query': {'match_all': {}}}

        must = []
        keyword_fields = ['user_id', 'sender_id', 'notification_type', 'status']

        for f in param:
            if f in keyword_fields:
                must.append({'term': {f: param[f]}})
            else:
                must.append({'match': {f: param[f]}})

        if len(must) > 0:
            query_json = {'query': {'bool': {'must': must}}}

        query_json['size'] = size
        query_json['sort'] = [{'created_at': {'order': 'desc'}}]

        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_user_user_notification, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        item_list = []
        if 'hits' in response:
            for hit in response['hits']['hits']:
                data = hit['_source']
                data['id'] = hit['_id']
                user_details = get_user_details(data['user_id'])
                data['user_id_handle'] = user_details['username']
                if data['sender_id'] != 'System':
                    user_details = get_user_details(data['sender_id'])
                    data['sender_id_handle'] = user_details['username']
                else:
                    data['sender_id_handle'] = 'System'

                if 'notification_text' in data:
                    data['notification_text'] = data['notification_text'] + ' ' + data['sender_id_handle']

                if 'created_at' in data:
                    data['created_at'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data['created_at']))

                if 'status' in data and data['status'] == UNREAD:
                    data[UNREAD] = True

                item_list.append(data)
        return item_list

    except Exception as e:
        raise e
