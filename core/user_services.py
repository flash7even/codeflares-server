import requests
from flask import current_app as app
import time
import json
from core.follower_services import get_follow_stat

from core.rating_services import get_user_rating_history

_http_headers = {'Content-Type': 'application/json'}

_es_index_user = 'cfs_users'
_es_type = '_doc'
_es_size = 2000

public_fields = ['username', 'first_name', 'last_name', 'full_name', 'skill_value', 'skill_title', 'solve_count']


def get_user_details_by_handle_name(username):
    try:
        rs = requests.session()
        query_json = {'query': {'bool': {'must': [{'match': {'username': username}}]}}}
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_user, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        if 'hits' in response:
            for hit in response['hits']['hits']:
                user = hit['_source']
                user['id'] = hit['_id']
                user['created_at'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(user['created_at']))
                return user
        return None
    except Exception as e:
        raise e


def get_user_details(user_id):
    try:
        rs = requests.session()
        search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index_user, _es_type, user_id)
        response = rs.get(url=search_url, headers=_http_headers).json()
        print('response: ', response)
        if 'found' in response:
            if response['found']:
                data = response['_source']
                data['id'] = response['_id']
                data['follow_stat'] = get_follow_stat(user_id)
                data['created_at'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data['created_at']))
                return data
        raise Exception('User not found')
    except Exception as e:
        raise e


def update_user_details(user_id, user_data):
    try:
        ignore_fields = ['username', 'password']
        rs = requests.session()

        search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index_user, _es_type, user_id)
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
            app.logger.info('User not found')
            return 'not found'
        app.logger.error('Elasticsearch down')
        return response

    except Exception as e:
        return {'message': str(e)}


def add_contribution(user_id, value):
    app.logger.info(f'add_contribution for {user_id} by {str(value)}')
    try:
        ignore_fields = ['username', 'password']
        rs = requests.session()

        search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index_user, _es_type, user_id)
        response = rs.get(url=search_url, headers=_http_headers).json()

        if 'found' in response:
            if response['found']:
                user = response['_source']
                contribution = int(user.get('contribution', 0)) + value
                user['contribution'] = contribution
                response = rs.put(url=search_url, json=user, headers=_http_headers).json()
                if 'result' in response:
                    return response['result']
            app.logger.info('User not found')
            return 'not found'
        app.logger.error('Elasticsearch down')
        return response

    except Exception as e:
        return {'message': str(e)}


def get_user_details_public(user_id):
    try:
        rs = requests.session()
        search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index_user, _es_type, user_id)
        response = rs.get(url=search_url, headers=_http_headers).json()
        print('response: ', response)
        if 'found' in response:
            if response['found']:
                data = response['_source']
                data['follow_stat'] = get_follow_stat(user_id)
                data['created_at'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data['created_at']))
                public_data = {}
                for f in public_fields:
                    public_data[f] = data.get(f, None)
                public_data['id'] = user_id
                return public_data
        raise Exception('User not found')
    except Exception as e:
        raise e


def search_user(param, from_val, to_val, sort_by = 'updated_at', sort_order = 'desc'):
    try:
        must = []

        text_fields = ['username', 'email', 'mobile']
        keyword_fields = ['user_role']

        for k in text_fields:
            if k in param:
                must.append({'match': {k: param[k]}})

        for k in keyword_fields:
            if k in param:
                must.append({'term': {k: param[k]}})

        query_json = {'query': {'bool': {'must': must}}}
        query_json['sort'] = [{sort_by: {'order': sort_order}}]

        query_json['from'] = from_val
        query_json['size'] = to_val
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_user, _es_type)
        response = requests.session().post(url=search_url, json=query_json, headers=_http_headers).json()
        print(response)

        if 'hits' in response:
            data = []
            rank = 1
            for hit in response['hits']['hits']:
                user = hit['_source']
                user['id'] = hit['_id']
                follow_stat = get_follow_stat(user['id'])
                user['follow_stat'] = follow_stat
                user['rating_history'] = get_user_rating_history(user['id'])
                user['rank'] = rank
                user['created_at'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(user['created_at']))
                rank += 1
                data.append(user)
            return data
        app.logger.error('Elasticsearch down, response : ' + str(response))
        raise Exception('Internal server error')

    except Exception as e:
        raise e


def dtsearch_user(param, start, length, sort_by = 'updated_at', sort_order = 'desc'):
    try:
        query_json = {'query': {'match_all': {}}}
        text_fields = ['username', 'full_name']
        should = []

        if 'filter' in param and param['filter']:
            for f in text_fields:
                should.append({'fuzzy': {f: {'value': param['filter'], 'prefix_length': 0, 'fuzziness': 3}}})

        if len(should) > 0:
            query_json = {'query': {'bool': {'should': should}}}

        query_json['sort'] = [{sort_by: {'order': sort_order}}]
        query_json['from'] = start
        query_json['size'] = length
        print('query_json: ', json.dumps(query_json))
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_user, _es_type)
        response = requests.session().post(url=search_url, json=query_json, headers=_http_headers).json()
        print('response: ', response)

        if 'hits' in response:
            data = []
            rank = 1
            for hit in response['hits']['hits']:
                user = hit['_source']
                user['id'] = hit['_id']
                follow_stat = get_follow_stat(user['id'])
                user['follow_stat'] = follow_stat
                user['rating_history'] = get_user_rating_history(user['id'])
                user['rank'] = rank+start
                user['skill_value'] = user.get('skill_value', 0)
                user['solve_count'] = user.get('solve_count', 0)
                user['contribution'] = user.get('contribution', 0)
                user['created_at'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(user['created_at']))
                rank += 1
                data.append(user)
            return {
                'user_list': data,
                'total': response['hits']['total']['value']
            }
        app.logger.error('Elasticsearch down, response : ' + str(response))
        raise Exception('Internal server error')

    except Exception as e:
        raise e
