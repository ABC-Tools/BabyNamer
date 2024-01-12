from typing import Dict

from app.lib.common import Gender

import app.lib.redis as redis_lib
import app.openai_lib.embedding_client as ec
from app.lib import name_statistics as ns
from app.lib import name_pref as np
from app.lib import embedding_search as es
from app.lib import name_rating as nr


def suggest(session_id, gender: Gender, count=50):
    # Fetch all preferences and sentiments from redis
    user_prefs_dict = redis_lib.get_user_pref(session_id)
    user_sentiments = redis_lib.get_user_sentiments(session_id)

    suggest_name_scores_dict = {}
    suggest_name_reason_dict = {}

    # User option is a significant factor; let us use it as base if present
    option_prefs = get_option_pref(user_prefs_dict)
    if option_prefs:
        count = int(1000 / len(option_prefs))
        suggest_name_scores_dict, suggest_name_reason_dict = nr.NAME_RATING.suggest(
            gender, option_prefs, count=count)

    # if there is text-based preference, use embedding either as a start or as a way to reorder
    if has_text_pref(user_prefs_dict, user_sentiments):
        # Fetch proposals from Embedding client
        eb = ec.creat_embedding_from_pref_sentiments(gender, user_prefs_dict, user_sentiments)
        suggested_names = es.FAISS_SEARCH.search_with_embedding(gender, eb, num_of_result=30)



    # use popularity
    # - if there is suggested names previously, augment using popularity rank
    # - if there is no suggested names previously, suggest the post popular names

    # use name preference to do final augment
    if has_name_pref(user_prefs_dict):
        pass


    # If there is no user preference or if there is only gender preference, use popular names
    if not user_prefs_dict or (len(user_prefs_dict) == 1 and
                               user_prefs_dict.get(np.GenderPref.get_url_param_name(), None)):
        popular_names = ns.NAME_STATISTICS.get_popular_names(gender, count=30)
        return popular_names



    # Write a copy in redis for late references
    redis_lib.update_name_proposal(session_id, suggested_names)

    return suggested_names


def has_text_pref(user_prefs_dict: Dict[str, np.PrefInterface],
                  user_sentiments: np.UserSentiments) -> bool:
    """
    Whether user provides preferences which can only be processed using language
    """
    text_pref_url_params = [x.get_url_param_name() for x in np.TEXT_PREFS]

    for present_pref_key in user_prefs_dict.keys():
        if present_pref_key not in text_pref_url_params:
            return True

    for name, val_dict in user_sentiments.get_val().items():
        if 'reason' in val_dict and val_dict['reason']:
            return True

    return False


def get_option_pref(user_prefs_dict: Dict[str, np.PrefInterface]) -> Dict[str, np.PrefInterface]:
    option_pref_url_params = [x.get_url_param_name() for x in np.OPTION_PREFS]

    result = {}
    for url_param, pref_instance in user_prefs_dict.items():
        if url_param not in option_pref_url_params:
            result[url_param] = pref_instance

    return result


def has_name_pref(user_prefs_dict: Dict[str, np.PrefInterface]) -> bool:
    name_pref_url_params = [x.get_url_param_name() for x in np.NAME_PREFS]

    for present_pref_key in user_prefs_dict.keys():
        if present_pref_key not in name_pref_url_params:
            return True

    return False


def filter_names(suggested_name_score_dict: Dict[str, float], )