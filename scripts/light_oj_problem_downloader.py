import csv

header = [
    'problem_name',
    'problem_id',
    'problem_difficulty',
    'problem_significance',
    'oj_name',
    'source_link',
    'solved_count',
    'tried_count',
]


def download_in_csv_format(file_name, data):
    with open(file_name, 'w+') as my_csv:
        csvWriter = csv.writer(my_csv, delimiter=',')
        csvWriter.writerows(data)


def make_table_rows(file_source, file_dest, min_diff, max_diff):
    data_list = []
    data_list.append(header)
    problem_count = 0

    with open(file_source, mode='r') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        for row in csv_reader:
            problem_count += 1

    scale = (max_diff - min_diff)/problem_count
    cur_diff = min_diff
    json_list = []

    with open(file_source, mode='r') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        for row in csv_reader:
            d = {
                'problem_name': row["problem_name"],
                'problem_id': row["problem_id"],
                'oj_name': 'lightoj',
                'source_link': 'http://lightoj.com/volume_showproblem.php?problem=' + row["problem_id"],
            }
            solved_tried = row["solved"].replace(" ", "")
            mlist = solved_tried.split("/")
            d['solved_count'] = int(mlist[0])
            d['tried_count'] = mlist[1]
            json_list.append(d)

    json_list = sorted(json_list, key=lambda i: i['solved_count'])
    json_list.reverse()

    for d in json_list:
        d['problem_difficulty'] = cur_diff
        d['problem_significance'] = (10.0 - cur_diff)
        d['problem_difficulty'] = "{:.2f}".format(d['problem_difficulty'])
        d['problem_significance'] = "{:.2f}".format(d['problem_significance'])

        data = [d['problem_name'], d['problem_id'], d['problem_difficulty'], d['problem_significance'],
                d['oj_name'],d['source_link'], d['solved_count'], d['tried_count']]
        data_list.append(data)
        cur_diff += scale

    download_in_csv_format(file_dest, data_list)


if __name__ == '__main__':

    source_file_list = ['lightoj-basic-math - Sheet1.csv', 'light-oj-beginners - Sheet1.csv', 'light-oj-bfs-dfs - Sheet1.csv', 'lightoj-binary-search - Sheet1.csv',
                 'lightoj-bpm - Sheet1.csv', 'lightoj-counting - Sheet1.csv', 'lightoj-dijkstra - Sheet1.csv', 'lightoj-dp - Sheet1.csv'
                 , 'lightoj-greedy - Sheet1.csv', 'lightoj-matrix-exponentiation - Sheet1.csv', 'lightoj-maxflow - Sheet1.csv', 'lightoj-mcmf - Sheet1.csv',
                 'lightoj-mst - Sheet1.csv', 'lightoj-number-theory - Sheet1.csv', 'lightoj-segment-tree - Sheet1.csv', 'lightoj-trie - Sheet1.csv']

    min_difficulty = [2.5, 1.5, 3.00, 2.75, 5.0, 3.0, 4.65, 3.25, 2.25, 4.5, 4.60, 5.50, 4.15, 2.50, 4.50, 3.50]
    max_difficulty = [4.5, 3.5, 6.25, 6.25, 8.5, 7.75, 7.85, 9.00, 6.5, 8.0, 9.00, 9.00, 5.75, 8.55, 8.50, 6.55]

    file_count = len(source_file_list)

    for idx in range(0, file_count):
        file_name = source_file_list[idx]
        file_name = file_name.replace(" ", "")
        words = file_name.split("-")
        words = words[:-1]
        file_dest = "_".join(words)
        file_dest += ".csv"
        src = "../dataset-row/lightoj-row/" + source_file_list[idx]
        dst = "../dataset-row/lightoj/" + file_dest
        make_table_rows(src, dst, min_difficulty[idx], max_difficulty[idx])



