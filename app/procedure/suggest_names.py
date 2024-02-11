import logging
from typing import Dict, List, Tuple

from app.lib.common import Gender

import app.lib.redis as redis_lib
import app.openai_lib.embedding_client as ec
from app.lib import name_statistics as ns
from app.lib import name_pref as np
from app.lib import embedding_search as es
from app.lib import name_rating as nr
from app.lib import similar_names as sn


def suggest(session_id, gender: Gender, count=30):
    # Fetch all preferences and sentiments from redis
    user_prefs_dict = redis_lib.get_user_pref(session_id)
    user_sentiments = redis_lib.get_user_sentiments(session_id)
    logging.debug('Fetched user prefs: {}'.format(list(user_prefs_dict.keys())))

    # User option to get recommendation if there is option input
    suggest_names_from_option = {}
    option_prefs = get_option_pref(user_prefs_dict)
    raw_options = {url_param: pref_inst.get_val() for url_param, pref_inst in option_prefs.items()}
    if option_prefs:
        suggest_names_from_option = nr.NAME_RATING.suggest(gender, raw_options, count=count * 10)

    # Use text content to get recommendation if there is text input
    suggested_names_from_text = {}
    if has_text_pref(user_prefs_dict, user_sentiments):
        eb = ec.creat_embedding_from_pref_sentiments(gender, user_prefs_dict, user_sentiments)
        suggested_names_from_text = es.FAISS_SEARCH.search_with_embedding(gender, eb, num_of_result=count * 10)

    # Get similar names from siblings' names
    suggested_names_from_siblings = {}
    sibling_name_pref = get_sibling_name_pref(user_prefs_dict)
    if sibling_name_pref:
        suggested_names_from_siblings = suggest_name_using_sibling_names(gender, sibling_name_pref.get_val())
        logging.debug('suggest using sibling_name_pref: {}'.format(suggested_names_from_siblings))

    # Recommend names using popularity
    name_by_popularity = ns.NAME_STATISTICS.get_popular_names(gender, count=count * 10)
    suggested_names_from_popularity = {name: 1.0 - rank / len(name_by_popularity)
                                       for rank, name
                                       in enumerate(name_by_popularity)}

    # get the ranked names based on scores
    name_score_list = choose_names(suggest_names_from_option,
                                   suggested_names_from_text,
                                   suggested_names_from_siblings,
                                   suggested_names_from_popularity)

    # use name preference to do final filtering
    name_prefs = get_name_pref(user_prefs_dict)
    final_name_score_list = filter_using_name_pref(gender, name_score_list, name_prefs, user_sentiments)
    final_names = [name for name, score in final_name_score_list]
    max_count = count if len(final_names) > count else len(final_names)
    final_names = final_names[0:max_count]

    # generate recommendation reasons
    names_from_options = set(suggest_names_from_option).intersection(final_names)
    names_from_sibling_names = set(suggested_names_from_siblings).intersection(final_names)
    names_from_embeddings = set(suggested_names_from_text).intersection(final_names)
    names_from_popularity = set(suggested_names_from_popularity).intersection(final_names)
    name_reasons = generate_recommend_reasons(gender,
                                              raw_options,
                                              names_from_options,
                                              sibling_name_pref.get_val() if sibling_name_pref else [],
                                              names_from_sibling_names,
                                              names_from_popularity)

    # Write a copy in redis for late references
    redis_lib.update_name_proposal(session_id, final_names, name_reasons)
    # write the job to create recommendation reasons
    redis_lib.add_job(session_id, final_names)

    # write data for late analysis
    logging.info('[data] (session: {}) final suggested names: {}'.format(
        session_id, sorted(final_names)))
    logging.info('[data] (session: {}) final suggested names from options: {}'.format(
        session_id, sorted(names_from_options)))
    logging.info('[data] (session: {}) final suggested names from text embeddings: {}'.format(
        session_id, sorted(names_from_embeddings)))
    logging.info('[data] (session: {}) final suggested names from sibling names: {}'.format(
        session_id, sorted(names_from_sibling_names)))
    logging.info('[data] (session: {}) final suggested names from names_from_popularity: {}'.format(
        session_id, sorted(names_from_popularity)))

    return final_names


def generate_recommend_reasons(gender: Gender,
                               raw_options: Dict[str, str],
                               names_from_options,
                               sibling_names: List[str],
                               names_from_sibling_names,
                               names_from_popularity):
    name_reasons = nr.NAME_RATING.create_suggest_reason(gender, list(names_from_options), raw_options)

    for name in names_from_sibling_names:
        sibling_reason = 'we recommend this name because it complements the sibling\'s names ({sibling_names}).'\
                .format(sibling_names=', '.join(sibling_names))

        if name in name_reasons:
            name_reasons[name] = '{existing_reason} Also, {new_reason}'\
                .format(existing_reason=name_reasons[name], new_reason=sibling_reason)
        else:
            name_reasons[name] = sibling_reason.capitalize()

    for name in names_from_popularity:
        _, rank = ns.NAME_STATISTICS.get_frequency_and_rank(name, gender)
        popularity_reason = 'we recommend this name because it is very popular recently ' \
                            '(ranked #{rank} among all names in last 3 years)'.format(rank=rank)

        if name in name_reasons:
            name_reasons[name] = '{existing_reason} Further, {new_reason}'\
                .format(existing_reason=name_reasons[name], new_reason=popularity_reason)
        else:
            name_reasons[name] = popularity_reason.capitalize()

    return name_reasons


def choose_names(suggest_names_from_option,
                 suggested_names_from_text,
                 suggested_names_from_siblings,
                 suggested_names_from_popularity) -> List[Tuple[str, float]]:
    norm_suggest_names_from_option = normalize_scores(suggest_names_from_option)
    norm_suggested_names_from_text = normalize_scores(suggested_names_from_text)
    norm_suggested_names_from_siblings = normalize_scores(suggested_names_from_siblings)
    norm_suggested_names_from_popularity = normalize_scores(suggested_names_from_popularity)

    logging.debug('norm_suggest_names_from_option: {}'.format(norm_suggest_names_from_option))
    logging.debug('suggested_names_from_text: {}'.format(suggested_names_from_text))
    logging.debug('suggested_names_from_siblings: {}'.format(suggested_names_from_siblings))
    logging.debug('suggested_names_from_popularity: {}'.format(suggested_names_from_popularity))

    all_names = set(norm_suggest_names_from_option).union(norm_suggested_names_from_text) \
        .union(norm_suggested_names_from_siblings)\
        .union(norm_suggested_names_from_popularity)

    # TODO: add a weight of rank for each name; probably a weight of normal distribution
    # TODO: adjust the weights based on the number of options, length of text, and number of sibling names

    # merge scores
    result = {}
    for name in all_names:
        result[name] = norm_suggest_names_from_option.get(name, 0) \
                       + norm_suggested_names_from_text.get(name, 0) \
                       + norm_suggested_names_from_siblings.get(name, 0) \
                       + norm_suggested_names_from_popularity.get(name, 0)

    # sorted based scores
    result_list = [(name, score) for name, score in result.items()]
    result_list = sorted(result_list, key=lambda x: x[1], reverse=True)

    # return the result
    # num = min(len(result), count)
    return result_list


def normalize_scores(suggest_names_score_dict: Dict[str, float]) -> Dict[str, float]:
    """
    convert distance to scores, and normalized the score value between 0 and 1
    """
    if len(suggest_names_score_dict) == 0:
        return {}

    min_dist = min(suggest_names_score_dict.values())
    max_dist = max(suggest_names_score_dict.values())
    scale = max_dist - min_dist
    if scale < 0.00000001:
        result = {name: 1 for name, dist in suggest_names_score_dict.items()}
        return result

    return {name: ((dist - min_dist) / scale) for name, dist in suggest_names_score_dict.items()}


def has_text_pref(user_prefs_dict: Dict[str, np.PrefInterface],
                  user_sentiments: np.UserSentiments) -> bool:
    """
    Whether user provides preferences which can only be processed using language
    """
    text_pref_url_params = [x.get_url_param_name() for x in np.TEXT_PREFS]

    for present_pref_key in user_prefs_dict.keys():
        if present_pref_key in text_pref_url_params:
            return True

    for name, val_dict in user_sentiments.get_val().items():
        if 'reason' in val_dict and val_dict['reason']:
            return True

    return False


def get_option_pref(user_prefs_dict: Dict[str, np.PrefInterface]) -> Dict[str, np.PrefInterface]:
    option_pref_url_params = [x.get_url_param_name() for x in np.OPTION_PREFS]

    result = {}
    for url_param, pref_instance in user_prefs_dict.items():
        if url_param in option_pref_url_params:
            result[url_param] = pref_instance

    return result


def get_sibling_name_pref(user_prefs_dict: Dict[str, np.PrefInterface]):
    for pref_inst in user_prefs_dict.values():
        if isinstance(pref_inst, np.SiblingNames):
            return pref_inst

    return None


def suggest_name_using_sibling_names(gender: Gender,
                                     sibling_names: List[str],
                                     count=20) -> Dict[str, float]:
    name_similarity = {}

    for sibling_name in sibling_names:
        sibling_gender = ns.NAME_STATISTICS.guess_gender(sibling_name)
        tmp_result = es.FAISS_SEARCH.similar_names(sibling_gender, sibling_name, gender, num_of_result=20)

        for candidate_name, similarity in tmp_result.items():
            if candidate_name not in name_similarity:
                name_similarity[candidate_name] = 0
            name_similarity[candidate_name] += similarity

    name_similarity_list = [(candidate_name, similarity) for candidate_name, similarity in name_similarity.items()]
    name_similarity_list = sorted(name_similarity_list, key=lambda x: x[1], reverse=True)

    num = min(count, len(name_similarity_list))
    return {name: distance for name, distance in name_similarity_list[0:num]}


def get_name_pref(user_prefs_dict: Dict[str, np.PrefInterface]) -> List[np.PrefInterface]:
    name_pref_url_params = [x.get_url_param_name() for x in np.NAME_PREFS]

    result = []
    for present_pref_key, pref_inst in user_prefs_dict.items():
        if present_pref_key in name_pref_url_params:
            result.append(pref_inst)

    return result


def filter_using_name_pref(gender: Gender,
                           name_score_list: List[Tuple[str, float]],
                           name_prefs: List[np.PrefInterface],
                           user_sentiments: np.UserSentiments):
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

    return filtered_name_score_list
