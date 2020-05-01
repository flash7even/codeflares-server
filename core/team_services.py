import time
import json
import requests
from flask import current_app as app

_http_headers = {'Content-Type': 'application/json'}

_es_index_user_team_edge = 'cp_training_user_team_edges'
_es_index_team = 'cp_training_teams'
_es_type = '_doc'
_es_size = 100


def get_team_details(team_id):
    print('get_team_details: ', team_id)
    try:
        rs = requests.session()
        search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index_team, _es_type, team_id)
        response = rs.get(url=search_url, headers=_http_headers).json()
        print('response: ', json.dumps(response))

        if 'found' in response:
            if response['found']:
                data = response['_source']
                data['id'] = response['_id']
                data['member_list'] = get_all_users_from_team(team_id)
                data['rating'] = 1988
                data['title'] = 'Candidate Master'
                data['max_rating'] = 1988
                data['solve_count'] = 890
                data['follower'] = 921
                data['following'] = 530
                return data
            app.logger.warning('Team not found')
            raise Exception('Team not found')
        app.logger.error('Elasticsearch down, response: ' + str(response))
        raise Exception('Internal server error')
    
    except Exception as e:
        raise Exception(e)


def delete_all_users_from_team(team_id):
    try:
        rs = requests.session()
        must = [
            {'term': {'team_id': team_id}},
        ]
        query_json = {'query': {'bool': {'must': must}}}
        query_json['size'] = _es_size
        search_url = 'http://{}/{}/{}/_delete_by_query'.format(app.config['ES_HOST'], _es_index_user_team_edge, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        return response

    except Exception as e:
        raise Exception(e)


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
            if 'status' not in data:
                data['status'] = 'pending'
            item_list.append(data)

    return item_list


def get_user_team_edge(team_id, user_handle):
    print('get_user_team_edge: ', team_id, user_handle)
    rs = requests.session()
    must = [
        {'term': {'team_id': team_id}},
        {'term': {'user_handle': user_handle}}
    ]
    query_json = {'query': {'bool': {'must': must}}}
    query_json['size'] = 1
    print('query: ', json.dumps(query_json))
    search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_user_team_edge, _es_type)
    response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()

    print('response: ', json.dumps(response))

    if 'hits' in response:
        if response['hits']['total']['value'] > 0:
            return response['hits']['hits'][0]
    return None


def add_team_member(data):
    try:
        app.logger.info('add_team_members method called')
        rs = requests.session()

        resp = get_user_team_edge(data['team_id'], data['user_handle'])

        if resp is not None:
            raise Exception('Member already added')

        data['created_at'] = int(time.time())
        data['updated_at'] = int(time.time())

        post_url = 'http://{}/{}/{}'.format(app.config['ES_HOST'], _es_index_user_team_edge, _es_type)
        response = rs.post(url=post_url, json=data, headers=_http_headers).json()

        if 'result' in response and response['result'] == 'created':
            app.logger.info('add_team_members method completed')
            return response

        app.logger.error('Elasticsearch down, response: ' + str(response))
        raise Exception('Internal server error')

    except Exception as e:
        raise e


def update_team_member(data):
    try:
        app.logger.info('update_team_member method called')
        print('data: ', json.dumps(data))
        rs = requests.session()

        resp = get_user_team_edge(data['team_id'], data['user_handle'])

        if resp is None:
            raise Exception('Member not found')

        resp_data = resp['_source']
        resp_data['status'] = data['status']
        resp_data['updated_at'] = int(time.time())

        url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index_user_team_edge, _es_type, resp['_id'])
        response = rs.put(url=url, json=resp_data, headers=_http_headers).json()

        if 'result' in response:
            app.logger.info('update_team_member method completed')
            return response

        app.logger.error('Elasticsearch down, response: ' + str(response))
        raise Exception('Internal server error')

    except Exception as e:
        raise e


def delete_team_member(team_id, user_handle):
    try:
        app.logger.info('delete_team_member method called')
        rs = requests.session()
        resp = get_user_team_edge(team_id, user_handle)

        if resp is None:
            raise Exception('Member not found')

        url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index_user_team_edge, _es_type, resp['_id'])
        response = rs.delete(url=url, headers=_http_headers).json()

        if 'result' in response:
            app.logger.info('delete_team_member method completed')
            return response

        app.logger.error('Elasticsearch down, response: ' + str(response))
        raise Exception('Internal server error')

    except Exception as e:
        raise e


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


def search_teams_for_user(user_handle, param):
    try:
        app.logger.info('search_teams_for_user called')
        rs = requests.session()

        must = []
        must.append({'term': {'user_handle': user_handle}})
        for p in param:
            must.append({'term': {p: param[p]}})

        query_json = {'query': {'bool': {'must': must}}}
        query_json['query']['bool']['must_not'] = [
            {'term': {'status': 'rejected'}},
            {'term': {'status': 'removed'}},
            {'term': {'status': 'deleted'}}
        ]

        print('query_json: ', json.dumps(query_json))
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_user_team_edge, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        print('response: ', json.dumps(response))
        if 'hits' in response:
            item_list = []
            for hit in response['hits']['hits']:
                team_edge = hit['_source']
                print('Search details for: ', json.dumps(team_edge))
                team = get_team_details(team_edge['team_id'])
                print('Found Details')
                team['status'] = team_edge.get('status', 'pending')
                item_list.append(team)
            print('item_list', json.dumps(item_list))
            app.logger.info('Team search method completed')
            return item_list
        app.logger.error('Elasticsearch down, response: ' + str(response))
        raise Exception('Internal server error')

    except Exception as e:
        raise Exception('Internal server error')
