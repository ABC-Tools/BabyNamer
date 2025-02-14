import json
import logging
import os
import time

import scipy.stats as stats

from typing import Dict, Tuple, List, Any, Union
from app.lib.common import Gender, canonicalize_gender, canonicalize_name, get_app_root_dir, \
    float_to_percentage, percentage_to_float
import app.lib.name_statistics as ns

ALL_RATINGS = [
    # internal option 1, internal option 2, URL parameter name, external option 1, external option 2
    ("A Good Name", "A Bad Name", 'overall_option', "Good", "Bad"),
    ("Masculine", "Feminine", 'gender_option', "Masculine", "Feminine"),
    ("Classic", "Modern", 'style_option', "Classic", "Modern"),
    ("Mature", "Youthful", 'maturity_option', "Mature", "Youthful"),
    ("Formal", "Informal", 'formality_option', "Formal", "Casual"),
    ("Upper Class", "Common", 'class_option', "Noble", "Grassroots "),
    ("Urban", "Natural", 'environment_option', "Urban", "Natural"),
    ("Wholesome", "Devious", 'moral_option', "Wholesome", "Tactful"),
    ("Strong", "Delicate", 'strength_option', "Strong", "Delicate"),
    ("Refined", "Rough", 'texture_option', "Refined", "Rough"),
    ("Strange", "Boring", 'creativity_option', "Creative", "Practical"),
    ("Simple", "Complex", 'complexity_option', "Simple", "Complex"),
    ("Serious", "Comedic", 'tone_option', "Serious", "Cute"),
    ("Nerdy", "Unintellectual", 'intellectual_option', "Intellectual", "Modest")
]

DISPLAY_RATINGS = {"style_option", "maturity_option", "formality_option", "class_option",
                   "environment_option", "moral_option", "strength_option", "texture_option",
                   "creativity_option", "complexity_option", "tone_option", "intellectual_option"}

RATING_DISTRIBUTION = {
    Gender.BOY: {
        # mean, std dev
        "Good": (0.7095883488672485, 0.054284520974145094),
        "Masculine": (0.8516815245926722, 0.03845062574854393),
        "Classic": (0.630654396955258, 0.052457795101303835),
        "Mature": (0.567208311919214, 0.054512310816690134),
        "Formal": (0.5878436236856359, 0.05377349318559044),
        "Noble": (0.5557353909407857, 0.05536344066890343),
        "Urban": (0.4335645409970402, 0.05745842050395597),
        "Wholesome": (0.6492459266873176, 0.05599049318087365),
        "Strong": (0.748571611128859, 0.05001480430129141),
        "Refined": (0.5994107760476723, 0.05602597219281701),
        "Creative": (0.657932048949204, 0.05161597432755281),
        "Simple": (0.5591581125942792, 0.05486902478496766),
        "Serious": (0.5917832289250339, 0.0548356636707774),
        "Intellectual": (0.6057190560193412, 0.05594803894183484),
    },
    Gender.GIRL: {
        "Good": (0.731890183328819, 0.04809467132134483),
        "Masculine": (0.10702889482353015, 0.03257073884564129),
        "Classic": (0.5978575729036324, 0.04897800255139655),
        "Mature": (0.4487827104109957, 0.05020089624131008),
        "Formal": (0.5857440449312562, 0.0492942112919231),
        "Noble": (0.5987515965475849, 0.050280000384560944),
        "Urban": (0.3562172680866805, 0.0509335128343213),
        "Wholesome": (0.6976071998383009, 0.04936526123825189),
        "Strong": (0.5322117720925625, 0.05125233340190662),
        "Refined": (0.7182022766661107, 0.04819943112862181),
        "Creative": (0.6571660581508821, 0.047317459374429306),
        "Simple": (0.5289386882722029, 0.04995100442544437),
        "Serious": (0.6011593623270693, 0.05052240978824469),
        "Intellectual": (0.59568979456679, 0.05126756643368472),
    }
}


class NameRating:

    def __init__(self):
        raw_input = NameRating.load_file()
        self.__name_rating__ = NameRating.loaded_list_to_dict(raw_input)
        self._names = {
            Gender.BOY: [name for name in self.__name_rating__[Gender.BOY].keys()],
            Gender.GIRL: [name for name in self.__name_rating__[Gender.GIRL].keys()]
        }

    def get_feature_scores(self, raw_name: str, raw_gender: Union[str, Gender]) \
            -> Dict[str, Dict[str, Union[List[str], int]]]:
        name = canonicalize_name(raw_name)
        gender = canonicalize_gender(raw_gender)
        if not gender:
            gender = ns.NAME_STATISTICS.guess_gender(name)

        if name not in self.__name_rating__[gender]:
            return {}

        result = {}
        for types in ALL_RATINGS:
            url_param = types[2]
            ext_opt1 = types[3]
            ext_opt2 = types[4]
            if url_param not in DISPLAY_RATINGS:
                continue

            zscore = self._get_zscore(gender, name, url_param, ext_opt1, ext_opt2, ext_opt1)
            percentile_float = stats.norm.sf(abs(zscore))
            percentile_float = percentile_float if zscore > 0 else 1 - percentile_float
            score = round(percentile_float * 10)

            result[url_param] = {
                'characteristics': [ext_opt1, ext_opt2],
                'score': score
            }
        return result

    def get_feature_percentiles(self, raw_name: str, raw_gender: Union[str, Gender]) -> Dict:
        name = canonicalize_name(raw_name)
        gender = canonicalize_gender(raw_gender)
        if not gender:
            gender = ns.NAME_STATISTICS.guess_gender(name)

        if name not in self.__name_rating__[gender]:
            return {}

        result = {}
        rating_dict = self.__name_rating__[gender][name]
        for types in ALL_RATINGS:
            url_param = types[2]
            ext_opt1 = types[3]
            ext_opt2 = types[4]

            score = rating_dict[ext_opt1]
            zscore = self._get_zscore(gender, name, url_param, ext_opt1, ext_opt2, ext_opt1)
            percentile_float = stats.norm.sf(abs(zscore))
            percentile_str = float_to_percentage(percentile_float, min_val=1)

            result[types[2]] = {
                types[3]: (float_to_percentage(score), 'top' if zscore > 0 else 'bottom',
                           percentile_str, zscore, percentile_float),
                types[4]: (float_to_percentage(1 - score), 'bottom' if zscore > 0 else 'top',
                           percentile_str, -zscore, percentile_float)
            }
        return result

    def suggest(self, raw_target_gender: Union[str, Gender], options: Dict[str, str], count=20) \
            -> Dict[str, float]:
        start_ts = time.time()
        suggest_name_scores = self._suggest1(raw_target_gender, options, count=count)
        logging.debug('time spent for suggesting names: {} seconds'.format(time.time() - start_ts))

        return suggest_name_scores

    def create_suggest_reason(self, raw_target_gender: str, names: List[str], options: Dict[str, str]) \
            -> Dict[str, str]:
        target_gender = canonicalize_gender(raw_target_gender)
        if not target_gender:
            raise ValueError('Invalid target gender: {}'.format(raw_target_gender))

        name_reasons = {name: {'pros': [], 'cons': []} for name in names}

        for url_param, choice in options.items():
            opt1, opt2 = NameRating.get_options_by_url_param(url_param)
            if not opt1 or not opt2:
                logging.warning('Unexpected URL param for rating choice: {}; skip'.format(url_param))
                continue

            choice = options.get(url_param, "").strip()
            if not choice or choice not in [opt1, opt2]:
                logging.warning('Unexpected choice: "{}", allowed values are "{}" and "{}"; skip'.format(
                    choice if choice else '', opt1, opt2))
                continue

            for name in names:
                percentile = self._get_percentile(target_gender, name, url_param, opt1, opt2, choice)
                percentile_str = float_to_percentage(percentile, min_val=1)

                if percentile < 0.4:
                    name_reasons[name]['pros'].append(
                        'the top {percentile} {choice} names'.format(
                            percentile=percentile_str, choice=choice
                        )
                    )
                elif percentile > 0.6:
                    name_reasons[name]['cons'].append(
                        '{choice}'.format(choice=choice)
                    )

        name_reason_sentences = {name: '' for name in names}
        for name, pros_cons in name_reasons.items():
            pros = pros_cons['pros']
            # cons = pros_cons['cons']

            if pros:
                name_reason_sentences[name] = 'We recommend this name because it is considered as {}.'\
                    .format(', '.join(pros))
                """
                if cons:
                    name_reason_sentences[name] = \
                        '{original} However, the name is usually considered as not {cons}.'. \
                            format(original=name_reason_sentences[name], cons=', '.join(cons))
                """

        return name_reason_sentences

    def _suggest1(self, raw_target_gender: str, options: Dict[str, str], count=20, cap_zscore=2.0) \
            -> Dict[str, float]:
        target_gender = canonicalize_gender(raw_target_gender)
        if not target_gender:
            raise ValueError('Invalid target gender: {}'.format(raw_target_gender))

        # score all top names
        available_names = set(self._names[target_gender])
        top_names = set(ns.NAME_STATISTICS.get_popular_names(target_gender, count=5000))
        top_available_names = available_names.intersection(top_names)
        logging.debug('# of Top available names for suggest is {}'.format(len(top_available_names)))
        name_score_dict = {x: 0.0 for x in top_available_names}

        for url_param, choice in options.items():
            opt1, opt2 = NameRating.get_options_by_url_param(url_param)
            if not opt1 or not opt2:
                logging.warning('Unexpected URL param for rating choice: {}; skip'.format(url_param))
                continue

            choice = options.get(url_param, "").strip()
            if not choice or choice not in [opt1, opt2]:
                logging.warning('Unexpected choice: "{}", allowed values are "{}" and "{}"; skip'.format(
                    choice if choice else '', opt1, opt2))
                continue

            for name in name_score_dict.keys():
                percentile = self._get_percentile(target_gender, name, url_param, opt1, opt2, choice)
                name_score_dict[name] += 1 - percentile

        num_choices = len(options)
        name_score_list = [(name, score / num_choices) for name, score in name_score_dict.items()
                           if score > 0.5 * num_choices]
        name_score_list = sorted(name_score_list, key=lambda x: x[1], reverse=True)

        count = min(count, len(name_score_list))
        result_dict = {name_score[0]: name_score[1] for name_score in name_score_list[0:count]}

        return result_dict

    def stats(self, gender: Gender):
        count = {
            "A Good Name": 0,
            "Masculine": 0,
            "Classic": 0,
            "Mature": 0,
            "Formal": 0,
            "Noble": 0,
            "Urban": 0,
            "Wholesome": 0,
            "Strong": 0,
            "Refined": 0,
            "Creative": 0,
            "Simple": 0,
            "Serious": 0,
            "Intellectual": 0,
        }
        for types in ALL_RATINGS:
            for name in self._names[gender]:
                score = self.__name_rating__[gender][name][types[3]]
                if score >= 0.5:
                    count[types[3]] += 1

        total = len(self._names[gender])
        percentage = {key: "{}%".format(round(100.0 * val / total)) for key, val in count.items()}
        logging.info('Total: {}, count of names with >=50%: {}, percentage: {}'.format(
            total, count, percentage
        ))

    def _get_percentile(self, gender: Union[Gender, str], name: str,
                        url_param: str, ext_option1: str, ext_option2: str,
                        option_choice: str) -> float:
        gender = canonicalize_gender(gender)
        zscore = self._get_zscore(gender, name, url_param, ext_option1, ext_option2, option_choice)
        percentile = stats.norm.sf(abs(zscore))
        return percentile if zscore > 0 else 1 - percentile

    def _get_zscore(self, gender: Gender, name: str,
                    url_param: str, ext_option1: str, ext_option2: str,
                    option_choice: str) -> float:
        if name not in self.__name_rating__[gender]:
            return 0

        if option_choice.lower() == ext_option1.lower():
            go_higher = True
        elif option_choice.lower() == ext_option2.lower():
            go_higher = False
        else:
            raise ValueError('Unexpected option: {} --> {}'.format(url_param, option_choice))

        mean = RATING_DISTRIBUTION[gender][ext_option1][0]
        std_dev = RATING_DISTRIBUTION[gender][ext_option1][1]

        score = self.__name_rating__[gender][name][ext_option1]
        z_score = (score - mean) / std_dev
        if not go_higher:
            z_score = -z_score

        return z_score

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
        all options are mapped to external options, as defined at ALL_RATINGS
        returns a dict like
        {
            Gender.BOY : {
                "George": {
                    "A Good Name": 0.69,
                    "Masculine": 0.92,
                    "Classic": 0.46,
                    "Mature": 0.36,
                    ...
                }
            }
        }
        """
        result = {
            Gender.BOY: {},
            Gender.GIRL: {}
        }

        boy_count = 0
        girl_count = 0
        for name_dict in name_list:
            name = canonicalize_name(name_dict['name'])
            gender = canonicalize_gender(name_dict['gender'])

            votes = int(name_dict['votes'])
            if votes < 20:
                # logging.debug('Skip {name} because of limited votes: {votes}'.format(name=name, votes=votes))
                continue

            if gender == Gender.BOY:
                boy_count += 1
            else:
                girl_count += 1

            raw_ratings = name_dict['rating']
            parsed_ratings = {}
            for rating_type in ALL_RATINGS:
                int_opt1 = rating_type[0]
                ext_opt1 = rating_type[3]
                # here we map internal option 1 to external option 1, like "Strange" to "Creative"
                parsed_ratings[ext_opt1] = NameRating.get_score(raw_ratings, int_opt1)

            result[gender][name] = parsed_ratings

        logging.debug('Name Rating: boy count: {}, girl count: {}'.format(boy_count, girl_count))

        return result

    @staticmethod
    def get_score(rating_record: List[Dict[str, str]], int_opt1: str) -> float:
        record = next(x for x in rating_record if int_opt1 in x)
        return percentage_to_float(record[int_opt1])

    @staticmethod
    def get_options_by_url_param(url_param):
        record = next(x for x in ALL_RATINGS if url_param == x[2])
        return record[3], record[4]

    @staticmethod
    def get_source_file():
        return os.path.join(get_app_root_dir(), 'data', 'ratings.json')


NAME_RATING = NameRating()
