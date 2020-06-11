
class Skill:

    max_skill = 1000000

    skill_levels = [0, 8, 20, 35, 70, 120, 200, 320, 470, 670, 920, max_skill]
    weekly_min_score = [1, 3, 5.82, 9.01, 16.01, 24.37, 33.87, 44.39, 55.83, 68.14, 81.24, 100]
    score_table = [0, 1, 2.82, 5.19, 8, 11.18, 14.69, 18.52, 22.62, 27, 31.62]

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
        'Level 10'
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

    def get_skill_title(self, skill):
        idx = 10
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
