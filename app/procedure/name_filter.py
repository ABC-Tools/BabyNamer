import logging
from typing import List, Tuple, Dict

from app.lib.common import Gender
from app.lib import name_pref as np
from app.lib import similar_names as sn
import app.lib.redis as redis_lib


def filter_names(session_id: str,
                 gender: Gender,
                 user_prefs_dict: Dict[str, np.PrefInterface],
                 user_sentiments: np.UserSentiments,
                 name_score_list: List[Tuple[str, float]]) -> List[Tuple[str, float]]:
    name_prefs = np.get_name_pref(user_prefs_dict)
    displayed_names = redis_lib.get_displayed_names(session_id)

    # Filter names based on preference
    names_to_avoid = set()
    for pref in name_prefs:
        if isinstance(pref, np.MotherName) or  isinstance(pref, np.FatherName):
            names_to_avoid.add(pref.get_val())
        elif isinstance(pref, np.SiblingNames):
            names_to_avoid.update(pref.get_val())
        elif isinstance(pref, np.NamesToAvoid):
            names_to_avoid.update(pref.get_val())
            for name in pref.get_val():
                similar_names = sn.SIMILAR_NAMES.get(name, gender)
                names_to_avoid.update(similar_names)

    filtered_name_score_list = [(name, score) for name, score in name_score_list if name not in names_to_avoid]
    filtered_out_names = [name for name, score in name_score_list if name in names_to_avoid]
    if filtered_out_names:
        logging.debug('Names {} has been removed because of user preferences'.format(filtered_out_names))

    # filter out names which user has reviewed (favored/liked/disliked)
    names_from_sentiments = set(user_sentiments.get_val().keys())
    filtered_out_names = [name for name, score in filtered_name_score_list if name in names_from_sentiments]
    filtered_name_score_list = [(name, score) for name, score in filtered_name_score_list
                                if name not in names_from_sentiments]
    if filtered_out_names:
        logging.debug('Names {} has been removed because of user sentiments'.format(filtered_out_names))

    # filter out names which is similar to those names which user disliked
    similar_disliked_names = set()
    for name, sentiment_dict in user_sentiments.get_val().items():
        if sentiment_dict['sentiment'] != np.Sentiment.DISLIKED:
            continue

        similar_names = sn.SIMILAR_NAMES.get(name, gender)
        similar_disliked_names.update(similar_names)
    filtered_out_names = [name for name, score in filtered_name_score_list if name in similar_disliked_names]
    filtered_name_score_list = [(name, score) for name, score in filtered_name_score_list
                                if name not in similar_disliked_names]
    if filtered_out_names:
        logging.debug('Names {} has been removed because they are similar as names user disliked'.format(
            filtered_out_names))

    # filter names displayed before
    displayed_names = set(displayed_names)
    filtered_out_names = [name for name, score in filtered_name_score_list if name in displayed_names]
    filtered_name_score_list = [(name, score) for name, score in filtered_name_score_list
                                if name not in similar_disliked_names]
    if filtered_out_names:
        logging.debug('Names {} has been removed because they have been displayed to user before'.format(
            filtered_out_names))

    return filtered_name_score_list


