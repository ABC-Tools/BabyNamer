import logging
from typing import List, Dict, Set

from app.lib.common import Gender
from app.lib import name_pref as np
import app.lib.name_sentiments as ns
from app.lib.name_sentiments import UserSentiments
import app.lib.redis as redis_lib


def filter_names(session_id: str,
                 gender: Gender,
                 user_prefs_dict: Dict[str, np.PrefInterface],
                 user_sentiments: UserSentiments,
                 name_list: List[str],
                 filter_displayed_names: bool = False) -> List[str]:
    # Filter names based on preference
    names_to_avoid = np.get_filter_names_from_pref(user_prefs_dict)
    filtered_names = filter_names_internal(name_list, names_to_avoid, 'user preferences')

    # filter out names which user has reviewed (favored/liked/disliked)
    names_from_sentiments = ns.get_filter_names_from_sentiments(user_sentiments)
    filtered_names = filter_names_internal(filtered_names, names_from_sentiments, 'user sentiments')

    # filter out names which is similar to those names which user disliked
    similar_disliked_names = ns.get_filter_names_from_dislikes(gender, user_sentiments)
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

