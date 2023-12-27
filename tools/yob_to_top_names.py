"""
$ . venv/bin/acitivate
$ sudo python -m tools.yob_to_top_names
"""
import json
import re

from app.lib.common import fprint
from typing import Dict, List

blank_line = re.compile(r'^\s*$')


def load_single_file(file_path: str, result: Dict[str, List[Dict[str, str]]]):
    print('processing: {}'.format(file_path))

    with open(file_path) as file:
        for line in file:
            if blank_line.search(line):
                continue

            line = line.rstrip()
            segments = line.split(',')
            if len(segments) != 3:
                fprint('Invalid line: %s in file {}'.format(line, file_path))
                continue

            name = segments[0]
            gender = segments[1]
            freq = segments[2]

            key = (name, gender)
            if key not in result:
                result[key] = 0
            result[key] += int(freq)


def load_related_files(write_file=True):
    start_year = 2022
    end_year = 2022  # inclusive

    all_files = []
    file_pattern = '/Users/santan/Downloads/names/yob{year}.txt'
    for year in range(start_year, end_year + 1):
        all_files.append(file_pattern.format(year=year))

    result = {}
    for file_path in all_files:
        load_single_file(file_path, result)

    if start_year == end_year:
        filename = 'top_names_{start_year}.json'.format(start_year=start_year)
    else:
        filename = 'top_names_{start_year}_to_{end_year}.json'.format(start_year=start_year, end_year=end_year)
    output_file = '/Users/santan/gitspace/BabyNamer/app/data/{filename}'.format(filename=filename)

    # convert result dictionary into a list
    ordered_output = []
    for name_gen, freq in result.items():
        name, gender = name_gen
        ordered_output.append(
            {
                'name': name,
                'gender': gender,
                'frequency': freq
            }
        )
    fprint('{} names were added'.format(len(ordered_output)))

    sorted_result = sorted(ordered_output, key=lambda x: x['frequency'], reverse=True)
    if write_file:
        with open(output_file, 'w') as fout:
            fprint('Writing file: {}'.format(output_file))
            json.dump(sorted_result, fout)


if __name__ == "__main__":
    load_related_files(write_file=False)
