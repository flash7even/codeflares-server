import time
import json
import requests
from flask import current_app as app
import random

from core.redis_services import add_new_job
from commons.skillset import Skill

_http_headers = {'Content-Type': 'application/json'}

_es_index_jobs = 'cfs_sync_jobs'
_es_index_team = 'cfs_teams'
_es_index_user = 'cfs_users'
_es_type = '_doc'
_es_size = 100

PENDING = 'PENDING'
PROCESSING = 'PROCESSING'
COMPLETED = 'COMPLETED'
USER_SYNC = 'USER_SYNC'
TEAM_SYNC = 'TEAM_SYNC'


def get_user_details(user_id):
    try:
        rs = requests.session()
        search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index_user, _es_type, user_id)
        response = rs.get(url=search_url, headers=_http_headers).json()
        print('response: ', response)
        if 'found' in response:
            if response['found']:
                data = response['_source']
                skill = Skill()
                data['skill_color'] = skill.get_color_from_skill_title(data.get('skill_title', 'NA'))
                return data
        raise Exception('User not found')
    except Exception as e:
        raise e


def get_team_details(team_id):
    try:
        rs = requests.session()
        search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index_team, _es_type, team_id)
        response = rs.get(url=search_url, headers=_http_headers).json()

        if 'found' in response:
            if response['found']:
                data = response['_source']
                skill = Skill()
                data['skill_color'] = skill.get_color_from_skill_title(data.get('skill_title'))
                return data
            raise Exception('Team not found')
        app.logger.error('Elasticsearch down, response: ' + str(response))
        raise Exception('Internal server error')

    except Exception as e:
        raise e


def search_jobs(param, page, size):
    try:
        app.logger.info('search_jobs called')
        rs = requests.session()
        fields = ['job_ref_id', 'job_type', 'status']
        must = []
        for f in param:
            if f in fields:
                must.append({'term': {f: param[f]}})

        query_json = {'query': {'match_all': {}}}
        if len(must) > 0:
            query_json = {'query': {'bool': {'must': must}}}

        query_json['sort'] = [{'created_at': {'order': 'asc'}}]
        if 'sort_order' in param:
            query_json['sort'] = [{'created_at': {'order': param['sort_order']}}]

        query_json['from'] = page*size
        query_json['size'] = size
        print('query_json: ', query_json)
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_jobs, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        print('response: ', response)
        if 'hits' in response:
            item_list = []
            for hit in response['hits']['hits']:
                data = hit['_source']
                data['id'] = hit['_id']
                if data['job_type'] == USER_SYNC:
                    data['ref_details'] = get_user_details(data['job_ref_id'])
                if data['job_type'] == TEAM_SYNC:
                    data['ref_details'] = get_team_details(data['job_ref_id'])
                if 'created_at' in data:
                    data['created_at'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data['created_at']))
                if 'updated_at' in data:
                    data['updated_at'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data['updated_at']))
                item_list.append(data)
            return item_list
        app.logger.error('Elasticsearch down, response: ' + str(response))
        raise Exception('Internal server error')
    except Exception as e:
        raise e


def add_pending_job(job_ref_id, job_type):
    try:
        app.logger.info('Create job method called')

        if add_new_job(job_ref_id) is False:
            return {'message': 'failed'}

        rs = requests.session()
        data = {
            'job_ref_id': job_ref_id,
            'job_type': job_type,
            'status': PENDING,
            'created_at': int(time.time()),
            'updated_at': int(time.time())
        }
        post_url = 'http://{}/{}/{}'.format(app.config['ES_HOST'], _es_index_jobs, _es_type)
        print(post_url)
        response = rs.post(url=post_url, json=data, headers=_http_headers).json()
        print(response)
        if 'result' in response and response['result'] == 'created':
            app.logger.info('Create vote method completed')
            return {'message': 'success'}
        app.logger.error('Elasticsearch down, response: ' + str(response))
        raise Exception('ES Down')
    except Exception as e:
        raise e


def update_pending_job(job_id, updated_job_type):
    try:
        app.logger.info('Create job method called')
        rs = requests.session()
        url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index_jobs, _es_type, job_id)
        response = rs.get(url=url,  headers=_http_headers).json()
        if 'found' in response:
            if response['found']:
                data = response['_source']
                data['status'] = updated_job_type
                data['updated_at'] = int(time.time())
                app.logger.info('Elasticsearch query : ' + str(url))
                response = rs.put(url=url, json=data, headers=_http_headers).json()
                app.logger.info('Elasticsearch response :' + str(response))
                if 'result' in response:
                    app.logger.info('update_pending_job completed')
                    return response['result']
            app.logger.info('job not found')
        raise Exception('ES Down')
    except Exception as e:
        raise e


def last_completed_job_time(job_ref_id):
    try:
        app.logger.info('last_completed_job_time called')
        rs = requests.session()
        must = [
            {'term': {'status': COMPLETED}},
            {'term': {'job_ref_id': job_ref_id}},
        ]
        query_json = {'query': {'bool': {'must': must}}}
        query_json['sort'] = [{'created_at': {'order': 'desc'}}]
        query_json['size'] = 1
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_jobs, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        if 'hits' in response:
            for hit in response['hits']['hits']:
                data = hit['_source']
                return data['updated_at']
            return 'NA'
        app.logger.error('Elasticsearch down, response: ' + str(response))
        raise Exception('Internal server error')
    except Exception as e:
        raise e
