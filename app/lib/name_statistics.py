import gzip
import json
import logging
import os

from typing import Dict
from .common import Gender, canonicalize_gender, canonicalize_name, get_app_root_dir


class NameStatistics:

    def __init__(self):
        self.__freq__ = NameStatistics.load_file()
        self._name_freq_3_year, self._name_ordered_list_3_year = \
            NameStatistics.create_name_freq_rank(self.__freq__, 2020, 2022)

    def guess_gender(self, name: str):
        boy_count = self._name_freq_3_year[Gender.BOY].get(name, {}).get('freq', 0)
        girl_count = self._name_freq_3_year[Gender.GIRL].get(name, {}).get('freq', 0)

        return Gender.GIRL if girl_count >= boy_count else Gender.BOY

    def get_frequency_and_rank(self, raw_name: str, raw_gender: str = None):
        name = canonicalize_name(raw_name)
        gender = canonicalize_gender(raw_gender)
        if not gender:
            gender = self.guess_gender(name)

        return self._name_freq_3_year[gender].get(name, {}).get('freq', 0), \
               self._name_freq_3_year[gender].get(name, {}).get('rank', 10000)

    def get_popular_names(self, raw_gender: str, count=30):
        gender = canonicalize_gender(raw_gender)
        if not gender:
            raise ValueError('Wrong gender: {}'.format(raw_gender))

        count = min(count, len(self._name_ordered_list_3_year[gender]))
        top_records = self._name_ordered_list_3_year[gender][0:count]
        return [x['name'] for x in top_records]

    def get_percentile(self, percentile, gender: Gender):
        total = 0
        for record in self._name_ordered_list_3_year[gender]:
            total += record['freq']

        names = []
        count = 0
        for record in self._name_ordered_list_3_year[gender]:
            count += record['freq']
            names.append(record['name'])
            if 1.0 * count / total >= percentile:
                break

        logging.debug('{} of names has a count of {} out of {}: {}'.format(len(names), count, total, names))
        return names

    def get_yearly_trend(self, raw_name: str, raw_gender: str = None) -> Dict[str, str]:
        """
        return a dict with year as key and with frequency as value
        """
        name = canonicalize_name(raw_name)
        gender = canonicalize_gender(raw_gender)
        if not gender:
            gender = self.guess_gender(name)

        result = self.__freq__.get((name, gender), {})
        return result

    def get_raw_yearly_trend(self):
        return self.__freq__.copy()

    @staticmethod
    def create_name_freq_rank(yearly_trend_dict, start_year, end_year):
        """
        :param yearly_trend_dict:
        :param start_year:
        :param end_year: inclusive
        :return:
        a frequency dictionary, like
        {
            Gender.GIRL: {
                'Ally': {
                    'freq': 80
                    'rank': 1
                }
                ...
            },
            Gender.BOY: {
                'George": {
                    'freq': 40,
                    'rank': 1
                }
                ...
            },
        }
        and a name list ordered by frequency, like
        {
            Gender.GIRL: [
                {
                    'name': 'Ally'
                    'freq': 80
                }
                ...
            ],
            Gender.BOY: {
                {
                    'name': 'George'
                    'freq': 40
                }
                ...
            },
        }
        """
        raw_freq_dict = {
            Gender.GIRL: {},
            Gender.BOY: {}
        }
        for name_gender, yearly_trend in yearly_trend_dict.items():
            name, gender = name_gender
            assert isinstance(gender, Gender), "wrong gender type: {}".format(gender)

            raw_freq_dict[gender][name] = {'freq': 0}
            for year in range(start_year, end_year + 1):
                raw_freq_dict[gender][name]['freq'] += int(yearly_trend.get(str(year), '0'))

        # remove names with 0 frequency
        freq_dict = {
            Gender.GIRL: {},
            Gender.BOY: {}
        }
        count = 0
        for gender in [Gender.GIRL, Gender.BOY]:
            for name, record in raw_freq_dict[gender].items():
                if record['freq'] > 0:
                    freq_dict[gender][name] = record
                    count += 1
        logging.debug('{} records has non-zero frequency'.format(count))

        raw_freq_list = {
            Gender.GIRL: [],
            Gender.BOY: []
        }
        for gender in [Gender.GIRL, Gender.BOY]:
            for name, record in freq_dict[gender].items():
                raw_freq_list[gender].append({'name': name, 'freq': record['freq']})
                # logging.debug('name {} frequency {}'.format(name, record['freq']))

        freq_list = {
            Gender.GIRL: sorted(raw_freq_list[Gender.GIRL], key=lambda x: x['freq'], reverse=True),
            Gender.BOY: sorted(raw_freq_list[Gender.BOY], key=lambda x: x['freq'], reverse=True)
        }

        # write rank  into freq_dict
        for gender in [Gender.GIRL, Gender.BOY]:
            rank = 1
            for record in freq_list[Gender.GIRL]:
                name = record['name']
                freq_dict[gender][name] = rank
                rank += 1

        return freq_dict, freq_list

    @staticmethod
    def load_file():
        """
        The input has the format of
        [
            {
                'name': 'San'',
                'gender': 'M',
                'trend': {
                    '2023': '23'
                    '2022': '21'
                    ...
                }
            },
            ...
        ]
        :return:
        """
        json_gzip_filename = NameStatistics.get_source_file()
        with gzip.open(json_gzip_filename, 'r') as fin:
            data = json.loads(fin.read().decode('utf-8'))

        logging.info("Loaded number of names: {}".format(len(data)))

        output = {}
        for elem in data:
            name = canonicalize_name(elem['name'])
            gender = canonicalize_gender(elem['gender'])
            trend = elem['trend']

            output[(name, gender)] = trend

        return output

    @staticmethod
    def get_source_file():
        return os.path.join(get_app_root_dir(), 'data', 'name_year_trend.json.gzip')


NAME_STATISTICS = NameStatistics()
