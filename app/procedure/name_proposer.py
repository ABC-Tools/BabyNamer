import logging
from typing import List, Dict

from app.lib.common import Gender
import app.openai_lib.embedding_client as ec
from app.lib import name_statistics as ns
from app.lib import name_pref as np
from app.lib import embedding_search as es
from app.lib import name_rating as nr
from app.lib.name_sentiments import UserSentiments


class ProposedNames(object):

    def __init__(self,
                 suggest_names_from_option=None,
                 suggested_names_from_siblings=None,
                 suggested_names_from_text=None,
                 suggested_names_by_popularity=None):
        self._suggest_names_from_option = \
            suggest_names_from_option if suggest_names_from_option else []
        self._suggested_names_from_siblings = \
            suggested_names_from_siblings if suggested_names_from_siblings else []
        self._suggested_names_from_text = \
            suggested_names_from_text if suggested_names_from_text else []
        self._suggested_names_by_popularity = \
            suggested_names_by_popularity if suggested_names_by_popularity else []

    def get_suggest_names_from_option(self):
        return self._suggest_names_from_option

    def get_suggested_names_from_siblings(self):
        return self._suggested_names_from_siblings

    def get_suggested_names_from_text(self):
        return self._suggested_names_from_text

    def get_suggested_names_from_popularity(self):
        return self._suggested_names_by_popularity


def proposed_names(gender: Gender,
                   user_prefs_dict: Dict[str, np.PrefInterface],
                   user_sentiments: UserSentiments,
                   count=20):
    # User option to get recommendation if there is option input
    suggest_names_from_option = {}
    option_prefs = np.get_option_pref(user_prefs_dict)
    raw_options = {url_param: pref_inst.get_val() for url_param, pref_inst in option_prefs.items()}
    if option_prefs:
        suggest_names_from_option = nr.NAME_RATING.suggest(gender, raw_options, count=count * 10)

    # Get similar names from siblings' names
    suggested_names_from_siblings = {}
    sibling_name_pref = np.get_sibling_name_pref(user_prefs_dict)
    if sibling_name_pref:
        suggested_names_from_siblings = suggest_name_using_sibling_names(gender, sibling_name_pref.get_val())
        logging.debug('suggest using sibling_name_pref: {}'.format(suggested_names_from_siblings))

    # Use text content to get recommendation if there is text input
    suggested_names_from_text = {}
    if has_text_pref(user_prefs_dict, user_sentiments):
        eb = ec.create_embedding_from_pref_sentiments(gender, user_prefs_dict, user_sentiments)
        suggested_names_from_text = es.FAISS_SEARCH.search_with_embedding(gender, eb, num_of_result=count * 10)

    # Recommend names using popularity
    name_by_popularity = ns.NAME_STATISTICS.get_popular_names(gender, count=count * 10)
    suggested_names_from_popularity = {name: 1.0 - rank / len(name_by_popularity)
                                       for rank, name
                                       in enumerate(name_by_popularity)}

    return ProposedNames(suggest_names_from_option,
                         suggested_names_from_siblings,
                         suggested_names_from_text,
                         suggested_names_from_popularity)


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


def has_text_pref(user_prefs_dict: Dict[str, np.PrefInterface],
                  user_sentiments: UserSentiments) -> bool:
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
