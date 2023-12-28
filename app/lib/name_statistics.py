import gzip
import json
import logging
import os

from typing import Dict
from .common import Gender, canonicalize_gender, canonicalize_name, get_app_root_dir


class YearTrend:

    def __init__(self):
        self.__freq__ = YearTrend.load_file()

    def get(self, raw_name: str, raw_gender: str = None) -> Dict[str, str]:
        """
        return a dict with year as key and with frequency as value
        """
        name = canonicalize_name(raw_name)
        gender = canonicalize_gender(raw_gender)
        if gender:
            result = self.__freq__.get((name, gender), {})
            if not result:
                result = self.__freq__.get((name, None), {})
            return result

        # try different genders
        result = self.__freq__.get((name, None), {})
        if not result:
            result = self.__freq__.get((name, Gender.GIRL), {})
        if not result:
            result = self.__freq__.get((name, Gender.BOY), {})
        return result

    def get_raw(self):
        return self.__freq__.copy()

    @staticmethod
    def load_file():
        """
        The input has the format of
        [
            {
                'name': 'San'',
                'gender': '',
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
        json_gzip_filename = YearTrend.get_source_file()
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
        return os.path.join(get_app_root_dir(), 'static', 'name_year_trend.json.gzip')


YEAR_TREND = YearTrend()
