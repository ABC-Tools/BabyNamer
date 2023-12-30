import json
import re
import glob
import gzip

from collections import OrderedDict
from typing import Dict, List

year_match = re.compile(r'yob(\d{4})\.txt$')
blank_line = re.compile(r'^\s*$')

output_format = 'gzip'
json_gzip_filename = '/Users/santan/gitspace/BabyNamer/app/data/name_year_trend.json.gzip'
json_filename = '/Users/santan/gitspace/BabyNamer/app/data/name_year_trend.json'


def load_single_file(file_path: str, result: Dict[str, List[Dict[str, str]]]):
    print('processing: {}'.format(file_path))

    m = year_match.search(file_path)
    if not m:
        raise ValueError('Invalid file: %s'.format(file_path))
    year = m.group(1)

    with open(file_path) as file:
        for line in file:
            if blank_line.search(line):
                continue

            line = line.rstrip()
            segments = line.split(',')
            if len(segments) != 3:
                print('Invalid line: %s'.format(line))
                continue

            name = segments[0]
            gender = segments[1]
            freq = segments[2]

            key = (name, gender)
            if key not in result:
                result[key] = OrderedDict()
            result[key][year] = freq


def loads_all():
    all_files = glob.glob('/Users/santan/Downloads/names/yob*.txt')
    print('Numer of files found: {}'.format(len(all_files)))

    output = {}
    for file in all_files:
        load_single_file(file, output)

    print("Number of names found: {}".format(len(output.keys())))

    ordered_output = []
    for name_gen, year_num in output.items():
        name, gender = name_gen
        ordered_output.append(
            {
                'name': name,
                'gender': gender,
                'trend': year_num
            }
        )

    return ordered_output


def convert_files():
    name_list = loads_all()

    if output_format == 'gzip':
        with gzip.open(json_gzip_filename, 'w') as fout:
            fout.write(
                json.dumps(sorted(name_list, key=lambda x: x['name']))
                    .encode('utf-8'))
    else:
        with open(json_filename, 'w') as fout:
            json.dump(sorted(name_list, key=lambda x: x['name']), fout)


def read_output_file():
    with gzip.open(json_gzip_filename, 'r') as fin:
        data = json.loads(fin.read().decode('utf-8'))

    print("Loaded number of names: {}".format(len(data)))

    output = {}
    for elem in data:
        name = elem['name']
        gender = elem['gender']
        trend = elem['trend']

        output[(name, gender)] = trend

    return output
