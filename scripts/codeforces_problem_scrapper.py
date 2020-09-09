import time
import os
import json
import requests


rs = requests.session()
_http_headers = {'Content-Type': 'application/json'}


ADMIN_USER = os.getenv('ADMIN_USERNAME')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')
SERVER_HOST = 'http://localhost:5056/api'

access_token = None
login_api = f'{SERVER_HOST}/auth/login'
add_problem_url = f'{SERVER_HOST}/problem/'


tag_map = {
   "dp":"non_classical_dp",
   "strings":"ad_hoc",
   "sortings":"ad_hoc",
   "two pointers":"two_pointer",
   "greedy":"basic_greedy_knowledge",
   "math":"basic_math",
   "brute force":"ad_hoc",
   "number theory":"factorization",
   "constructive algorithms":"constructive_algorithm",
   "dfs and similar":"dfs",
   "graphs":"basic_graph_knowledge",
   "shortest paths":"dijkstra",
   "data structures":"segment_tree",
   "fft":"fft",
   "interactive":"interactive",
   "implementation":"implementation",
   "flows":"max_flow",
   "graph matchings":"maximum_bipartite_matching",
   "binary search":"binary_search",
   "games":"nim",
   "trees":"tree_dp",
   "*special":"ad_hoc",
   "combinatorics":"basic_permutation_combination",
   "2-sat":"two_sat",
   "matrices":"implementation",
   "geometry":"basic_geometry_knowledge",
   "dsu":"union_find",
   "bitmasks":"bit_mask",
   "string suffix structures":"suffix_array",
   "divide and conquer":"non_classical_dp",
   "ternary search":"ternary_search",
   "hashing":"hashing",
   "probabilities":"basic_probability",
   "meet-in-the-middle":"meet_in_the_middle",
   "expression parsing":"implementation",
   "chinese remainder theorem":"chinese_remainder_theorem",
   "schedules":"interval_scheduling"
}

rating_list = [0, 500, 750, 1000, 1500, 2000, 2500, 3000, 3500, 4000, 5000]
problem_count = 0
problem_count_without_rating = 0
error_count = 0


def get_access_token():
    try:
        global rs
        login_data = {
            "username": ADMIN_USER,
            "password": ADMIN_PASSWORD
        }
        response = rs.post(url=login_api, json=login_data, headers=_http_headers).json()
        return response['access_token']
    except Exception as e:
        raise Exception('Internal server error')


def get_header():
    try:
        global rs
        global access_token
        if access_token is None:
            access_token = get_access_token()
        auth_headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }
        return auth_headers
    except Exception as e:
        raise Exception('Internal server error')


def add_problem(problem_data):
    global problem_count
    global error_count
    try:
        global rs
        auth_header = get_header()
        response = rs.post(url=add_problem_url, json=problem_data, headers=auth_header).json()
        # print('response: ', response)
        problem_count += 1
    except Exception as e:
        error_count += 1
        print(f'Exception: {e}')



class CodeforcesScrapper:

    def get_problem_stats(self):
        try:
            rs = requests.session()
            url = f'https://codeforces.com/api/problemset.problems'
            response = rs.get(url=url, headers=_http_headers).json()
            problem_list = response['result']['problems']

            tags = []
            contest_list = []
            problem_count = 0
            contest_count = 0
            programming_problem_count = 0

            for problem in problem_list:
                problem_count += 1
                tag_list = problem['tags']
                contest_id = problem['contestId']

                if problem['type'] == 'PROGRAMMING':
                    programming_problem_count += 1
                else:
                    continue

                if contest_id not in contest_list:
                    contest_list.append(contest_id)
                    contest_count += 1

                for tag in tag_list:
                    if tag not in tags:
                        tags.append(tag)

            return {
                'problem_count': problem_count,
                'programming_problem_count': programming_problem_count,
                'contest_count': contest_count,
                'tag_count': len(tags),
                'tags': tags,
            }
        except Exception as e:
            return {
                'tags': [],
                'problem_count': 0,
                'tag_count': 0
            }

    def get_problem_tags(self):
        try:
            rs = requests.session()
            url = f'https://codeforces.com/api/problemset.problems'
            response = rs.get(url=url, headers=_http_headers).json()
            problem_list = response['result']['problems']

            tags = {}
            problem_count = 0
            programming_problem_count = 0

            for problem in problem_list:
                problem_count += 1
                tag_list = problem['tags']

                if problem['type'] == 'PROGRAMMING':
                    programming_problem_count += 1
                else:
                    continue

                for tag in tag_list:
                    if tag not in tags:
                        tags[tag] = tag

            return tags
        except Exception as e:
            return {}


    def get_difficulty_from_rating(self, rating):
        rating = int(rating)

        dif1 = 0

        while dif1 <= 10:
            if rating >= rating_list[dif1]:
                break
            dif1 += 1

        rating_ext = rating - rating_list[dif1]
        rating_dif = rating_list[dif1+1] - rating_list[dif1]

        dif = dif1 + rating_ext/rating_dif
        return dif


    def upload_problems(self):
        try:
            rs = requests.session()
            url = f'https://codeforces.com/api/problemset.problems'
            response = rs.get(url=url, headers=_http_headers).json()
            problem_list = response['result']['problems']

            global problem_count
            global problem_count_without_rating
            global error_count

            for problem in problem_list:
                tag_list = problem['tags']

                if 'rating' not in problem:
                    problem_count_without_rating += 1
                    continue

                problem_data = {
                    "problem_name": problem['name'],
                    "problem_id": f'{problem["contestId"]}/{problem["index"]}',
                    "problem_description": "NA",
                    "problem_difficulty": self.get_difficulty_from_rating(problem['rating']),
                    "problem_significance": 1,
                    "source_link": f'https://codeforces.com/contest/{problem["contestId"]}/problem/{problem["index"]}',
                    "category_dependency_list": [],
                    "oj_name": "codeforces",
                    "active_status": "pending"
                }

                for tag in tag_list:
                    if tag in tag_map:
                        edge = {
                            'category_name': tag_map[tag],
                            'factor': 7.5
                        }
                        problem_data['category_dependency_list'].append(edge)

                if len(problem_data['category_dependency_list']) > 1:
                    problem_data['problem_significance'] = 2

                add_problem(problem_data)

                if problem_count % 50 == 0:
                    print(f'problem_count: {problem_count}, problem_count_without_rating: {problem_count_without_rating}, error_count: {error_count}')

            return {
                'problem_count': problem_count,
                'problem_count_without_rating': problem_count_without_rating,
                'error_count': error_count
            }
        except Exception as e:
            print(f'Exception: {e}')
            raise e


if __name__ == '__main__':
    try:
        print('START RUNNING CODEFORCES SCRAPPER SCRIPT\n')
        codeforces_scrapper = CodeforcesScrapper()
        resp = codeforces_scrapper.upload_problems()
        print('Final Response: ', json.dumps(resp))
    except Exception as e:
        print(f'Exception: {e}')