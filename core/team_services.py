import time
import json
import requests
import datetime
from flask import current_app as app

_http_headers = {'Content-Type': 'application/json'}

from core.user_services import search_user, get_user_details
from scrappers.codeforces_scrapper import CodeforcesScrapper
from core.classroom_services import search_task_lists, search_class_lists
from core.user_services import get_user_details_by_handle_name
from core.notification_services import add_notification
from core.follower_services import get_follow_stat
from core.rating_services import search_user_ratings

_es_index_user_team_edge = 'cfs_user_team_edges'
_es_index_team = 'cfs_teams'
_es_type = '_doc'
_es_size = 100


def get_team_rating_history(team_id):
    rating_list = search_user_ratings(team_id)
    rating_history = []
    for rating_data in rating_list:
        day = datetime.date.fromtimestamp(rating_data['created_at'])
        data = {
            'rating': rating_data['skill_value'],
            'solve_count': rating_data['solve_count'],
            'date': {
                "year": day.year,
                "month": day.month,
                "day": day.day
            }
        }
        rating_history.append(data)
    return rating_history


def add_team_members_bulk(member_list, team_id, team_type, logged_in_user):
    try:
        team_lead = None
        for member in member_list:
            member_details = get_user_details_by_handle_name(member['user_handle'])

            edge = {
                'team_id': team_id,
                'team_type': team_type,
                'user_handle': member['user_handle'],
                'user_id': member_details['id'],
                'remarks': member.get('remarks', None),
                'status': 'confirmed'
            }

            if team_lead is not None:
                edge['status'] = 'pending'
            else:
                team_lead = member

            add_team_member(edge)

            notification_data = {
                'user_id': member_details['id'],
                'sender_id': logged_in_user,
                'notification_type': 'Team Invitation',
                'redirect_url': '/team/list/',
                'notification_text': 'You have been invited to join a team by',
                'status': 'UNREAD',
            }

            if team_type == 'classroom':
                notification_data = {
                    'user_id': member_details['id'],
                    'sender_id': logged_in_user,
                    'notification_type': 'Classroom Invitation',
                    'redirect_url': '/classroom/list/',
                    'notification_text': 'You have been invited to join a classroom by',
                    'status': 'UNREAD',
                }

            add_notification(notification_data)

    except Exception as e:
        raise e



def update_team_details(team_id, post_data):
    try:
        rs = requests.session()
        search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index_team, _es_type, team_id)
        response = rs.get(url=search_url, headers=_http_headers).json()
        if 'found' in response:
            if response['found']:
                data = response['_source']
                for key, value in post_data.items():
                    data[key] = value
                data['updated_at'] = int(time.time())
                response = rs.put(url=search_url, json=data, headers=_http_headers).json()
                if 'result' in response:
                    return response['result']
                else:
                    app.logger.error('Elasticsearch down, response: ' + str(response))
                    return response
            return {'message': 'not found'}
        app.logger.error('Elasticsearch down, response: ' + str(response))
        return response

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
                data['id'] = response['_id']
                data['member_list'] = get_all_users_from_team(team_id)
                data['rating_history'] = get_team_rating_history(team_id)
                data['task_list'] = search_task_lists({'classroom_id': team_id}, 0, 3)
                data['class_list'] = search_class_lists({'classroom_id': team_id}, 0, 3)
                user_details = get_user_details(data['team_leader_id'])
                data['team_leader_handle'] = user_details['username']
                data['follow_stat'] = get_follow_stat(data['id'])
                data['created_at'] = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(data['created_at']))
                return data
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
        rs = requests.session()
        must = [
            {'term': {'team_id': team_id}},
            {'term': {'user_handle': user_handle}}
        ]
        query_json = {'query': {'bool': {'must': must}}}
        query_json['size'] = 1
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_user_team_edge, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()

        if 'hits' in response:
            if response['hits']['total']['value'] > 0:
                return response['hits']['hits'][0]
    except Exception as e:
        raise e


def add_team_member(data):
    try:
        rs = requests.session()

        resp = get_user_team_edge(data['team_id'], data['user_handle'])

        if resp is not None:
            raise Exception('Member already added')

        data['created_at'] = int(time.time())
        data['updated_at'] = int(time.time())

        post_url = 'http://{}/{}/{}'.format(app.config['ES_HOST'], _es_index_user_team_edge, _es_type)
        response = rs.post(url=post_url, json=data, headers=_http_headers).json()

        if 'result' in response and response['result'] == 'created':
            return response

        app.logger.error('Elasticsearch down, response: ' + str(response))
        raise Exception('Internal server error')
    except Exception as e:
        raise e


def update_team_member(data):
    try:
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
            return response

        app.logger.error('Elasticsearch down, response: ' + str(response))
        raise Exception('Internal server error')

    except Exception as e:
        raise e


def delete_team_member(team_id, user_handle):
    try:
        rs = requests.session()
        resp = get_user_team_edge(team_id, user_handle)

        if resp is None:
            raise Exception('Member not found')

        url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index_user_team_edge, _es_type, resp['_id'])
        response = rs.delete(url=url, headers=_http_headers).json()

        if 'result' in response:
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
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_team, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        if 'hits' in response:
            item_list = []
            for hit in response['hits']['hits']:
                team = hit['_source']
                team['id'] = hit['_id']
                member_edge_list = get_all_users_from_team(team['id'])
                team['member_list'] = member_edge_list
                item_list.append(team)
            return item_list
        app.logger.error('Elasticsearch down, response: ' + str(response))
        raise Exception('Internal server error')

    except Exception as e:
        raise e


def search_teams_for_user(user_handle, param):
    try:
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

        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_user_team_edge, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        if 'hits' in response:
            item_list = []
            rank = 1
            for hit in response['hits']['hits']:
                team_edge = hit['_source']
                team = get_team_details(team_edge['team_id'])
                team['status'] = team_edge.get('status', 'pending')
                team['rank'] = rank
                rank += 1
                item_list.append(team)
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
            user_handle = member['user_handle']
            matched_user_list = search_user({'username': user_handle}, 0, 1)
            if len(matched_user_list) > 0:
                user_details = matched_user_list[0]
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
                effect_end = int(time.time())
                if c_idx+1 < len(history):
                    effect_end = history[c_idx+1]['ratingUpdateTimeSeconds']
                while idx < date_list_len:
                    if date_list[idx] < effect_end:
                        rating_list.append({'rating': history[c_idx]['newRating']})
                        idx += 1
                    else:
                        break

            handle_wise_rating.append(rating_list)

        rating_stat = []
        for date_idx in range(0, len(date_list)):
            day = datetime.date.fromtimestamp(date_list[date_idx])

            data = {
                'epoc_time': date_list[date_idx],
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
