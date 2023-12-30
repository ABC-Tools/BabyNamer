
import json
import os

from typing import Dict, Tuple, List, Any
from app.lib.common import Gender, canonicalize_gender, canonicalize_name, get_app_root_dir
import app.lib.name_statistics as ns


class OriginShortMeaning:

    def __init__(self):
        raw_input = OriginShortMeaning.load_file()
        self.__osm__ = OriginShortMeaning.loaded_list_to_dict(raw_input)

    def get(self, raw_name: str, raw_gender: str = None) -> str:
        name = canonicalize_name(raw_name)
        gender = canonicalize_gender(raw_gender)
        if not gender:
            gender = ns.NAME_STATISTICS.guess_gender(name)

        tmp_dict = self.__osm__.get((name, gender), {})
        origin = tmp_dict.get('origin', '')
        short_meaning = tmp_dict.get('short_meaning', '')
        return origin, short_meaning

    @staticmethod
    def load_file() -> List[Dict[str, Any]]:
        """
        The file has one JSON object for each line.
        For each line, the JSON object looks like
        [
            {"name": "liam", "gender": "Male", "origin": "Irish", "short_meaning": "Desired Helmet/Protector"},
            {"name": "noah", "gender": "Neutral", ...}
            ...
        ]
        :return:
        """
        input_filename = OriginShortMeaning.get_source_file()
        with open(input_filename, 'r') as fp:
            return json.load(fp)

    @staticmethod
    def loaded_list_to_dict(name_list) -> Dict[Tuple[str, Gender], str]:
        """
        returns a dict with key of (name, gender), and with the origin and the short meaning of the name
        """
        result = {}
        for name_dict in name_list:
            name = canonicalize_name(name_dict['name'])
            origin = name_dict['origin']
            short_meaning = name_dict['short_meaning']

            raw_gender = name_dict['gender']
            if raw_gender.lower() in ['neutral']:
                result[(name, Gender.BOY)] = {'origin': origin, 'short_meaning': short_meaning}
                result[(name, Gender.GIRL)] = {'origin': origin, 'short_meaning': short_meaning}
            else:
                gender = canonicalize_gender(raw_gender)
                result[(name, gender)] = {'origin': origin, 'short_meaning': short_meaning}

        return result

    @staticmethod
    def get_source_file():
        return os.path.join(get_app_root_dir(), 'data', 'origin_and_short_meaning.json')


ORIGIN_SHORT_MEANING = OriginShortMeaning()
