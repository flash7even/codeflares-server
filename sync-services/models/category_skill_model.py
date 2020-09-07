import argparse
import json

from .skillset import Skill


MAX_PROBLEM_SOLVED = 100


class CategorySkillGenerator:

    def __init__(self, group_table = None, group_bound = None):
        self.n = 0.40
        self.group_table = [0, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3]
        if group_table:
            self.group_table = group_table
        self.group_bound = [0, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10]
        if group_bound:
            self.group_bound = group_bound

    def get_score_for_latest_solved_problem(self, difficulty, solve_count_order, problem_factor):
        print(f'get_score_for_latest_solved_problem called, difficulty: {difficulty}, solve_count_order: {solve_count_order}')
        difficulty = int(difficulty)

        limit = self.group_bound[difficulty]
        group_len = self.group_table[difficulty]

        if solve_count_order > limit:
            group_order = int(limit/group_len)
            if limit%group_len != 0:
                group_order += 1
            group_order += (solve_count_order - limit)
        else:
            group_order = int(solve_count_order/group_len)
            if solve_count_order%group_len != 0:
                group_order += 1
        mty_factor = (1.0/group_order)**(self.n)
        score = Skill.score_table[difficulty] * mty_factor * float(problem_factor)
        # print(f'generated score: {score}')
        return score

    def generate_skill(self, solved_table, problem_factor):
        factor = {}
        x = 1.0
        skill = 0

        MAX_GROUP = 0
        for dif in range(1, 11):
            MAX_GROUP = max(MAX_GROUP, solved_table[dif])

        for a in range(1, MAX_GROUP+1):
            factor[a] = (x/a)**(self.n)

        for dif in range(1, 11):
            score = Skill.score_table[dif]
            solve_count = solved_table[dif]
            factor_dx = 1
            counted = 0
            gcount = self.group_table[dif]

            while solve_count > 0:
                take = min(solve_count, gcount)
                skill_diff = take*score*factor[factor_dx]*problem_factor
                skill += skill_diff
                solve_count -= take
                factor_dx += 1
                counted += take

                if counted >= self.group_bound[dif]:
                    gcount = 1

        if skill == 0:
            return {
                'skill': 0,
                'level': 0
            }

        max_level = 0
        for level in range(0, 10):
            if skill >= Skill.skill_levels[level]:
                max_level = level

        range_st = Skill.skill_levels[max_level]
        range_ed = Skill.max_skill

        if max_level < 10:
            range_ed = Skill.skill_levels[max_level+1]

        dx = range_ed - range_st
        skill_ext = skill - range_st
        level = max_level + skill_ext/dx

        return {
            'skill': skill,
            'level': level
        }


if __name__ == '__main__':

    score_data = [
        [0, 3, 1, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 3, 2, 1, 0, 0, 0, 0, 0, 0, 0],
        [0, 5, 2, 2, 1, 0, 0, 0, 0, 0, 0],
        [0, 4, 3, 2, 2, 1, 0, 0, 0, 0, 0],
        [0, 4, 4, 4, 4, 1, 0, 0, 0, 0, 0],
        [0, 4, 4, 3, 5, 4, 2, 0, 0, 0, 0],
        [0, 4, 4, 5, 5, 4, 3, 2, 0, 0, 0],
        [0, 3, 3, 4, 6, 3, 4, 4, 3, 0, 0],
        [0, 4, 4, 3, 4, 6, 5, 5, 4, 2, 0],
        [0, 3, 4, 3, 5, 3, 7, 8, 4, 5, 5],
    ]

    group_table = [0, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3]
    group_bound = [0, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10]

    skill_generator = CategorySkillGenerator(group_table,group_bound)

    for table in score_data:
        skill = skill_generator.generate_skill(table)
        print(skill)
