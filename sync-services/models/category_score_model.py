import argparse
import json
import random
import math

eps = 0.000000000001


class CategoryScoreGenerator:

    dependent_percentage = 70
    own_skill_percentage = 30

    dependent_skill_score_table = [0, 15, 30, 44, 57, 70, 79, 87, 93, 98, 100, 100]
    own_skill_score_table = [100, 96, 90, 85, 60, 40, 15, 10, 5, 2, 1, 1]

    def get_dependent_score(self, diff, percentage):
        if diff <= eps:
            return 0.0
        min_diff = min(int(diff), 10)
        range_st = self.dependent_skill_score_table[min_diff]
        min_score = self.dependent_skill_score_table[min_diff]
        range_ed = self.dependent_skill_score_table[min_diff+1]
        range_dif = range_ed - range_st
        score = min_score + range_dif * (1.0 - (diff - min_diff))
        score = score*percentage/100.0
        score = score*self.dependent_percentage/100.0
        return score

    def get_own_difficulty_based_score(self, diff):
        if diff <= eps:
            return 0.0
        min_diff = min(int(diff), 10)
        # print(f'get_own_difficulty_based_score, diff: {diff}, min_diff: {min_diff}')
        range_ed = self.own_skill_score_table[min_diff]
        range_st = self.own_skill_score_table[min_diff+1]
        max_score = self.own_skill_score_table[min_diff]
        range_dif = range_ed - range_st
        score = max_score - range_dif * (diff - min_diff)
        score = score*self.own_skill_percentage/100.0
        return score

    def generate_score(self, dependent_category_diff, own_diff):
        dependent_len = len(dependent_category_diff)
        if dependent_len == 0:
            final_score = self.get_own_difficulty_based_score(own_diff)
            return {
                'score': final_score
            }
        avg_percentage = 100/dependent_len
        dependent_score = 0
        for dep_cat_diff in dependent_category_diff:
            cur_score = self.get_dependent_score(dep_cat_diff, avg_percentage)
            dependent_score += cur_score
        own_diff_based_score = self.get_own_difficulty_based_score(own_diff)
        final_score = dependent_score + own_diff_based_score
        return {
            'score': final_score
        }
