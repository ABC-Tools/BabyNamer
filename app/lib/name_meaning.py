import json
import logging
import os

from typing import Dict, Tuple, List, Any, Union
from .common import Gender, canonicalize_gender, canonicalize_name, get_app_root_dir
import app.lib.name_statistics as ns


class NameMeaning:

    def __init__(self):
        raw_input = NameMeaning.load_file()
        self.__name_meaning__ = NameMeaning.loaded_list_to_dict(raw_input)

    def get(self, raw_name: str, raw_gender: Union[str, Gender] = None) -> str:
        name = canonicalize_name(raw_name)
        gender = canonicalize_gender(raw_gender)

        if not gender:
            gender = ns.NAME_STATISTICS.guess_gender(name)

        return self.__name_meaning__[gender].get(name, '')

    @staticmethod
    def load_file() -> List[Dict[str, Any]]:
        """
        The file has one JSON object for each line.
        For each line, the JSON object looks like
        {
           'San': {
                'description': '...',
                'gender': 'boy'     <-- optional
           }
        }
        :return:
        """
        result = []
        input_filename = NameMeaning.get_source_file()
        with open(input_filename, 'r') as fp:
            for line in fp:
                line = line.strip()
                content_dict = json.loads(line)

                result.append(content_dict)

        return result

    @staticmethod
    def loaded_list_to_dict(name_list) -> Dict[Tuple[str, Gender], str]:
        """
        returns a dict with key of (name, gender), and with the value of meaning of the name
        """
        result = {
            Gender.BOY: {},
            Gender.GIRL: {}
        }
        for name_dict in name_list:
            # there is one JSON dictionary in each element
            raw_name = list(name_dict.keys())[0]
            val_dict = name_dict[raw_name]

            name = canonicalize_name(raw_name)
            gender = canonicalize_gender(val_dict.get('gender', ''))
            if not gender:
                gender = ns.NAME_STATISTICS.guess_gender(name)
            description = val_dict.get('description', '')

            result[gender][name] = description

        logging.debug('Name_meaning loaded {} boy names and {} girl names'.format(
            len(result[Gender.BOY]), len(result[Gender.GIRL])
        ))
        return result

    @staticmethod
    def get_source_file():
        return os.path.join(get_app_root_dir(), 'data', 'name_meaning_new.txt')


NAME_MEANING = NameMeaning()


