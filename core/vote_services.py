import time
import json
import requests
from flask import current_app as app
import random

from core.user_services import get_user_details

_http_headers = {'Content-Type': 'application/json'}

_es_index_vote = 'cfs_votes'

_es_type = '_doc'
_es_size = 100

LIKE = 'LIKE'
DISLIKE = 'DISLIKE'


def get_vote_count(vote_ref_id, vote_type):
    try:
        app.logger.info('search_teams_for_user called')
        rs = requests.session()
        must = [
            {'term': {'vote_ref_id': vote_ref_id}},
            {'term': {'vote_type': vote_type}}
        ]
        query_json = {'query': {'bool': {'must': must}}}
        query_json['size'] = _es_size
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_vote, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        print('response: ', json.dumps(response))
        if 'hits' in response:
            return response['hits']['total']['value']
        app.logger.error('Elasticsearch down, response: ' + str(response))
        raise Exception('Internal server error')
    except Exception as e:
        raise e


def search_votes(param):
    try:
        app.logger.info('search_teams_for_user called')
        rs = requests.session()
        must = []
        for f in param:
            must.append({'term': {f: param[f]}})

        query_json = {'query': {'bool': {'must': must}}}
        query_json['size'] = _es_size
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_vote, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        if 'hits' in response:
            item_list = []
            for hit in response['hits']['hits']:
                data = hit['_source']
                data['id'] = hit['_id']
                item_list.append(data)
            return item_list
        app.logger.error('Elasticsearch down, response: ' + str(response))
        raise Exception('Internal server error')
    except Exception as e:
        raise e


def get_vote_list(vote_ref_id):
    try:
        like_count = get_vote_count(vote_ref_id, LIKE)
        dislike_count = get_vote_count(vote_ref_id, DISLIKE)
        data = {
            'like_count': like_count,
            'dislike_count': dislike_count
        }
        return data
    except Exception as e:
        raise e


def add_vote(data):
    try:
        app.logger.info('Create vote method called')

        param = {
            'vote_ref_id': data['vote_ref_id'],
            'voter_id': data['voter_id']
        }
        vote_list = search_votes(param)

        if len(vote_list) > 0:
            return {'message': 'already_voted'}

        rs = requests.session()
        data['created_at'] = int(time.time())
        data['updated_at'] = int(time.time())

        post_url = 'http://{}/{}/{}'.format(app.config['ES_HOST'], _es_index_vote, _es_type)
        response = rs.post(url=post_url, json=data, headers=_http_headers).json()

        if 'result' in response and response['result'] == 'created':
            app.logger.info('Create vote method completed')
            return {'message': 'success'}
        app.logger.error('Elasticsearch down, response: ' + str(response))
        raise Exception('ES Down')
    except Exception as e:
        raise e
