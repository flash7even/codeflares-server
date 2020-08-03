import time
import json
import requests
from flask import current_app as app
from flask import request
from flask_restplus import Namespace, Resource

api = Namespace('support', description='Namespace for support services')

_http_headers = {'Content-Type': 'application/json'}


@api.route('/university')
class GetUniversity(Resource):

    @api.doc('get university list')
    def get(self):
        try:
            app.logger.info('Get university api called')
            file = open('./datasets/storage/university_list.txt', 'r')
            univ_lines = file.readlines()
            university_list = []
            for univ in univ_lines:
                univ = univ.rstrip("\n")
                university_list.append({'name': univ})

            app.logger.info('Get university api completed')
            return {
                'university_list': university_list
            }, 200
        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/country')
class GetCountry(Resource):

    @api.doc('get country list')
    def get(self):
        try:
            app.logger.info('Get country api called')
            file = open('./datasets/storage/country_list.txt', 'r')
            univ_lines = file.readlines()
            country_list = []
            for univ in univ_lines:
                univ = univ.rstrip("\n")
                country_list.append({'name': univ})

            app.logger.info('Get country api completed')
            return {
                'country_list': country_list
            }, 200
        except Exception as e:
            return {'message': str(e)}, 500
