import json
import os
import logging

from typing import Dict, Tuple, List, Any
from .common import Gender, canonicalize_gender, canonicalize_name, get_app_root_dir
import app.lib.name_statistics as ns


class SimilarNames:
    def __init__(self):
        self.__similar_names__ = SimilarNames.load_file()

    def get(self, raw_name: str, raw_gender: str = None) -> List[str]:
        name = canonicalize_name(raw_name)
        gender = canonicalize_gender(raw_gender)
        if gender:
            gender = ns.NAME_STATISTICS.guess_gender(name)

        return self.__similar_names__[gender].get(name, [])

    @staticmethod
    def load_file():
        """
        The input has the format of
        {
            'San': ["wynnie", "miller", "everley", ...],
            ...
        {
        :return:
        """
        json_filename = SimilarNames.get_source_file()
        with open(json_filename, 'r') as fin:
            data = json.load(fin)

        output = {
            Gender.BOY: data[str(Gender.BOY)],
            Gender.GIRL: data[str(Gender.GIRL)]
        }

        logging.info("similar names: loaded number of boy names: {} and number of girl names: {}".format(
            len(output[Gender.BOY]), len(output[Gender.GIRL])))

        return output

    @staticmethod
    def get_source_file():
        return os.path.join(get_app_root_dir(), 'data', 'similar_names_from_embedding.json')


SIMILAR_NAMES = SimilarNames()
