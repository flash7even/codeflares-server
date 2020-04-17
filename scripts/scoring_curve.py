import argparse
import logging
import os
import json
import time

dif_score = [1, 2.82, 5.19, 8, 11.18, 14.69, 18.52, 22.62, 27, 31.62]

MAX_STEP = 100

def plot_curve(n):
    res = {}
    x = 1.0

    res['factor'] = {}
    for a in range(1, MAX_STEP):
        res['factor'][a] = (x/a)**n

    print(json.dumps(res))

    for dif in range(1, 10):
        cur_score = dif_score[dif]
        res[dif] = {}
        step = 2
        res[dif][1] = cur_score
        while step <= MAX_STEP:
            a = step
            y = (x/a)**n
            res[dif][step] = cur_score * y
            step += 1
    print(json.dumps(res))


if __name__ == '__main__':
    print('START RUNNING CURVE PLOTTING SCRIPT\n')

    parser = argparse.ArgumentParser(description='Enroll an image or by a directory of images of a person')
    parser.add_argument('--n', help="Controls how flat the curve is at the top")
    args = parser.parse_args()

    n = float(args.n)
    plot_curve(n)
