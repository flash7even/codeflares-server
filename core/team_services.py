import time
import json
import requests
import datetime
from flask import current_app as app

_http_headers = {'Content-Type': 'application/json'}

from core.user_services import search_user
from scrappers.codeforces_scrapper import CodeforcesScrapper

_es_index_user_team_edge = 'cp_training_user_team_edges'
_es_index_team = 'cp_training_teams'
_es_type = '_doc'
_es_size = 100


def get_team_rating_history(team_id):
    return [
        {
            "date": {
                "year": 2013, "month": 1, "day": 16
            },
            "rating": 1408
        },
        {
            "date": {
                "year": 2013, "month": 3, "day": 4
            },
            "rating": 1520
        },
        {
            "date": {
                "year": 2013, "month": 5, "day": 8
            },
            "rating": 1780
        },
        {
            "date": {
                "year": 2013, "month": 9, "day": 22
            },
            "rating": 1710
        },
        {
            "date": {
                "year": 2013, "month": 12, "day": 5
            },
            "rating": 1812
        },
        {
            "date": {
                "year": 2014, "month": 2, "day": 6
            },
            "rating": 1730
        },
        {
            "date": {
                "year": 2014, "month": 3, "day": 18
            },
            "rating": 1905
        },
        {
            "date": {
                "year": 2014, "month": 4, "day": 22
            },
            "rating": 2070
        }
    ]


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
                data['rating_history'] = get_team_rating_history(team_id)
                return data
            app.logger.warning('Team not found')
            raise Exception('Team not found')
        app.logger.error('Elasticsearch down, response: ' + str(response))
        raise Exception('Internal server error')
    
    except Exception as e:
        raise e


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
        raise e


def get_all_users_from_team(team_id):
    try:
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
    except Exception as e:
        raise e


def get_user_team_edge(team_id, user_handle):
    try:
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
    except Exception as e:
        raise e


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
        print('resp: ', resp)

        if resp is None:
            raise Exception('Member not found')

        url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index_user_team_edge, _es_type, resp['_id'])
        response = rs.delete(url=url, headers=_http_headers).json()
        print('response: ', response)

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
        raise e


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
        raise e


def get_rating_history_codeforces(team_id):
    try:
        members = get_all_users_from_team(team_id)
        handle_list = []
        handle_wise_rating = []
        history_list = []
        cf_scrapper = CodeforcesScrapper()

        for member in members:
            print('member details: ', member)
            user_handle = member['user_handle']
            matched_user_list = search_user({'username': user_handle}, 0, 1)
            if len(matched_user_list) > 0:
                user_details = matched_user_list[0]
                print('   user details: ', user_details)
                cf_handle = user_details.get('codeforces_handle', None)
                if cf_handle:
                    rating_history = cf_scrapper.get_user_rating_history(cf_handle)
                    handle_list.append({'user_handle': user_handle})
                    history_list.append(rating_history)

        date_list = []

        for idx in range(0, len(history_list)):
            history = history_list[idx]
            for contest in history:
                d = contest['ratingUpdateTimeSeconds']
                if d not in date_list:
                    date_list.append(d)

        date_list.sort()

        for history in history_list:
            date_list_len = len(date_list)
            idx = 0
            rating_list = []

            for c_idx in range(0, len(history)):
                contest = history[c_idx]
                contest_time = contest['ratingUpdateTimeSeconds']
                effect_end = date_list[len(date_list)-1]
                if c_idx+1 < len(history):
                    effect_end = history[c_idx+1]['ratingUpdateTimeSeconds']
                while idx < date_list_len:
                    if date_list[idx] <= effect_end:
                        rating_list.append({'rating': contest['newRating']})
                        idx += 1
                    else:
                        break

            handle_wise_rating.append(rating_list)

        rating_stat = []
        for date_idx in range(0, len(date_list)):
            day = datetime.date.fromtimestamp(date_list[date_idx])

            data = {
                'date': {
                    "year": day.year,
                    "month": day.month,
                    "day": day.day
                },
                'rating_list': []
            }

            for c_idx in range(0, len(handle_wise_rating)):
                data['rating_list'].append(handle_wise_rating[c_idx][date_idx])

            rating_stat.append(data)

        return {
            'handle_list': handle_list,
            'history': rating_stat
        }
    except Exception as e:
        raise e