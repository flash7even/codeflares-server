import datetime
import time
import requests
from flask import current_app as app

_http_headers = {'Content-Type': 'application/json'}

_es_index_user_ratings = 'cfs_user_rating_records'

_es_type = '_doc'
_es_size = 500


def search_user_ratings(user_id):
    try:
        rs = requests.session()
        must = [{'term': {'user_id': user_id}}]
        query_json = {'query': {'bool': {'must': must}}}
        query_json['sort'] = [{'created_at': {'order': 'asc'}}]
        query_json['size'] = _es_size
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_user_ratings, _es_type)
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


def add_user_ratings(user_id, skill_value, solve_count):
    try:
        rs = requests.session()
        data = {
            'user_id': user_id,
            'skill_value': skill_value,
            'solve_count': solve_count,
            'created_at': int(time.time()),
            'updated_at': int(time.time())
        }
        post_url = 'http://{}/{}/{}'.format(app.config['ES_HOST'], _es_index_user_ratings, _es_type)
        response = rs.post(url=post_url, json=data, headers=_http_headers).json()
        if 'result' in response and response['result'] == 'created':
            return {'message': 'success'}
        app.logger.error('Elasticsearch down, response: ' + str(response))
        raise Exception('ES Down')
    except Exception as e:
        raise e


def get_user_rating_history(user_id):
    rating_list = search_user_ratings(user_id)
    rating_history = []
    for rating_data in rating_list:
        daytime = datetime.datetime.fromtimestamp(rating_data['created_at'])
        daytime = daytime.strftime('%Y %m %d %H %M %S')
        daytime = daytime.split(' ')
        data = {
            'rating': rating_data['skill_value'],
            'solve_count': rating_data['solve_count'],
            'date': {
                "year": daytime[0],
                "month": daytime[1],
                "day": daytime[2],
                "hour": daytime[3],
                "minute": daytime[4],
                "second": daytime[5],
            },
            'created_at': rating_data['created_at']
        }
        rating_history.append(data)
    return rating_history
