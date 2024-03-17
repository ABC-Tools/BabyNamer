import logging

from app.lib.common import Gender

import app.lib.redis as redis_lib
from app.procedure import name_proposer as n_proposer
from app.procedure import name_ranker as n_ranker
from app.procedure import name_filter as n_filter
from app.procedure import reason_generator as r_generator


def suggest(session_id, gender: Gender, last_suggest_no=None, count=20):
    # Fetch all preferences and sentiments from redis
    user_prefs_dict = redis_lib.get_user_pref(session_id)
    user_sentiments = redis_lib.get_user_sentiments(session_id)
    logging.debug('Fetched user prefs: {}'.format(list(user_prefs_dict.keys())))

    proposed_names = n_proposer.proposed_names(gender, user_prefs_dict, user_sentiments, count=count)

    # get the ranked names based on scores
    name_score_list = n_ranker.rank_names(proposed_names)

    # use name preference to do final filtering
    final_name_score_list = n_filter.filter_names(
        session_id, gender, user_prefs_dict, user_sentiments, name_score_list)
    final_names = [name for name, score in final_name_score_list]

    # Trim names based on the maximum count
    max_count = count if len(final_names) > count else len(final_names)
    final_names = final_names[0:max_count]

    # generate recommendation reasons
    r_generator.generate(session_id, gender, user_prefs_dict, proposed_names, final_names)

    # write data for late analysis
    logging.info('[data] (session: {}) final suggested names: {}'.format(
        session_id, sorted(final_names)))
    names_from_options = set(proposed_names.get_suggest_names_from_option()).intersection(final_names)
    logging.info('[data] (session: {}) final suggested names from options: {}'.format(
        session_id, sorted(names_from_options)))
    names_from_embeddings = set(proposed_names.get_suggested_names_from_text()).intersection(final_names)
    logging.info('[data] (session: {}) final suggested names from text embeddings: {}'.format(
        session_id, sorted(names_from_embeddings)))
    names_from_sibling_names = set(proposed_names.get_suggested_names_from_siblings()).intersection(final_names)
    logging.info('[data] (session: {}) final suggested names from sibling names: {}'.format(
        session_id, sorted(names_from_sibling_names)))
    names_from_popularity = set(proposed_names.get_suggested_names_from_popularity()).intersection(final_names)
    logging.info('[data] (session: {}) final suggested names from names_from_popularity: {}'.format(
        session_id, sorted(names_from_popularity)))

    redis_lib.append_displayed_names(session_id, final_names)

    return final_names

