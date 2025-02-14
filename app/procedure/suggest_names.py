import logging
from typing import Dict, Set

from app.lib.common import Gender

import app.lib.redis as redis_lib
from app.lib.name_sentiments import UserSentiments
from app.procedure import name_proposer as n_proposer
from app.procedure import name_ranker as n_ranker
from app.procedure import name_filter as n_filter
from app.procedure import reason_generator as r_generator
from app.openai_lib import chat_completion as cc
from app.lib import name_pref as np
import app.lib.name_sentiments as ns


def suggest(session_id, gender: Gender, filter_displayed_names=False, count=20):
    return suggest_names_using_gpt(session_id, gender, filter_displayed_names=filter_displayed_names, count=count)


def suggest_names_using_facts(session_id, gender: Gender, filter_displayed_names=False, count=20):
    # Fetch all preferences and sentiments from redis
    user_prefs_dict = redis_lib.get_user_pref(session_id)
    user_sentiments = redis_lib.get_user_sentiments(session_id)
    logging.debug('Fetched user prefs: {}'.format(list(user_prefs_dict.keys())))

    proposed_names = n_proposer.proposed_names(gender, user_prefs_dict, user_sentiments, count=count)

    # get the ranked names based on scores
    name_score_list = n_ranker.rank_names(proposed_names)
    ranked_names = [name for name, score in name_score_list]

    # use name preference to do final filtering
    filtered_names = n_filter.filter_names(
        session_id, gender, user_prefs_dict, user_sentiments,
        ranked_names, filter_displayed_names=filter_displayed_names)

    # Trim names based on the maximum count
    max_count = min(count, len(filtered_names))

    # Use ChatGPT to understand the user input and do a final processing
    final_names = cc.check_proposed_names(filtered_names, user_prefs_dict, user_sentiments, max_count)
    final_names = final_names[0:max_count]
    logging.info(f'ChatGPT reviewed the proposed names and suggested names: {final_names}')

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


def suggest_names_using_gpt(session_id, gender: Gender, filter_displayed_names=False, count=20):
    user_prefs_dict = redis_lib.get_user_pref(session_id)
    user_sentiments = redis_lib.get_user_sentiments(session_id)
    logging.debug('Fetched user prefs: {}'.format(list(user_prefs_dict.keys())))

    names_to_avoid = get_names_to_avoid(session_id, gender, user_prefs_dict, user_sentiments, filter_displayed_names)

    final_names = cc.propose_names(gender, user_prefs_dict, user_sentiments, names_to_avoid, count)

    # generate recommendation reasons
    r_generator.generate(session_id, gender, user_prefs_dict, n_proposer.ProposedNames(), final_names)

    # write data for late analysis
    logging.info('[data] (session: {}) final suggested names: {}'.format(
        session_id, sorted(final_names)))

    redis_lib.append_displayed_names(session_id, final_names)

    return final_names


def get_names_to_avoid(session_id: str,
                       gender: Gender,
                       user_prefs: Dict[str, np.PrefInterface],
                       user_sentiments: UserSentiments,
                       filter_displayed_names) -> Set[str]:

    names_to_avoid = set()
    names_to_avoid = names_to_avoid.union(np.get_filter_names_from_pref(user_prefs))
    names_to_avoid = names_to_avoid.union(ns.get_filter_names_from_sentiments(user_sentiments))
    names_to_avoid = names_to_avoid.union(ns.get_filter_names_from_dislikes(gender, user_sentiments))
    if filter_displayed_names:
        names_to_avoid = names_to_avoid.union(set(redis_lib.get_displayed_names(session_id)))
    return names_to_avoid
