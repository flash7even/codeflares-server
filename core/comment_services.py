import time
import json
import requests
from flask import current_app as app
import random

from core.user_services import get_user_details

from core.vote_services import get_vote_count_list

_http_headers = {'Content-Type': 'application/json'}

_es_index_comment = 'cfs_comments'

_es_type = '_doc'
_es_size = 100


def dfs_comment_tree(cur_node_id):
    try:
        app.logger.info('search_teams_for_user called')
        rs = requests.session()
        must = [{'term': {'comment_parent_id': cur_node_id}}]
        query_json = {'query': {'bool': {'must': must}}}
        query_json['size'] = _es_size
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_comment, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        print('response: ', json.dumps(response))
        if 'hits' in response:
            comment_list = []
            for hit in response['hits']['hits']:
                data = hit['_source']
                data['comment_id'] = hit['_id']
                data['updated_at'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data['updated_at']))
                if 'comment_writer' in data:
                    user_details = get_user_details(data['comment_writer'])
                    data['comment_writer_handle'] = user_details['username']
                data['comment_id'] = hit['_id']
                data['vote_count'] = get_vote_count_list(data['comment_id'])
                child_list = dfs_comment_tree(data['comment_id'])
                data['comment_list'] = child_list
                comment_list.append(data)
            return comment_list
        app.logger.error('Elasticsearch down, response: ' + str(response))
        raise Exception('Internal server error')
    except Exception as e:
        raise e


def get_comment_count(blog_id):
    try:
        app.logger.info('search_teams_for_user called')
        rs = requests.session()
        must = [{'term': {'comment_ref_id': blog_id}}]
        query_json = {'query': {'bool': {'must': must}}}
        query_json['size'] = 0
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_comment, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        if 'hits' in response:
            return response['hits']['total']['value']
        app.logger.error('Elasticsearch down, response: ' + str(response))
        raise Exception('Internal server error')
    except Exception as e:
        raise e


def get_comment_list(blog_id):
    try:
        comment_list = dfs_comment_tree(blog_id)
        return comment_list
    except Exception as e:
        raise e

