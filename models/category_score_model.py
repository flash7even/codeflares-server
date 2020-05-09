import argparse
import json
import random

from commons.skillset import Skill


class CategoryScoreGenerator:

    def __init__(self):
        self.n = 0.40

    def generate_score(self):
        return {
            'score': random.randint(50, 100)
        }


if __name__ == '__main__':
    category_score = CategoryScoreGenerator()
    score = category_score.generate_score()

