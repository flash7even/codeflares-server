import time
import json
import requests
import os
import logging
import re
import os
import json
from logging.handlers import TimedRotatingFileHandler
from bs4 import BeautifulSoup
import re


logger = logging.getLogger('category uploader logger')
logger.setLevel(logging.DEBUG)
handler = TimedRotatingFileHandler('../logs/a2oj_uploader.log', when='midnight', interval=1,  backupCount=30)
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter(
    fmt='[%(asctime)s.%(msecs)03d] [%(levelname)s]: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))
handler.suffix = "%Y%m%d"
handler.extMatch = re.compile(r"^\d{8}$")
logger.addHandler(handler)

rs = requests.session()
_http_headers = {'Content-Type': 'application/json'}


ADMIN_USER = os.getenv('ADMIN_USERNAME')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')
SERVER_HOST = 'http://localhost:5056/api'

access_token = None
login_api = f'{SERVER_HOST}/auth/login'
add_problem_url = f'{SERVER_HOST}/problem/merge-data'


algorithm_map = {
    "56": {
        "algorithm_list": ["basic_greedy_knowledge"],
        "min_difficulty": 1,
        "max_difficulty": 8
    },
    "86": {
        "algorithm_list": ["basic_math"],
        "min_difficulty": 1,
        "max_difficulty": 8.5
    },
    "85": {
        "algorithm_list": ["ad_hoc"],
        "min_difficulty": 0.5,
        "max_difficulty": 7
    },
    "94": {
        "algorithm_list": ["constructive_algorithm"],
        "min_difficulty": 2,
        "max_difficulty": 10
    },
    "95": {
        "algorithm_list": ["ad_hoc"],
        "min_difficulty": 1.5,
        "max_difficulty": 7
    },
    "90": {
        "algorithm_list": ["basic_permutation_combination"],
        "min_difficulty": 2,
        "max_difficulty": 8
    },
    "12": {
        "algorithm_list": ["max_flow"],
        "min_difficulty": 4,
        "max_difficulty": 10
    },
    "100": {
        "algorithm_list": ["basic_probability"],
        "min_difficulty": 2.5,
        "max_difficulty": 9
    },
    "96": {
        "algorithm_list": ["two_pointer"],
        "min_difficulty": 2.5,
        "max_difficulty": 7.5
    },
    "98": {
        "algorithm_list": ["union_find"],
        "min_difficulty": 3,
        "max_difficulty": 8
    },
    "97": {
        "algorithm_list": ["bit_mask"],
        "min_difficulty": 2.2,
        "max_difficulty": 8
    },
    "93": {
        "algorithm_list": ["hashing"],
        "min_difficulty": 3,
        "max_difficulty": 8.5
    },
    "26": {
        "algorithm_list": ["binary_index_tree"],
        "min_difficulty": 4,
        "max_difficulty": 9
    },
    "49": {
        "algorithm_list": ["trie"],
        "min_difficulty": 3.5,
        "max_difficulty": 8.5
    },
    "119": {
        "algorithm_list": ["basic_backtracking"],
        "min_difficulty": 3.5,
        "max_difficulty": 7.5
    },
    "58": {
        "algorithm_list": ["maximum_bipartite_matching"],
        "min_difficulty": 4.5,
        "max_difficulty": 10
    },
    "126": {
        "algorithm_list": ["non_classical_dp"],
        "min_difficulty": 4,
        "max_difficulty": 10
    },
    "76": {
        "algorithm_list": ["bfs"],
        "min_difficulty": 3,
        "max_difficulty": 8.5
    },
    "72": {
        "algorithm_list": ["heavy_light_decomposition"],
        "min_difficulty": 5,
        "max_difficulty": 10
    },
    "377": {
        "algorithm_list": ["suffix_array"],
        "min_difficulty": 5.5,
        "max_difficulty": 10
    },
    "29": {
        "algorithm_list": ["kmp"],
        "min_difficulty": 4.5,
        "max_difficulty": 10
    },
    "36": {
        "algorithm_list": ["implementation"],
        "min_difficulty": 3,
        "max_difficulty": 9
    },
    "44": {
        "algorithm_list": ["suffix_array"],
        "min_difficulty": 3,
        "max_difficulty": 10
    },
    "125": {
        "algorithm_list": ["knapsack"],
        "min_difficulty": 3.5,
        "max_difficulty": 9
    },
    "42": {
        "algorithm_list": ["fft"],
        "min_difficulty": 6.5,
        "max_difficulty": 10
    },
    "22": {
        "algorithm_list": ["convex_hull"],
        "min_difficulty": 4.5,
        "max_difficulty": 10
    },
    "79": {
        "algorithm_list": ["longest_increasing_subsequence"],
        "min_difficulty": 3,
        "max_difficulty": 8
    },
    "31": {
        "algorithm_list": ["topological_sort"],
        "min_difficulty": 4,
        "max_difficulty": 8
    },
    "318": {
        "algorithm_list": ["mo_algorithm"],
        "min_difficulty": 4,
        "max_difficulty": 9.5
    },
    "124": {
        "algorithm_list": ["longest_common_subsequence"],
        "min_difficulty": 3,
        "max_difficulty": 7.5
    },
    "30": {
        "algorithm_list": ["meet_in_the_middle"],
        "min_difficulty": 3,
        "max_difficulty": 7
    },
    "319": {
        "algorithm_list": ["centroid_decomposition"],
        "min_difficulty": 5.5,
        "max_difficulty": 10
    },
    "84": {
        "algorithm_list": ["basic_backtracking"],
        "min_difficulty": 1.5,
        "max_difficulty": 7
    },
    "150": {
        "algorithm_list": ["lowest_common_ancestor", "sparse_table"],
        "min_difficulty": 3.5,
        "max_difficulty": 8
    },
    "27": {
        "algorithm_list": ["line_sweep"],
        "min_difficulty": 5,
        "max_difficulty": 10
    },
    "59": {
        "algorithm_list": ["gaussian_elimination"],
        "min_difficulty": 5,
        "max_difficulty": 10
    },
    "35": {
        "algorithm_list": ["aho_corasick"],
        "min_difficulty": 5.5,
        "max_difficulty": 10
    },
    "208": {
        "algorithm_list": ["lowest_common_ancestor", "sparse_table"],
        "min_difficulty": 3.5,
        "max_difficulty": 8
    },
    "231": {
        "algorithm_list": ["strongly_connected_component"],
        "min_difficulty": 4,
        "max_difficulty": 9
    },
    "92": {
        "algorithm_list": ["implementation"],
        "min_difficulty": 0.5,
        "max_difficulty": 8
    },
    "40": {
        "algorithm_list": ["binary_search", "ternary_search"],
        "min_difficulty": 3,
        "max_difficulty": 9
    },
    "14": {
        "algorithm_list": ["treap", "splay_tree"],
        "min_difficulty": 5.5,
        "max_difficulty": 10
    },
    "65": {
        "algorithm_list": ["two_sat"],
        "min_difficulty": 4.5,
        "max_difficulty": 9
    },
    "69": {
        "algorithm_list": ["priority_queue"],
        "min_difficulty": 1.5,
        "max_difficulty": 8
    },
    "216": {
        "algorithm_list": ["bit_manipulation"],
        "min_difficulty": 2,
        "max_difficulty": 7
    },
    "64": {
        "algorithm_list": ["articulation_point"],
        "min_difficulty": 3.5,
        "max_difficulty": 9
    },
    "610": {
        "algorithm_list": ["sqrt_decomposition"],
        "min_difficulty": 3.5,
        "max_difficulty": 9
    },
    "80": {
        "algorithm_list": ["bellaman_ford"],
        "min_difficulty": 3.5,
        "max_difficulty": 8
    },
    "165": {
        "algorithm_list": ["dijkstra"],
        "min_difficulty": 3.5,
        "max_difficulty": 10
    },
    "54": {
        "algorithm_list": ["maximum_bipartite_matching"],
        "min_difficulty": 4.5,
        "max_difficulty": 10
    },
    "130": {
        "algorithm_list": ["coin_change"],
        "min_difficulty": 3.5,
        "max_difficulty": 8
    },
    "103": {
        "algorithm_list": ["edit_distance"],
        "min_difficulty": 3,
        "max_difficulty": 7
    },
    "651": {
        "algorithm_list": ["persistent_data_structure"],
        "min_difficulty": 5,
        "max_difficulty": 10
    },
    "131": {
        "algorithm_list": ["floyd_warshall"],
        "min_difficulty": 3.5,
        "max_difficulty": 8
    },
    "669": {
        "algorithm_list": ["mobius_function"],
        "min_difficulty": 5,
        "max_difficulty": 9
    },
    "21": {
        "algorithm_list": ["basic_vector_geometry"],
        "min_difficulty": 2,
        "max_difficulty": 8
    },
    "87": {
        "algorithm_list": ["basic_stl"],
        "min_difficulty": 0.5,
        "max_difficulty": 7
    },
    "32": {
        "algorithm_list": ["matrix_exponentiation"],
        "min_difficulty": 4.5,
        "max_difficulty": 10
    },
    "91": {
        "algorithm_list": ["non_classic_games"],
        "min_difficulty": 2,
        "max_difficulty": 8
    },
    "62": {
        "algorithm_list": ["ad_hoc"],
        "min_difficulty": 0.5,
        "max_difficulty": 5
    },
    "99": {
        "algorithm_list": ["divide_and_conquer"],
        "min_difficulty": 3.5,
        "max_difficulty": 8
    },
    "743": {
        "algorithm_list": ["interactive"],
        "min_difficulty": 3.5,
        "max_difficulty": 8
    },
    "227": {
        "algorithm_list": ["suffix_array"],
        "min_difficulty": 7,
        "max_difficulty": 10
    },
    "166": {
        "algorithm_list": ["basic_stl"],
        "min_difficulty": 3.5,
        "max_difficulty": 8
    },
    "48": {
        "algorithm_list": ["non_classic_games"],
        "min_difficulty": 2,
        "max_difficulty": 6
    },
    "671": {
        "algorithm_list": ["randomized_algorithm"],
        "min_difficulty": 1.5,
        "max_difficulty": 7
    },
    "308": {
        "algorithm_list": ["segment_tree"],
        "min_difficulty": 4.5,
        "max_difficulty": 8
    },
    "348": {
        "algorithm_list": ["matrix_exponentiation"],
        "min_difficulty": 2,
        "max_difficulty": 6
    },
    "37": {
        "algorithm_list": ["sparse_table"],
        "min_difficulty": 4.5,
        "max_difficulty": 8
    },
    "315": {
        "algorithm_list": ["digit_dp"],
        "min_difficulty": 4,
        "max_difficulty": 8
    },
    "13": {
        "algorithm_list": ["bfs", "dfs", "dijkstra"],
        "min_difficulty": 3.5,
        "max_difficulty": 10
    },
    "33": {
        "algorithm_list": ["non_classical_dp"],
        "min_difficulty": 3.5,
        "max_difficulty": 10
    },
    "101": {
        "algorithm_list": ["non_classical_graph"],
        "min_difficulty": 3,
        "max_difficulty": 10
    },
    "41": {
        "algorithm_list": ["non_classical_nt"],
        "min_difficulty": 1.5,
        "max_difficulty": 9
    },
    "88": {
        "algorithm_list": ["non_classical_ds"],
        "min_difficulty": 4,
        "max_difficulty": 10
    },
    "89": {
        "algorithm_list": ["tree_dp", "dfs", "basic_tree_knowledge", "non_classical_dp"],
        "min_difficulty": 3.5,
        "max_difficulty": 10
    },
    "17": {
        "algorithm_list": ["non_classical_graph", "minimum_spanning_tree", "strongly_connected_component"],
        "min_difficulty": 4,
        "max_difficulty": 7.5
    },
    "134": {
        "algorithm_list": ["ad_hoc"],
        "min_difficulty": 0.2,
        "max_difficulty": 1
    },
    "24": {
        "algorithm_list": ["euler_circuit"],
        "min_difficulty": 3.5,
        "max_difficulty": 7
    },
}


success = 0
error = 0


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
    global rs
    global success
    global error
    try:
        auth_header = get_header()
        response = rs.post(url=add_problem_url, json=problem_data, headers=auth_header).json()
        if 'message' in response:
            logger.error(f'Error uploading problem, response: {response}, problem_data: {problem_data}')
            error += 1
        else:
            logger.info(f'response: {response}')
            success += 1
    except Exception as e:
        logger.warning(f'Exception: {e}')
        error += 1



oj_map = {
    "SPOJ": "spoj",
    "CodeChef": "codechef",
    "Codeforces": "codeforces",
    "UVA": "uva"
}


def update_difficulties(problem_list, min_diff, max_diff):
    if len(problem_list) == 0:
        return problem_list
    total = len(problem_list)
    diff_range = max_diff - min_diff
    dx = diff_range/total
    cur_diff = min_diff

    for problem in problem_list:
        problem['problem_difficulty'] = cur_diff
        problem['problem_difficulty'] = round(problem['problem_difficulty'], 2)
        cur_diff += dx
        if cur_diff > max_diff:
            cur_diff = max_diff

    return problem_list


def get_uva_problem_id(source_link):
    logger.info(f'get_uva_problem_id called for source_link: {source_link}')
    try:
        rs = requests.session()
        url_spilts = source_link.split("=")
        logger.info(f'url_spilts: {url_spilts}')
        problem_id = url_spilts[len(url_spilts)-1]
        logger.info(f'problem_id: {problem_id}')
        url = f'https://uhunt.onlinejudge.org/api/p/id/{problem_id}'
        problem_info = rs.get(url=url, headers=_http_headers).json()
        logger.info(f'problem_info: {problem_info}')
        problem_num = problem_info['num']
        logger.info(f'UVA problem_id: {problem_id}, problem_num: {problem_num}')
        return str(problem_num)
    except Exception as e:
        logger.error(f'Could not scrap UVA problem id for source_link: {source_link}: {str(e)}')
        return source_link


def get_problem_id(source_link, oj_name):
    try:
        if oj_name == 'uva':
            problem_id = get_uva_problem_id(source_link)
            return problem_id

        if source_link.endswith('/') is False:
            source_link += '/'

        words = source_link.split("/")
        if oj_name == 'codeforces':
            problem_id = words[len(words)-3] + '/' + words[len(words)-2]
        else:
            problem_id = words[len(words)-2]
        return problem_id
    except Exception as e:
        logger.error(f'Could not problem id for source_link: {source_link}, oj_name: {oj_name}')
        return source_link


class A2ojScrapper:

    def test_upload(self, algorithm_id, algorithm_list, min_diff, max_diff):
        logger.info(f'upload_problem_history called, algorithm_list: {algorithm_list}, min_diff: {min_diff}')
        rs = requests.session()
        url = f'https://a2oj.com/category?ID={algorithm_id}'
        submission_page = rs.get(url=url, headers=_http_headers, verify=False)
        soup = BeautifulSoup(submission_page.text, 'html.parser')
        soup.prettify()

        header_map = {}

        table = soup.find("table",{"class":"tablesorter"})
        for row in table.find_all("tr")[0:]:
            cells = row.find_all("th")
            idx = 0
            for cell in cells:
                cell = str(cell)
                cell = cell[4:-5]
                header_map[cell] = idx
                idx += 1
            print(header_map)
            break


    def upload_problem_history(self, algorithm_id, algorithm_list, min_diff, max_diff):
        logger.info(f'upload_problem_history called, algorithm_list: {algorithm_list}, min_diff: {min_diff}')
        rs = requests.session()
        url = f'https://a2oj.com/category?ID={algorithm_id}'
        submission_page = rs.get(url=url, headers=_http_headers, verify=False)
        soup = BeautifulSoup(submission_page.text, 'html.parser')
        soup.prettify()

        problem_list = []
        header_map = {}
        table = soup.find("table",{"class":"tablesorter"})

        for row in table.find_all("tr")[0:]:
            cells = row.find_all("th")
            idx = 0
            for cell in cells:
                cell = str(cell)
                cell = cell[4:-5]
                header_map[cell] = idx
                idx += 1
            break

        logger.info(f'HEADER_MAP: {header_map}')

        for row in table.find_all("tr")[1:]:  # skipping header row
            cells = row.find_all("td")
            try:
                problem_name_idx = header_map["Problem Name"]
                oj_name_idx = header_map["Online Judge"]
                problem_difficulty_idx = header_map["Difficulty Level"]

                problem_name = cells[problem_name_idx].text
                source_link = cells[problem_name_idx].find('a').get('href')
                oj_name = cells[oj_name_idx].text
                problem_difficulty = cells[problem_difficulty_idx].text
                logger.info(f'TABLE_PROBLEM_STAT: problem_name: {problem_name}, source_link: {source_link}, oj_name: {oj_name}, problem_difficulty: {problem_difficulty}')

                if oj_name not in oj_map:
                    continue

                oj_name = oj_map[oj_name]

                if oj_name == "codeforces":
                    if "gym" in source_link:
                        continue

                problem_id = get_problem_id(source_link, oj_name)

                problem_data = {
                    "problem_name": problem_name,
                    "problem_id": problem_id,
                    "problem_description": "NA",
                    "problem_difficulty": problem_difficulty,
                    "problem_significance": 1,
                    "source_link": str(source_link),
                    "category_dependency_list": [],
                    "oj_name": oj_name,
                    "active_status": "approved"
                }

                for algorithm_name in algorithm_list:
                    problem_data['category_dependency_list'].append(
                        {
                            'category_name': algorithm_name,
                            'factor': 7.5
                        }
                    )
                problem_list.append(problem_data)
            except Exception as e:
                logger.warning(f'Exception occurred for problem cells: {cells}, Exception: {str(e)}')
                global error
                error += 1

        problem_list = update_difficulties(problem_list, min_diff, max_diff)

        if len(problem_list) == 0:
            logger.warning('no problem list found')

        for problem in problem_list:
            add_problem(problem)
            if success % 50 == 0:
                logger.info(f'Problem submission statistics, success: {success}, error: {error}')
                print(f'Problem submission statistics, success: {success}, error: {error}')

        return {
            "problem_list": problem_list
        }

    def uva_scrapper(self):
        problem_url = 'https://onlinejudge.org/index.php?option=onlinejudge&page=show_problem&problem=1140'
        rs = requests.session()
        problem_page = rs.get(url=problem_url, headers=_http_headers)
        soup = BeautifulSoup(problem_page.text, 'html.parser')
        soup = soup.find("div", {"id": "col3_content_wrapper"})
        first_table = soup.select_one("table:nth-of-type(1)")

        # print(first_table)

        for row in first_table.find_all("tr")[1:]:  # skipping header row
            cells = row.find_all("td")
            problem_info_cell = cells[0]
            header_info = problem_info_cell.find('h3')
            header_info = str(header_info)
            header_info = header_info[4:-5]
            header_info = header_info.split("- ")
            problem_id = header_info[0]
            problem_name = header_info[1]
            problem_id = problem_id.strip()
            problem_name = problem_name.strip()
            print("problem_id:", problem_id, " problem_name: ", problem_name)


if __name__ == '__main__':
    print('START RUNNING CODECHEF SCRAPPER SCRIPT\n')
    a2oj_scrapper = A2ojScrapper()

    for algorithm_id in algorithm_map:
        logger.info(f'Problem upload for algorithm_id: {algorithm_id}')
        print(f'Problem upload for algorithm_id: {algorithm_id}')
        algorithm_list = algorithm_map[algorithm_id]['algorithm_list']
        min_difficulty = algorithm_map[algorithm_id]['min_difficulty']
        max_difficulty = algorithm_map[algorithm_id]['max_difficulty']
        a2oj_scrapper.upload_problem_history(algorithm_id, algorithm_list, min_difficulty , max_difficulty)
        logger.info(f'Problem upload for algorithm_id: {algorithm_id} completed')
