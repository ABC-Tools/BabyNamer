import json
from enum import Enum
from typing import Any, Set, Dict, List

from app.lib import similar_names as sn
from app.lib.common import canonicalize_name, Gender


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


class UserSentiments:
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


def get_filter_names_from_sentiments(user_sentiments: UserSentiments) -> Set[str]:
    return set(user_sentiments.get_val().keys())


def get_filter_names_from_dislikes(gender: Gender, user_sentiments: UserSentiments) -> Set[str]:
    similar_disliked_names = set()
    for name, sentiment_dict in user_sentiments.get_val().items():
        if sentiment_dict['sentiment'] != Sentiment.DISLIKED:
            continue

        similar_names = sn.SIMILAR_NAMES.get(name, gender)
        similar_disliked_names.update(similar_names)
    return similar_disliked_names
