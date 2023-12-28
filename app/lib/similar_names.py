import json
import os
import logging

from typing import Dict, Tuple, List, Any
from .common import Gender, canonicalize_gender, canonicalize_name, get_app_root_dir


class SimilarNames:
    def __init__(self):
        self.__similar_names__ = SimilarNames.load_file()

    def get(self, raw_name: str, raw_gender: str = None) -> List[str]:
        name = canonicalize_name(raw_name)
        gender = canonicalize_gender(raw_gender)
        if gender:
            result = self.__similar_names__.get((name, gender), [])
            if not result:
                result = self.__similar_names__.get((name, None), [])
            return result

        # try different genders
        result = self.__similar_names__.get((name, None), {})
        if not result:
            result = self.__similar_names__.get((name, Gender.GIRL), [])
        if not result:
            result = self.__similar_names__.get((name, Gender.BOY), [])
        return result

    @staticmethod
    def load_file():
        """
        The input has the format of
        [
            {
                'name': 'San'',
                'gender': 'boy',  <- optional
                'similar_names': ["wynnie", "miller", "everley", ...]
            },
            ...
        ]
        :return:
        """
        json_filename = SimilarNames.get_source_file()
        with open(json_filename, 'r') as fin:
            data = json.load(fin)

        logging.info("Loaded number of names: {}".format(len(data)))

        output = {}
        for elem in data:
            name = canonicalize_name(elem['name'])
            gender = canonicalize_gender(elem.get('gender', ''))
            similar_names = elem['similar_names']

            output[(name, gender)] = similar_names

        return output

    @staticmethod
    def get_source_file():
        return os.path.join(get_app_root_dir(), 'data', 'similar_names.json')


SIMILAR_NAMES = SimilarNames()
