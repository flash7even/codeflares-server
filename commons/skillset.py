
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
