from typing import Any, List, Dict, Union

import json
from enum import Enum
from .common import Gender, canonicalize_gender, canonicalize_name
import app.lib.name_rating as nr


class PrefInterface:
    @staticmethod
    def get_url_param_name():
        """
        :return: the parameter name used in URL requests; this can be also used for
        redis key
        """
        pass

    @staticmethod
    def get_pref_meaning():
        """
        :return: a string which is the English meaning of this preference
        """
        pass

    def get_val(self):
        """
        :return: the value (or, user choice) of this preference, which may have Enum value therefore
        is not appropriate for json.dumps
        """
        pass

    def get_native_val(self):
        """
        :return: the value (or, user choice) of this preference, which does not have Enum value and
        is appropriate for json.dumps
        """
        pass

    def get_val_str(self) -> str:
        pass

    @staticmethod
    def create(val: str):
        pass


class GenderPref(PrefInterface):
    def __init__(self, gender: Gender):
        self._gender = gender

    @staticmethod
    def get_url_param_name():
        return 'gender'

    @staticmethod
    def get_pref_meaning():
        return 'gender'

    def get_val(self):
        return self._gender

    def get_native_val(self):
        return str(self._gender)

    def get_val_str(self):
        return str(self._gender)

    @staticmethod
    def create(raw_gender: str):
        gender = canonicalize_gender(raw_gender)
        return GenderPref(gender)


class StringPref(PrefInterface):
    def __init__(self, val: str):
        self._val = val

    def get_val(self) -> str:
        return self._val

    def get_native_val(self):
        return self._val

    def get_val_str(self) -> str:
        return self._val


class FamilyName(StringPref):
    @staticmethod
    def get_url_param_name():
        return 'family_name'

    @staticmethod
    def get_pref_meaning():
        return 'family name'

    @staticmethod
    def create(name: str):
        if not name:
            return None

        return FamilyName(canonicalize_name(name))


class MotherName(StringPref):
    @staticmethod
    def get_url_param_name():
        return 'mother_name'

    @staticmethod
    def get_pref_meaning():
        return "mother's name"

    @staticmethod
    def create(name: str):
        if not name:
            return None
        return MotherName(canonicalize_name(name))


class FatherName(StringPref):
    @staticmethod
    def get_url_param_name():
        return 'father_name'

    @staticmethod
    def get_pref_meaning():
        return "father's name"

    @staticmethod
    def create(name: str):
        if not name:
            return None
        return FatherName(canonicalize_name(name))


class ListPref(PrefInterface):
    def __init__(self, val_list: List[str]):
        self._val_list = val_list

    def get_val(self) -> List[str]:
        return self._val_list.copy()

    def get_native_val(self):
        return self._val_list.copy()

    def get_val_str(self) -> str:
        return json.dumps(self._val_list)


class SiblingNames(ListPref):
    @staticmethod
    def get_url_param_name():
        return 'sibling_names'

    @staticmethod
    def get_pref_meaning():
        return "siblings' name"

    @staticmethod
    def create(name_list_str):
        """
        :param name_list_str: a string like ["mike", "george", ...]
        :return:
        """
        if not name_list_str:
            return None

        name_list = json.loads(name_list_str)
        if not isinstance(name_list, list):
            raise ValueError('Invalid sibling names; it should be an array, but get: {}'.format(name_list_str))

        # return None if no name is given
        if len(name_list) == 0:
            return None

        canonical_name_list = [canonicalize_name(name) for name in name_list]
        return SiblingNames(canonical_name_list)


class Origin(StringPref):
    @staticmethod
    def get_url_param_name():
        return 'origin'

    @staticmethod
    def get_pref_meaning():
        return 'family origin'

    @staticmethod
    def create(val: str):
        return Origin(val)


class NamesToAvoid(ListPref):
    @staticmethod
    def get_url_param_name():
        return 'names_to_avoid'

    @staticmethod
    def get_pref_meaning():
        return 'names to avoid'

    @staticmethod
    def create(name_list_str):
        """
        :param name_list_str: a string like ["mike", "george", ...]
        :return:
        """
        name_list = json.loads(name_list_str)
        if not isinstance(name_list, list):
            raise ValueError('Invalid names to avoid; it should be an array, but get: {}'.format(name_list_str))

        # return None if no name is given
        if len(name_list) == 0:
            return None

        canonicalize_name_list = [canonicalize_name(name) for name in name_list]
        return NamesToAvoid(canonicalize_name_list)


class RatingPref(PrefInterface):

    def __init__(self, choice: str):
        self._choice = choice

    def get_val(self):
        return self._choice

    def get_native_val(self):
        return self._choice

    def get_val_str(self) -> str:
        return self._choice


class StyleChoice(RatingPref):
    TYPES = next(x for x in nr.ALL_RATINGS if 'style_option' in x)

    @staticmethod
    def get_url_param_name():
        return StyleChoice.TYPES[2]

    @staticmethod
    def get_pref_meaning():
        return StyleChoice.TYPES[2].replace('_', ' ')

    @staticmethod
    def get_possible_vals():
        return [StyleChoice.TYPES[3], StyleChoice.TYPES[4]]

    @staticmethod
    def create(choice: str):
        choice = choice.lower().capitalize()
        if choice not in [StyleChoice.TYPES[3], StyleChoice.TYPES[4]]:
            raise ValueError("Invalid style choice; must be either {} or {}, but got {}".format(
                StyleChoice.TYPES[3], StyleChoice.TYPES[4], choice
            ))
        return StyleChoice(choice)


class MaturityChoice(RatingPref):
    TYPES = next(x for x in nr.ALL_RATINGS if 'maturity_option' in x)

    @staticmethod
    def get_url_param_name():
        return MaturityChoice.TYPES[2]

    @staticmethod
    def get_pref_meaning():
        return MaturityChoice.TYPES[2].replace('_', ' ')

    @staticmethod
    def get_possible_vals():
        return [MaturityChoice.TYPES[3], MaturityChoice.TYPES[4]]

    @staticmethod
    def create(choice: str):
        choice = choice.lower().capitalize()
        if choice not in [MaturityChoice.TYPES[3], MaturityChoice.TYPES[4]]:
            raise ValueError("Invalid maturity choice; must be either {} or {}, but got {}".format(
                MaturityChoice.TYPES[3], MaturityChoice.TYPES[4], choice
            ))
        return MaturityChoice(choice)


class FormalityChoice(RatingPref):
    TYPES = next(x for x in nr.ALL_RATINGS if 'formality_option' in x)

    @staticmethod
    def get_url_param_name():
        return FormalityChoice.TYPES[2]

    @staticmethod
    def get_pref_meaning():
        return FormalityChoice.TYPES[2].replace('_', ' ')

    @staticmethod
    def get_possible_vals():
        return [FormalityChoice.TYPES[3], FormalityChoice.TYPES[4]]

    @staticmethod
    def create(choice: str):
        choice = choice.lower().capitalize()
        if choice not in [FormalityChoice.TYPES[3], FormalityChoice.TYPES[4]]:
            raise ValueError("Invalid formality choice; must be either {} or {}, but got {}".format(
                FormalityChoice.TYPES[3], FormalityChoice.TYPES[4], choice
            ))
        return FormalityChoice(choice)


class ClassChoice(RatingPref):
    TYPES = next(x for x in nr.ALL_RATINGS if 'class_option' in x)

    @staticmethod
    def get_url_param_name():
        return ClassChoice.TYPES[2]

    @staticmethod
    def get_pref_meaning():
        return ClassChoice.TYPES[2].replace('_', ' ')

    @staticmethod
    def get_possible_vals():
        return [ClassChoice.TYPES[3], ClassChoice.TYPES[4]]

    @staticmethod
    def create(choice: str):
        choice = choice.lower().capitalize()
        if choice not in [ClassChoice.TYPES[3], ClassChoice.TYPES[4]]:
            raise ValueError("Invalid class choice; must be either {} or {}, but got {}".format(
                ClassChoice.TYPES[3], ClassChoice.TYPES[4], choice
            ))
        return ClassChoice(choice)


class EnvironmentChoice(RatingPref):
    TYPES = next(x for x in nr.ALL_RATINGS if 'environment_option' in x)

    @staticmethod
    def get_url_param_name():
        return EnvironmentChoice.TYPES[2]

    @staticmethod
    def get_pref_meaning():
        return EnvironmentChoice.TYPES[2].replace('_', ' ')

    @staticmethod
    def get_possible_vals():
        return [EnvironmentChoice.TYPES[3], EnvironmentChoice.TYPES[4]]

    @staticmethod
    def create(choice: str):
        choice = choice.lower().capitalize()
        if choice not in [EnvironmentChoice.TYPES[3], EnvironmentChoice.TYPES[4]]:
            raise ValueError("Invalid environment choice; must be either {} or {}, but got {}".format(
                EnvironmentChoice.TYPES[3], EnvironmentChoice.TYPES[4], choice
            ))
        return EnvironmentChoice(choice)


class MoralChoice(RatingPref):
    TYPES = next(x for x in nr.ALL_RATINGS if 'moral_option' in x)

    @staticmethod
    def get_url_param_name():
        return MoralChoice.TYPES[2]

    @staticmethod
    def get_pref_meaning():
        return MoralChoice.TYPES[2].replace('_', ' ')

    @staticmethod
    def get_possible_vals():
        return [MoralChoice.TYPES[3], MoralChoice.TYPES[4]]

    @staticmethod
    def create(choice: str):
        choice = choice.lower().capitalize()
        if choice not in [MoralChoice.TYPES[3], MoralChoice.TYPES[4]]:
            raise ValueError("Invalid moral choice; must be either {} or {}, but got {}".format(
                MoralChoice.TYPES[3], MoralChoice.TYPES[4], choice
            ))
        return MoralChoice(choice)


class StrengthChoice(RatingPref):
    TYPES = next(x for x in nr.ALL_RATINGS if 'strength_option' in x)

    @staticmethod
    def get_url_param_name():
        return StrengthChoice.TYPES[2]

    @staticmethod
    def get_pref_meaning():
        return StrengthChoice.TYPES[2].replace('_', ' ')

    @staticmethod
    def get_possible_vals():
        return [StrengthChoice.TYPES[3], StrengthChoice.TYPES[4]]

    @staticmethod
    def create(choice: str):
        choice = choice.lower().capitalize()
        if choice not in [StrengthChoice.TYPES[3], StrengthChoice.TYPES[4]]:
            raise ValueError("Invalid strength choice; must be either {} or {}, but got {}".format(
                StrengthChoice.TYPES[3], StrengthChoice.TYPES[4], choice
            ))
        return StrengthChoice(choice)


class TextureChoice(RatingPref):
    TYPES = next(x for x in nr.ALL_RATINGS if 'texture_option' in x)

    @staticmethod
    def get_url_param_name():
        return TextureChoice.TYPES[2]

    @staticmethod
    def get_pref_meaning():
        return TextureChoice.TYPES[2].replace('_', ' ')

    @staticmethod
    def get_possible_vals():
        return [TextureChoice.TYPES[3], TextureChoice.TYPES[4]]

    @staticmethod
    def create(choice: str):
        choice = choice.lower().capitalize()
        if choice not in [TextureChoice.TYPES[3], TextureChoice.TYPES[4]]:
            raise ValueError("Invalid texture choice; must be either {} or {}, but got {}".format(
                TextureChoice.TYPES[3], TextureChoice.TYPES[4], choice
            ))
        return TextureChoice(choice)


class CreativityChoice(RatingPref):
    TYPES = next(x for x in nr.ALL_RATINGS if 'creativity_option' in x)

    @staticmethod
    def get_url_param_name():
        return CreativityChoice.TYPES[2]

    @staticmethod
    def get_pref_meaning():
        return CreativityChoice.TYPES[2].replace('_', ' ')

    @staticmethod
    def get_possible_vals():
        return [CreativityChoice.TYPES[3], CreativityChoice.TYPES[4]]

    @staticmethod
    def create(choice: str):
        choice = choice.lower().capitalize()
        if choice not in [CreativityChoice.TYPES[3], CreativityChoice.TYPES[4]]:
            raise ValueError("Invalid creativity choice; must be either {} or {}, but got {}".format(
                CreativityChoice.TYPES[3], CreativityChoice.TYPES[4], choice
            ))
        return CreativityChoice(choice)


class ComplexityChoice(RatingPref):
    TYPES = next(x for x in nr.ALL_RATINGS if 'complexity_option' in x)

    @staticmethod
    def get_url_param_name():
        return ComplexityChoice.TYPES[2]

    @staticmethod
    def get_pref_meaning():
        return ComplexityChoice.TYPES[2].replace('_', ' ')

    @staticmethod
    def get_possible_vals():
        return [ComplexityChoice.TYPES[3], ComplexityChoice.TYPES[4]]

    @staticmethod
    def create(choice: str):
        choice = choice.lower().capitalize()
        if choice not in [ComplexityChoice.TYPES[3], ComplexityChoice.TYPES[4]]:
            raise ValueError("Invalid complexity choice; must be either {} or {}, but got {}".format(
                ComplexityChoice.TYPES[3], ComplexityChoice.TYPES[4], choice
            ))
        return ComplexityChoice(choice)


class ToneChoice(RatingPref):
    TYPES = next(x for x in nr.ALL_RATINGS if 'tone_option' in x)

    @staticmethod
    def get_url_param_name():
        return ToneChoice.TYPES[2]

    @staticmethod
    def get_pref_meaning():
        return ToneChoice.TYPES[2].replace('_', ' ')

    @staticmethod
    def get_possible_vals():
        return [ToneChoice.TYPES[3], ToneChoice.TYPES[4]]

    @staticmethod
    def create(choice: str):
        choice = choice.lower().capitalize()
        if choice not in [ToneChoice.TYPES[3], ToneChoice.TYPES[4]]:
            raise ValueError("Invalid tone choice; must be either {} or {}, but got {}".format(
                ToneChoice.TYPES[3], ToneChoice.TYPES[4], choice
            ))
        return ToneChoice(choice)


class IntellectualChoice(RatingPref):
    TYPES = next(x for x in nr.ALL_RATINGS if 'intellectual_option' in x)

    @staticmethod
    def get_url_param_name():
        return IntellectualChoice.TYPES[2]

    @staticmethod
    def get_pref_meaning():
        return IntellectualChoice.TYPES[2].replace('_', ' ')

    @staticmethod
    def get_possible_vals():
        return [IntellectualChoice.TYPES[3], IntellectualChoice.TYPES[4]]

    @staticmethod
    def create(choice: str):
        choice = choice.lower().capitalize()
        if choice not in [IntellectualChoice.TYPES[3], IntellectualChoice.TYPES[4]]:
            raise ValueError("Invalid intellectual choice; must be either {} or {}, but got {}".format(
                IntellectualChoice.TYPES[3], IntellectualChoice.TYPES[4], choice
            ))
        return IntellectualChoice(choice)


class Sentiment(Enum):
    LIKED = 1
    DISLIKED = 2
    SAVED = 3

    def __str__(self):
        return f'{self.name}'.lower()

    @staticmethod
    def create(s: str):
        if not s:
            return None

        if s.lower() in ['liked']:
            return Sentiment.LIKED
        elif s.lower() in ['disliked']:
            return Sentiment.DISLIKED
        elif s.lower() in ['saved']:
            return Sentiment.SAVED
        else:
            raise ValueError('Invalid sentiment type; allow only "Liked/Disliked"; got {}'.format(s))


class UserSentiments(PrefInterface):
    def __init__(self, names_sentiments: Dict[str, Dict[str, Any]]):
        self._names_sentiments = names_sentiments

    @staticmethod
    def get_url_param_name():
        return 'name_sentiments'

    @staticmethod
    def get_pref_meaning():
        return 'name sentiments'

    def get_val(self):
        """
        :return: a dictionary like {
            'George': {
                "sentiment": Sentiment.LIKED/DISLIKED/SAVED,
                "reason": "..."   <-- optional
            }
        }
        """
        return self._names_sentiments

    def get_native_val(self):
        """
        :return: a dictionary like {
            'George': {
                "sentiment": 'liked/disliked/saved',
                "reason": "..."   <-- optional
            }
        }
        """
        result = {}
        for name, enum_dict in self._names_sentiments.items():
            result[name] = enum_dict.copy()
            result[name]['sentiment'] = str(result[name]['sentiment'])

        return result

    def get_val_str(self) -> str:
        return json.dumps(self._names_sentiments)

    @staticmethod
    def create_from_dict(raw_names_sentiments: Dict[str, Dict[str, str]]):
        """
        create from dictionary by canonicalizing name and converting sentiment to enum
        """
        names_sentiments = {}
        for name, sentiment_dict in raw_names_sentiments.items():
            if 'sentiment' not in sentiment_dict or not sentiment_dict['sentiment']:
                raise ValueError('Invalid name sentiment: {}'.format(json.dumps(sentiment_dict)))

            name = canonicalize_name(name)
            names_sentiments[name] = {
                'sentiment': Sentiment.create(sentiment_dict['sentiment'])
            }
            if 'reason' in sentiment_dict:
                names_sentiments[name]['reason'] = sentiment_dict['reason']

        return UserSentiments(names_sentiments)

    @staticmethod
    def create(names_sentiment_str: str):
        if not names_sentiment_str:
            return None

        raw_names_sentiments = json.loads(names_sentiment_str)
        if not raw_names_sentiments:
            return None

        return UserSentiments.create_from_dict(raw_names_sentiments)


class OtherPref(StringPref):
    @staticmethod
    def get_url_param_name():
        return 'other'

    @staticmethod
    def get_pref_meaning():
        return "other preferences"

    @staticmethod
    def create(val: str):
        return OtherPref(val)


def str_dict_to_class_dict(str_dict: Dict[str, str]) -> Dict[str, PrefInterface]:
    """
    Convert a dictionary with URL parameter as key, and with values as a whole string, like
    {
        'gender': 'boy',
        'names_to_avoid': '["George", "Mike", ...]'  <-- the value is a json.dumps string
    }, into a dictionary like
    {
        'gender': Gender_Instance,
        'names_to_avoid': NamesToAvoid_Instance
    },
    which is often needed to convert from URL parameters or from Redis readings
    """
    result = {}
    for pref_class in ALL_PREFERENCES:
        val = str_dict.get(pref_class.get_url_param_name(), None)
        if not val:
            continue

        pref = pref_class.create(val)
        if pref is not None:
            result[pref_class.get_url_param_name()] = pref

    return result


def class_dict_to_str_dict(class_dict: Dict[str, PrefInterface]) -> Dict[str, str]:
    """
        Convert a dictionary with URL parameter as key, and with values as a class instance, like
        {
            'gender': Gender_Instance,
            'names_to_avoid': NamesToAvoid_Instance
        }, into a dictionary like
        {
            'gender': 'boy',
            'names_to_avoid': '["George", "Mike", ...]' <-- the value is a json.dumps string
        },
        which is often needed to write Redis
        """
    result = {}
    for url_param_name, pref_inst in class_dict.items():
        result[url_param_name] = pref_inst.get_val_str()

    return result


def class_dict_to_native_dict(class_dict: Dict[str, PrefInterface]) -> Dict[str, Union[str, List[str], Dict[str, str]]]:
    """
    Convert a dictionary with URL parameter as key, and with values as a class instance, like
        {
            'gender': Gender_Instance,
            'names_to_avoid': NamesToAvoid_Instance
        }, into a dictionary like
        {
            'gender': 'boy',
            'names_to_avoid': '["George", "Mike", ...]' <-- the value is a dictionary
        },
    which is often needed before calling json.dumps to return as HTTP response
    """
    result = {}
    for url_param_name, pref_inst in class_dict.items():
        result[url_param_name] = pref_inst.get_native_val()
    return result


def name_sentiments_by_sentiments(name_sentiments: UserSentiments) -> Dict[str, List[Dict[str, str]]]:
    """
    :return: a dictionary like
    {
        "liked": [
            {
                "name": "George",
                "reason": "blah"
            },
            {
                "name": "Mike",
                "reason": "what..."
            }
        ],
        "disliked": [
            {
                "name": "Kayden",
                "reason": "blah"
            },
            {
                "name": "Allen",
                "reason": "what..."
            }
        ]
    }
    """
    result = {
        "liked": [],
        "disliked": [],
        "saved": []
    }

    for name, val_dict in name_sentiments.get_val().items():
        if val_dict['sentiment'] == Sentiment.LIKED:
            tmp_dict = {'name': name}
            if "reason" in val_dict:
                tmp_dict["reason"] = val_dict["reason"]
            result['liked'].append(tmp_dict)
        elif val_dict['sentiment'] == Sentiment.DISLIKED:
            tmp_dict = {'name': name}
            if "reason" in val_dict:
                tmp_dict["reason"] = val_dict["reason"]
            result['disliked'].append(tmp_dict)
        else:
            tmp_dict = {'name': name}
            if "reason" in val_dict:
                tmp_dict["reason"] = val_dict["reason"]
            result['saved'].append(tmp_dict)

    return result


ALL_PREFERENCES = [GenderPref, FamilyName, MotherName, FatherName, SiblingNames,
                   Origin, NamesToAvoid, OtherPref,
                   StyleChoice, MaturityChoice, FormalityChoice, ClassChoice,
                   EnvironmentChoice, MoralChoice, StrengthChoice, TextureChoice,
                   CreativityChoice, ComplexityChoice, ToneChoice, IntellectualChoice]


NAME_PREFS = [FamilyName, MotherName, FatherName, SiblingNames, NamesToAvoid]

TEXT_PREFS = [Origin, OtherPref]

OPTION_PREFS = [StyleChoice, MaturityChoice, FormalityChoice, ClassChoice,
                EnvironmentChoice, MoralChoice, StrengthChoice, TextureChoice,
                CreativityChoice, ComplexityChoice, ToneChoice, IntellectualChoice]
