
import json
import os

from typing import Dict, Tuple, List, Any, Union
from app.lib.common import Gender, canonicalize_gender, canonicalize_name, get_app_root_dir
import app.lib.name_statistics as ns


class OriginMeaning:

    def __init__(self):
        self.__osm__ = OriginMeaning.load_file()

    def get(self, raw_name: str, raw_gender: Union[str, Gender] = None) -> Tuple[str, str, str]:
        name = canonicalize_name(raw_name)
        gender = canonicalize_gender(raw_gender)
        if not gender:
            gender = ns.NAME_STATISTICS.guess_gender(name)

        tmp_dict = self.__osm__[gender].get(name, {})
        origin = tmp_dict.get('origin', '')
        short_meaning = tmp_dict.get('short_meaning', '')
        meaning = tmp_dict.get('meaning', '')
        return origin, short_meaning, meaning

    @staticmethod
    def load_file() -> List[Dict[str, Any]]:
        result = {}

        input_filename = OriginMeaning.get_source_file(Gender.BOY)
        with open(input_filename, 'r') as fp:
            result[Gender.BOY] = json.load(fp)

        input_filename = OriginMeaning.get_source_file(Gender.GIRL)
        with open(input_filename, 'r') as fp:
            result[Gender.GIRL] = json.load(fp)

        return result

    @staticmethod
    def get_source_file(gender: Gender):
        return os.path.join(get_app_root_dir(), 'data', 'origin_meaning_{gender}.json'.format(gender=str(gender)))


ORIGIN_MEANING = OriginMeaning()
