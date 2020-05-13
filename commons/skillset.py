
class Skill:

    max_skill = 2000

    skill_levels = [0, 10, 20, 45, 85, 130, 175, 220, 300, 450, 750, max_skill]

    skill_title = [
        'Zero',
        'Newbie',
        'Pupil',
        'Specialist',
        'Expert',
        'Candidate Master',
        'Master',
        'International Master',
        'Grandmaster',
        'International Grandmaster',
        'Legendary Grandmaster	'
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
