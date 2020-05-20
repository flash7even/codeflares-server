import time
import json
import requests
from flask import current_app as app
import random
import math

from core.problem_category_services import search_problem_list_simplified

_http_headers = {'Content-Type': 'application/json'}

_es_index_contest = 'cfs_contests'

_es_type = '_doc'
_es_size = 100


class ContestModel:

    def add_category_for_problem_selection(self, category_params, category_map, cat):
        try:
            category_name = cat['category_name']
            data = {
                'category_name': category_name,
                'minimum_difficulty': float(cat.get('minimum_difficulty', 0)),
                'maximum_difficulty': float(cat.get('maximum_difficulty', 0)),
                'minimum_problem': int(cat.get('minimum_problem', 0)),
                'maximum_problem': int(cat.get('maximum_problem', 0)),
            }
            if data['minimum_difficulty'] > data['maximum_difficulty'] or data['minimum_problem'] > data['maximum_problem']:
                raise Exception('Invalid data provided')
            category_map[category_name] = 1
            category_params.append(data)
        except Exception as e:
            raise e

    def create_problem_set_for_contest(self, param_list, category_configs_by_level, problem_count, solved_problem_list):
        try:
            category_params = []
            category_map = {}
            # FIRST SELECT THE CATEGORY PROVIDED BY CLIENT
            for param in param_list:
                self.add_category_for_problem_selection(category_params, category_map, param)

            print('Added category_params based on given param list: ', category_params)

            # NOW SELECT THE CATEGORY NOT PROVIDED BY CLIENT
            for cat in category_configs_by_level:
                category_name = cat['category_name']
                if category_name in category_map:
                    continue
                self.add_category_for_problem_selection(category_params, category_map, cat)

            print('Added category_params with remaining list: ', category_params)

            # NOW SELECT THE PROBLEM FROM CATEGORY PARAM LIST
            selected_problem_list = self.generate_problem_set(problem_count, category_params, solved_problem_list)
            print('selected_problem_list: ', selected_problem_list)
            return selected_problem_list
        except Exception as e:
            raise e

    def find_random_index_by_probability(self, szz, upper_half_start):
        try:
            mid = int(math.ceil(szz/2))
            prob = random.randint(1, 100)
            if prob >= upper_half_start:
                return random.randint(mid, szz)
            else:
                return random.randint(0, szz)
        except Exception as e:
            raise e

    def add_problem_from_chosen_list(self, selected_problems, problem_list, count):
        try:
            while count > 0 and len(problem_list) > 0:
                pos = self.find_random_index_by_probability(len(problem_list)-1, 50)
                selected_problems.append(problem_list[pos])
                count -= 1
                problem_list = [item for item in problem_list if item not in selected_problems]
            return selected_problems
        except Exception as e:
            raise e

    def generate_problem_set(self, needed_problem, category_params, black_listed):
        try:
            selected_problems = []
            random_min_diff = 0
            random_max_diff = 0

            # FIRST SELECT THE PROBLEMS BASED ON QUERY PARAMS
            for category in category_params:
                if len(selected_problems) == needed_problem:
                    break
                if category['category_name'] == 'random_choice':
                    random_min_diff = category['minimum_difficulty']
                    random_max_diff = category['maximum_difficulty']
                    continue
                take_now = random.randint(category['minimum_problem'], category['maximum_problem'])
                take_now = min(take_now, needed_problem - len(selected_problems))
                search_param = {
                    'category_root': category['category_name'],
                    'minimum_difficulty': category['minimum_difficulty'],
                    'maximum_difficulty': category['maximum_difficulty'],
                }
                problem_list = search_problem_list_simplified(search_param)
                problem_list = [item for item in problem_list if item not in black_listed]
                selected_problems = self.add_problem_from_chosen_list(selected_problems, problem_list, take_now)

            if len(selected_problems) == needed_problem:
                return selected_problems

            # NOW SELECT THE PROBLEMS RANDOMLY FOLLOWING THE DIFFICULTY RANGE
            search_param = { 'minimum_difficulty': random_min_diff, 'maximum_difficulty': random_max_diff}
            problem_list = search_problem_list_simplified(search_param)
            problem_list = [item for item in problem_list if item not in black_listed]
            selected_problems = self.add_problem_from_chosen_list(selected_problems, problem_list, needed_problem-len(selected_problems))

            if len(selected_problems) == needed_problem:
                return selected_problems

            # NOW SELECT THE PROBLEMS IN COMPLETE RANDOM ORDER
            problem_list = search_problem_list_simplified({})
            problem_list = [item for item in problem_list if item not in black_listed]
            selected_problems = self.add_problem_from_chosen_list(selected_problems, problem_list, needed_problem-len(selected_problems))
            return selected_problems
        except Exception as e:
            raise e
