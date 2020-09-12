
class Skill:

    max_skill = 1000000

    skill_levels = [0, 500, 1000, 1300, 1600, 1900, 2200, 2500, 2750, 3000, 3500, max_skill]
    weekly_min_score = [1, 3, 5.82, 9.01, 16.01, 24.37, 33.87, 44.39, 55.83, 68.14, 81.24, 100]
    score_table = [0, 5, 15, 25, 40, 55, 75, 95, 125, 155, 200]
    color_codes = ['#868686', '#258326', '#2ca39b', '#392fc5', '#920192', '#e9840a', '#c26f0a', '#ff1414', '#ce0f0f', '#8b0000', '#400E04']

    skill_title = [
        'Level 00',
        'Level 01',
        'Level 02',
        'Level 03',
        'Level 04',
        'Level 05',
        'Level 06',
        'Level 07',
        'Level 08',
        'Level 09',
        'Level 10',
    ]

    score_per_level_dx = [
        [80, 100],
        [65, 79],
        [50, 64],
        [40, 49],
        [30, 39],
        [20, 29],
        [15, 19],
        [10, 14],
        [9, 9],
        [8, 8],
        [7, 7],
        [6, 6],
        [5, 5],
        [3, 4],
        [0, 2],
    ]

    def get_problem_relevent_score_from_level(self, depth):
        if depth < len(self.score_per_level_dx):
            return self.score_per_level_dx[depth]
        return [0, 1]

    def get_skill_title(self, skill):
        idx = 9
        while idx >= 0:
            if skill > self.skill_levels[idx]:
                return self.skill_title[idx+1]
            idx -= 1
        return self.skill_title[0]

    def get_skill_level_from_skill(self, skill):
        max_level = 0
        for level in range(0, 10):
            if skill >= self.skill_levels[level]:
                max_level = level

        range_st = self.skill_levels[max_level]
        range_ed = self.max_skill

        if max_level < 10:
            range_ed = self.skill_levels[max_level+1]

        dx = range_ed - range_st
        skill_ext = skill - range_st
        level = max_level + skill_ext/dx
        return level

    def generate_next_week_prediction(self, level):
        u = int(level)
        v = u + 1
        score_dx = self.weekly_min_score[v] - self.weekly_min_score[u]
        level_dx = level - u
        score = self.weekly_min_score[u] + score_dx*level_dx
        return score

    def get_problem_score(self, dif):
        dif = int(dif)
        return self.score_table[dif]

    def get_color_from_skill(self, skill):
        skill_level = int(self.get_skill_level_from_skill(skill))
        return self.color_codes[skill_level]

    def get_color_from_level(self, skill_level):
        return self.color_codes[skill_level-1]

    def get_color_from_skill_title(self, skill_title):
        if skill_title not in self.skill_title:
            return self.color_codes[0]
        for i in range(0, 11):
            if self.skill_title[i] == skill_title:
                return self.color_codes[i]
        return self.color_codes[0]
