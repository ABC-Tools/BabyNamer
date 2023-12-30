
import json
import logging
import os

from typing import Dict, Tuple, List, Any
from app.lib.common import Gender, canonicalize_gender, canonicalize_name, get_app_root_dir
import app.lib.name_statistics as ns

ALL_RATINGS = [("A Good Name", "A Bad Name", 'overall_rating'),
               ("Masculine", "Feminine", 'gender_option'),
               ("Classic", "Modern", 'style_option'),
               ("Mature", "Youthful", 'age_option'),
               ("Formal", "Informal", 'formality_option'),
               ("Upper Class", "Common", 'class_option'),
               ("Urban", "Natural", 'environment_option'),
               ("Wholesome", "Devious", 'moral_option'),  # Devious is negative; use "Tactful"
               ("Strong", "Delicate", 'strength_option'),
               ("Refined", "Rough", 'texture_option'),
               ("Strange", "Boring", 'creativity_option'),  # use "Creative" and "Consistent"
               ("Simple", "Complex", 'complexity_option'),
               ("Serious", "Comedic", 'tone_option'),  # Comedic --> Charming
               ("Nerdy", "Unintellectual", 'intellectual_option')  # use Intellectual and Modest
               ]

RATING_DISTRIBUTION = {
    "boy": {
        "A Good Name": (0.7095883488672485, 0.054284520974145094),
        "Masculine": (0.8516815245926722, 0.03845062574854393),
        "Classic": (0.630654396955258, 0.052457795101303835),
        "Mature": (0.567208311919214, 0.054512310816690134),
        "Formal": (0.5878436236856359, 0.05377349318559044),
        "Upper Class": (0.5557353909407857, 0.05536344066890343),
        "Urban": (0.4335645409970402, 0.05745842050395597),
        "Wholesome": (0.6492459266873176, 0.05599049318087365),
        "Strong": (0.748571611128859, 0.05001480430129141),
        "Refined": (0.5994107760476723, 0.05602597219281701),
        "Strange": (0.657932048949204, 0.05161597432755281),
        "Simple": (0.5591581125942792, 0.05486902478496766),
        "Serious": (0.5917832289250339, 0.0548356636707774),
        "Nerdy": (0.6057190560193412, 0.05594803894183484),
    },
    "girl": {
        "A Good Name": (0.731890183328819, 0.04809467132134483),
        "Masculine": (0.10702889482353015, 0.03257073884564129),
        "Classic": (0.5978575729036324, 0.04897800255139655),
        "Mature": (0.4487827104109957, 0.05020089624131008),
        "Formal": (0.5857440449312562, 0.0492942112919231),
        "Upper Class": (0.5987515965475849, 0.050280000384560944),
        "Urban": (0.3562172680866805, 0.0509335128343213),
        "Wholesome": (0.6976071998383009, 0.04936526123825189),
        "Strong": (0.5322117720925625, 0.05125233340190662),
        "Refined": (0.7182022766661107, 0.04819943112862181),
        "Strange": (0.6571660581508821, 0.047317459374429306),
        "Simple": (0.5289386882722029, 0.04995100442544437),
        "Serious": (0.6011593623270693, 0.05052240978824469),
        "Nerdy": (0.59568979456679, 0.05126756643368472),
    }
}

DISPLAY_RATINGS = set(["Classic", "Formal", "Urban", "Strong", "Simple"])


class NameRating:

    def __init__(self):
        raw_input = NameRating.load_file()
        self.__name_rating__, self.__name_rating_raw__ = NameRating.loaded_list_to_dict(raw_input)

    def get(self, raw_name: str, raw_gender: str = None) -> str:
        name = canonicalize_name(raw_name)
        gender = canonicalize_gender(raw_gender)
        if not gender:
            gender = ns.NAME_STATISTICS.guess_gender(name)

        return self.__name_rating__.get((name, gender), {})

    def get_display_str(self, raw_name: str, raw_gender: str = None) -> str:
        name = canonicalize_name(raw_name)
        gender = canonicalize_gender(raw_gender)
        if not gender:
            gender = ns.NAME_STATISTICS.guess_gender(name)

        return [x for x in self.__name_rating_raw__.get((name, gender), [])
                if DISPLAY_RATINGS.intersection(set(x.keys())) ]

    @staticmethod
    def load_file() -> List[Dict[str, Any]]:
        """
        [{
            "name": "Liam",
            "rating": [
                {"A Good Name": "69%", "A Bad Name": "31%"},
                {"Masculine": "92%", "Feminine": "8%"},
                {"Classic": "46%", "Modern": "54%"},
                {"Mature": "36%", "Youthful": "64%"},
                {"Formal": "41%", "Informal": "59%"},
                {"Upper Class": "43%", "Common": "57%"},
                {"Urban": "40%", "Natural": "60%"},
                {"Wholesome": "66%", "Devious": "34%"},
                {"Strong": "67%", "Delicate": "33%"},
                {"Refined": "62%", "Rough": "38%"},
                {"Strange": "52%", "Boring": "48%"},
                {"Simple": "75%", "Complex": "25%"},
                {"Serious": "53%", "Comedic": "47%"},
                {"Nerdy": "53%", "Unintellectual": "47%"}
            ],
            "votes": "875",
            "gender": "boy"
         {
            "name": "Olivia",
            ...
         }
        ]
        """
        input_filename = NameRating.get_source_file()
        with open(input_filename, 'r') as fp:
            return json.load(fp)

    @staticmethod
    def loaded_list_to_dict(name_list) -> Dict[Tuple[str, Gender], str]:
        """
        returns a dict with key of (name, gender), and with the value of a dictionary like
        {
            "A Good Name": 0.69,
            "Masculine": 0.92,
            "Classic": 0.46,
            "Mature": 0.36,
            ...
        }
        """
        result = {}
        result_with_raw_ratings = {}
        boy_count = 0
        girl_count = 0
        for name_dict in name_list:
            name = canonicalize_name(name_dict['name'])
            gender = canonicalize_gender(name_dict['gender'])

            if gender == Gender.BOY:
                boy_count += 1
            else:
                girl_count += 1

            raw_ratings = name_dict['rating']
            parsed_ratings = {}
            for rating_type in ALL_RATINGS:
                rating_key = rating_type[0]
                parsed_ratings[rating_key] = NameRating.get_score(raw_ratings, rating_key)

            result[(name, gender)] = parsed_ratings
            result_with_raw_ratings[(name, gender)] = raw_ratings

        logging.debug('Name Rating: boy count: {}, girl count: {}'.format(boy_count, girl_count))

        return result, result_with_raw_ratings

    @staticmethod
    def get_score(rating_record: List[Dict[str, str]], score_name: str) -> float:
        masculine_record = next(x for x in rating_record if score_name in x)
        return NameRating.percentage_to_float(masculine_record[score_name])

    @staticmethod
    def get_source_file():
        return os.path.join(get_app_root_dir(), 'data', 'ratings.json')

    @staticmethod
    def percentage_to_float(x: str):
        return float(x.strip().strip('%')) / 100

    @staticmethod
    def float_to_percentage(x: float):
        return "{}%".format(round(x))


NAME_RATING = NameRating()

