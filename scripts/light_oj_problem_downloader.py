import csv


def download_in_csv_format(file_name, data):
    with open(file_name, 'w+') as my_csv:
        csvWriter = csv.writer(my_csv, delimiter=',')
        csvWriter.writerows(data)


data_list = []


def make_table_header():
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
    data_list.append(header)


def make_table_rows(file_source):

    max_solved_value = 0
    max_tried_value = 0

    with open(file_source, mode='r') as csv_file:
        csv_reader = csv.DictReader(csv_file)

        for row in csv_reader:
            solved_tried = row["solved"].replace(" ", "")
            mlist = solved_tried.split("/")
            solved_val = int(mlist[0])
            tried_val = int(mlist[1])
            max_solved_value = max(max_solved_value, solved_val)
            max_tried_value = max(max_tried_value, tried_val)

        print('max_solved_value', max_solved_value)
        print('max_tried_value', max_tried_value)

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
            d['solved_count'] = mlist[0]
            d['tried_count'] = mlist[1]
            d['problem_difficulty'] = (10.0 - 6.75*float(mlist[0])/float(max_solved_value))
            d['problem_difficulty'] = "{:.2f}".format(d['problem_difficulty'])
            d['problem_significance'] = 9.5*float(mlist[1])/float(max_tried_value)
            d['problem_significance'] = "{:.2f}".format(d['problem_significance'])

            data = [d['problem_name'], d['problem_id'], d['problem_difficulty'], d['problem_significance'],
                    d['oj_name'],d['source_link'], d['solved_count'], d['tried_count']]

            print(data)
            data_list.append(data)


if __name__ == '__main__':
    file_source = 'Light OJ - DP - Sheet1.csv'
    make_table_header()
    make_table_rows(file_source)
    download_in_csv_format('light_oj_dp.csv', data_list)


