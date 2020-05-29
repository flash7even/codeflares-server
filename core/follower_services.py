import time
import json
import requests
from flask import current_app as app

_http_headers = {'Content-Type': 'application/json'}

_es_index_followers = 'cfs_followers'

_es_type = '_doc'
_es_size = 100


def get_followed_by_count(user_id):
    try:
        rs = requests.session()
        must = [{'term': {'user_id': user_id}}]
        query_json = {'query': {'bool': {'must': must}}}
        query_json['size'] = 0
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_followers, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        if 'hits' in response:
            return response['hits']['total']['value']
        return 0

    except Exception as e:
        raise e


def get_following_count(user_id):
    try:
        rs = requests.session()
        must = [{'term': {'followed_by': user_id}}]
        query_json = {'query': {'bool': {'must': must}}}
        query_json['size'] = 0
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_followers, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        if 'hits' in response:
            return response['hits']['total']['value']
        return 0

    except Exception as e:
        raise e


def get_follow_stat(user_id):
    try:
        following_count = get_following_count(user_id)
        follower_count = get_followed_by_count(user_id)
        data = {
            'following_count': following_count,
            'follower_count': follower_count
        }
        print('data: ', data)
        return data
    except Exception as e:
        raise e
