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
        'problem_difficulty_org',
        'problem_significance',
        'oj_name',
        'source_link',
        'solved_count',
        'tried_count',
    ]
    data_list.append(header)


def make_table_rows(file_source):

    max_solved_value = 1525
    max_tried_value = 1550

    scale_top = 1.0
    scale_top_dx = 0.02
    top_dif = 3.25

    scale_below = 1.0
    scale_below_dx = 0.003295

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

            if int(mlist[0]) > max_solved_value:
                d['solved_count'] = mlist[0]
                d['tried_count'] = mlist[1]
                d['problem_difficulty'] = top_dif*scale_top
                d['problem_difficulty_org'] = (10.0 - 6.50*float(mlist[0])/float(max_solved_value))
                d['problem_significance'] = 8.25
                scale_top += scale_top_dx
            else:
                d['solved_count'] = mlist[0]
                d['tried_count'] = mlist[1]
                d['problem_difficulty'] = (10.0 - 6.50*float(mlist[0])/float(max_solved_value)) * scale_below
                d['problem_difficulty_org'] = (10.0 - 6.75*float(mlist[0])/float(max_solved_value))
                d['problem_significance'] = 9.5*float(mlist[1])/float(max_tried_value)
                scale_below -= scale_below_dx
                print(scale_below)

            d['problem_difficulty'] = "{:.2f}".format(d['problem_difficulty'])
            d['problem_significance'] = "{:.2f}".format(d['problem_significance'])

            data = [d['problem_name'], d['problem_id'], d['problem_difficulty'], d['problem_significance'],
                    d['oj_name'],d['source_link'], d['solved_count'], d['tried_count']]

            #print(data)
            data_list.append(data)


if __name__ == '__main__':
    file_source = 'Light OJ - DP - Sheet1.csv'
    make_table_header()
    make_table_rows(file_source)
    download_in_csv_format('light_oj_dp.csv', data_list)


