import time
import json
import requests
from flask import current_app as app

_http_headers = {'Content-Type': 'application/json'}

_es_index_problem_category = 'cp_training_problem_category_edges'
_es_index_category_dependency = 'cp_training_category_dependencies'
_es_type = '_doc'
_es_size = 100


def add_problem_category_dependency(data):
    app.logger.info('add_problem_category_dependency method called')
    rs = requests.session()

    data['created_at'] = int(time.time())
    data['updated_at'] = int(time.time())

    post_url = 'http://{}/{}/{}'.format(app.config['ES_HOST'], _es_index_problem_category, _es_type)
    response = rs.post(url=post_url, json=data, headers=_http_headers).json()

    if 'result' in response and response['result'] == 'created':
        app.logger.info('add_problem_category_dependency method completed')
        return response['_id'], 201
    app.logger.error('Elasticsearch down, response: ' + str(response))
    return response, 500


def add_category_category_dependency(data):
    app.logger.info('add_category_category_dependency method called')
    rs = requests.session()

    data['created_at'] = int(time.time())
    data['updated_at'] = int(time.time())

    post_url = 'http://{}/{}/{}'.format(app.config['ES_HOST'], _es_index_category_dependency, _es_type)
    response = rs.post(url=post_url, json=data, headers=_http_headers).json()

    if 'result' in response and response['result'] == 'created':
        app.logger.info('add_category_category_dependency method completed')
        return response['_id'], 201
    app.logger.error('Elasticsearch down, response: ' + str(response))
    return response, 500

