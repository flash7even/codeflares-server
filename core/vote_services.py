import time
import json
import requests
from flask import current_app as app
import random

from core.user_services import add_contribution

_http_headers = {'Content-Type': 'application/json'}

_es_index_vote = 'cfs_votes'
_es_index_comment = 'cfs_comments'
_es_index_blog = 'cfs_blogs'

_es_type = '_doc'
_es_size = 100

LIKE = 'LIKE'
DISLIKE = 'DISLIKE'


class voteManager:
    blog = 5
    blog_comment = 1
    problem_comment = 3


def get_blog_details(blog_id):
    try:
        rs = requests.session()
        search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index_blog, _es_type, blog_id)
        response = rs.get(url=search_url, headers=_http_headers).json()
        print(response)
        if 'found' in response:
            if response['found']:
                data = response['_source']
                data['id'] = response['_id']
                data['blog_id'] = response['_id']
                return data
            app.logger.warning('Blog not found')
            raise Exception('Blog not found')
        raise Exception('Es Down')
    except Exception as e:
        raise e


def get_comment_details(comment_id):
    try:
        rs = requests.session()
        search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index_comment, _es_type, comment_id)
        response = rs.get(url=search_url, headers=_http_headers).json()
        if 'found' in response:
            if response['found']:
                data = response['_source']
                data['id'] = response['_id']
                return data
        app.logger.error('Elasticsearch down, response: ' + str(response))
        raise Exception('Internal server error')
    except Exception as e:
        raise e


def get_vote_count(vote_ref_id, vote_type):
    try:
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


def get_vote_count_list(vote_ref_id):
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

        vote_factor = 1
        if data['vote_type'] == DISLIKE:
            vote_factor = -1

        if 'result' in response and response['result'] == 'created':
            if data['vote_topic'] == 'blog':
                blog_details = get_blog_details(data['vote_ref_id'])
                blog_writer = blog_details['blog_writer']
                add_contribution(blog_writer, voteManager.blog*vote_factor)
            if data['vote_topic'] == 'blog-comment':
                comment_details = get_comment_details(data['vote_ref_id'])
                comment_writer = comment_details['comment_writer']
                add_contribution(comment_writer, voteManager.blog_comment*vote_factor)
            if data['vote_topic'] == 'problem-comment' or data['vote_topic'] == 'category-comment':
                comment_details = get_comment_details(data['vote_ref_id'])
                comment_writer = comment_details['comment_writer']
                add_contribution(comment_writer, voteManager.problem_comment*vote_factor)
            return {'message': 'success'}
        app.logger.error('Elasticsearch down, response: ' + str(response))
        raise Exception('ES Down')
    except Exception as e:
        raise e
