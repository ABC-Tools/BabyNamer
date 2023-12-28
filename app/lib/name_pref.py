from typing import Any, List, Dict, Union

import json
from enum import Enum
from .common import Gender, canonicalize_gender, canonicalize_name


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


class NameStyleEnum(Enum):
    MODERN = 1
    TRADITIONAL = 2

    def __str__(self):
        return f'{self.name}'.lower()


class NameStyle(PrefInterface):
    def __init__(self, style: NameStyleEnum):
        self._style = style

    @staticmethod
    def get_url_param_name():
        return 'style'

    @staticmethod
    def get_pref_meaning():
        return 'style of name'

    def get_val(self) -> NameStyleEnum:
        return self._style

    def get_native_val(self):
        return str(self._style)

    def get_val_str(self) -> str:
        return str(self._style)

    @staticmethod
    def create(raw_style: str):
        raw_style = raw_style.strip().lower()
        if not raw_style:
            return None

        if raw_style in ['modern']:
            return NameStyle(NameStyleEnum.MODERN)
        elif raw_style in ['traditional']:
            return NameStyle(NameStyleEnum.TRADITIONAL)

        raise ValueError('Invalid style value; expect the value '
                         'of "modern" or "traditional", but got: {}'.format(raw_style))


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
                   Origin, NamesToAvoid, NameStyle, OtherPref]


