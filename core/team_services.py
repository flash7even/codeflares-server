import time
import json
import requests
from flask import current_app as app

_http_headers = {'Content-Type': 'application/json'}

_es_index_user_team_edge = 'cp_training_user_team_edges'
_es_index_team = 'cp_training_teams'
_es_type = '_doc'
_es_size = 100


def delete_all_users_from_team(team_id):
    rs = requests.session()
    must = [
        {'term': {'team_id': team_id}},
    ]
    query_json = {'query': {'bool': {'must': must}}}
    query_json['size'] = _es_size
    search_url = 'http://{}/{}/{}/_delete_by_query'.format(app.config['ES_HOST'], _es_index_user_team_edge, _es_type)
    response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()

    return {
        'code': 200,
        'body': response
    }


def get_all_users_from_team(team_id):
    rs = requests.session()
    must = [
        {'term': {'team_id': team_id}},
    ]
    query_json = {'query': {'bool': {'must': must}}}
    query_json['size'] = _es_size
    search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_user_team_edge, _es_type)
    response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()

    item_list = []

    if 'hits' in response:
        for hit in response['hits']['hits']:
            data = hit['_source']
            data['id'] = hit['_id']
            item_list.append(data)

    return item_list


def get_user_team_edge(team_id, user_handle):
    rs = requests.session()
    must = [
        {'term': {'team_id': team_id}},
        {'term': {'user_handle': user_handle}}
    ]
    query_json = {'query': {'bool': {'must': must}}}
    query_json['size'] = 1
    search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_user_team_edge, _es_type)
    response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()

    print('response: ', json.dumps(response))

    if 'hits' in response:
        if response['hits']['total']['value'] > 0:
            return response['hits']['hits'][0]
    return None


def add_team_member(data):
    app.logger.info('add_team_members method called')
    rs = requests.session()

    resp = get_user_team_edge(data['team_id'], data['user_handle'])

    if resp is not None:
        return {
            'code': 400,
            'body': resp
        }

    data['created_at'] = int(time.time())
    data['updated_at'] = int(time.time())

    post_url = 'http://{}/{}/{}'.format(app.config['ES_HOST'], _es_index_user_team_edge, _es_type)
    response = rs.post(url=post_url, json=data, headers=_http_headers).json()

    if 'result' in response and response['result'] == 'created':
        app.logger.info('add_team_members method completed')
        return {
            'code': 201,
            'body': response
        }
    app.logger.error('Elasticsearch down, response: ' + str(response))
    return {
            'code': 500,
            'body': response
        }


def delete_team_member(team_id, user_handle):
    app.logger.info('add_team_members method called')
    rs = requests.session()
    resp = get_user_team_edge(team_id, user_handle)

    if resp is None:
        return {
            'code': 400,
            'body': resp
        }

    url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index_user_team_edge, _es_type, resp['_id'])
    response = rs.delete(url=url, headers=_http_headers).json()

    if 'result' in response:
        if response['result'] == 'deleted':
            app.logger.info('Delete delete_team_member method completed')
            return {
                'code': 200,
                'body': response['result']
            }
        else:
            return {
                'code': 400,
                'body': response['result']
            }
    app.logger.error('Elasticsearch down, response: ' + str(response))
    return {
        'code': 500,
        'body': response
    }


def search_teams(param, from_val, size_val):
    try:
        rs = requests.session()
        query_json = {'query': {'match_all': {}}}

        must = []
        keyword_fields = ['team_leader_id', 'team_type']

        for f in param:
            if f in keyword_fields:
                must.append({'term': {f: param[f]}})
            else:
                must.append({'match': {f: param[f]}})

        if len(must) > 0:
            query_json = {'query': {'bool': {'must': must}}}

        query_json['from'] = from_val
        query_json['size'] = size_val
        print('query_json: ', json.dumps(query_json))
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_team, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        print('response: ', json.dumps(response))
        if 'hits' in response:
            item_list = []
            for hit in response['hits']['hits']:
                team = hit['_source']
                team['id'] = hit['_id']
                member_edge_list = get_all_users_from_team(team['id'])
                team['member_list'] = member_edge_list
                item_list.append(team)
            print('item_list', json.dumps(item_list))
            app.logger.info('Team search method completed')
            return item_list
        app.logger.error('Elasticsearch down, response: ' + str(response))
        raise Exception('Internal server error')

    except Exception as e:
        raise Exception('Internal server error')
