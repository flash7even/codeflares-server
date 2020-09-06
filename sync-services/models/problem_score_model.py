import argparse
import json
import math

from .skillset import Skill

eps = 0.0000001


class ProblemScoreGenerator:

    def calculate(self, problem_diff, category_level):
        up = category_level + 1
        down = category_level - 0.5
        level_dx = []
        level_dx.append([category_level+eps, up])
        level_dx.append([down, category_level])

        while up+1.5 <= 10 or down-1 >= 0:
            if up+1.5 <= 10:
                level_dx.append([up+eps, up+1.5])
                up += 1.5
            elif up < 10:
                level_dx.append([up + eps, 10])
            if down-1 >= 0:
                level_dx.append([down-1, down-eps])
                down -= 1

        if down > 0.0:
            level_dx.append([0, down-eps])

        level_idx = 0
        for idx, level in enumerate(level_dx):
            if problem_diff >= level[0] and problem_diff <= level[1]:
                level_idx = idx
                break

        score_range = Skill.score_per_level_dx[level_idx]
        score_dif = score_range[1] - score_range[0]
        level_range_val = level_dx[level_idx][1] - level_dx[level_idx][0]
        if problem_diff > category_level:
            dx_end = level_dx[level_idx][1] - problem_diff
            score_add = score_dif * dx_end / level_range_val
            score = score_range[0] + score_add
            score = min(score, 100)
            score = max(score, 0)
            return score
        else:
            dx_end = problem_diff - level_dx[level_idx][0]
            score_add = score_dif * dx_end / level_range_val
            score = score_range[0] + score_add
            score = min(score, 100)
            score = max(score, 0)
            return score

    def generate_score(self, problem_diff, category_level_list, user_skill_level):
        category_len = len(category_level_list)
        if category_len == 0:
            score = (10.0 - user_skill_level)*100.0/10.0
            return {'score': score}
        score_sum = 0
        for category_level in category_level_list:
            cur_score = self.calculate(problem_diff, category_level)
            score_sum += cur_score
        score = score_sum/category_len
        return {'score': score}


if __name__ == '__main__':
    score_generator = ProblemScoreGenerator()
    category_skill = [7, 5, 6]

    print('CATEGORY SKILL: ', category_skill)

    problem_skill = 0.3
    while problem_skill < 10.0:
        score = score_generator.generate_score(problem_skill, category_skill)
        a = "{:.1f}".format(problem_skill)
        b = "{:.1f}".format(score['score'])
        print(a, " = ",b)
        problem_skill += 0.3
