import time
import json
import requests
from flask import current_app as app
import random

from core.redis_services import add_new_job

_http_headers = {'Content-Type': 'application/json'}

_es_index_jobs = 'cfs_sync_jobs'

_es_type = '_doc'
_es_size = 100

PENDING = 'PENDING'
PROCESSING = 'PROCESSING'
COMPLETED = 'COMPLETED'


def search_jobs(job_status, size):
    try:
        app.logger.info('search_jobs called')
        rs = requests.session()
        must = [{'term': {'status': job_status}}]
        query_json = {'query': {'bool': {'must': must}}}
        query_json['sort'] = [{'created_at': {'order': 'asc'}}]
        query_json['size'] = size
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_jobs, _es_type)
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
