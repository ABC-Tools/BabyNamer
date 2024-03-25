import logging
from typing import List, Tuple, Dict, Set

from app.lib.common import Gender
from app.lib import name_pref as np
from app.lib import similar_names as sn
import app.lib.redis as redis_lib


def filter_names(session_id: str,
                 gender: Gender,
                 user_prefs_dict: Dict[str, np.PrefInterface],
                 user_sentiments: np.UserSentiments,
                 name_list: List[str],
                 filter_displayed_names: bool = False) -> List[str]:
    # Filter names based on preference
    name_prefs = np.get_name_pref(user_prefs_dict)
    names_to_avoid = get_filter_names_from_pref(gender, name_prefs)
    filtered_names = filter_names_internal(name_list, names_to_avoid, 'user preferences')

    # filter out names which user has reviewed (favored/liked/disliked)
    names_from_sentiments = set(user_sentiments.get_val().keys())
    filtered_names = filter_names_internal(filtered_names, names_from_sentiments, 'user sentiments')

    # filter out names which is similar to those names which user disliked
    similar_disliked_names = get_filter_names_from_dislikes(gender, user_sentiments)
    filtered_names = filter_names_internal(filtered_names, similar_disliked_names, 'disliked names')

    # filter names displayed before
    if filter_displayed_names:
        displayed_names = set(redis_lib.get_displayed_names(session_id))
        filtered_names = filter_names_internal(filtered_names, displayed_names, 'previously displayed names')

    return filtered_names


def filter_names_internal(names: List[str],
                          names_to_avoid: Set[str],
                          verbose_reason: str) -> List[str]:
    filtered_names = [name for name in names if name not in names_to_avoid]
    filtered_out_names = [name for name in names if name in names_to_avoid]
    if filtered_out_names:
        logging.debug('Names {} has been removed because of {}'.format(filtered_out_names, verbose_reason))

    return filtered_names


def get_filter_names_from_pref(gender: Gender, name_prefs: List[np.PrefInterface]) -> Set[str]:
    names_to_avoid = set()
    for pref in name_prefs:
        if isinstance(pref, np.MotherName) or isinstance(pref, np.FatherName):
            names_to_avoid.add(pref.get_val())
        elif isinstance(pref, np.SiblingNames):
            names_to_avoid.update(pref.get_val())
        elif isinstance(pref, np.NamesToAvoid):
            names_to_avoid.update(pref.get_val())
            for name in pref.get_val():
                similar_names = sn.SIMILAR_NAMES.get(name, gender)
                names_to_avoid.update(similar_names)

    return names_to_avoid


def get_filter_names_from_dislikes(gender: Gender, user_sentiments: np.UserSentiments) -> Set[str]:
    similar_disliked_names = set()
    for name, sentiment_dict in user_sentiments.get_val().items():
        if sentiment_dict['sentiment'] != np.Sentiment.DISLIKED:
            continue

        similar_names = sn.SIMILAR_NAMES.get(name, gender)
        similar_disliked_names.update(similar_names)
    return similar_disliked_names
