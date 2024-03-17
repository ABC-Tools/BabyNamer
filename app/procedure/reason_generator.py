from typing import List, Dict

from app.lib.common import Gender
from app.lib import name_pref as np
from app.lib import name_rating as nr
from app.lib import name_statistics as ns
from app.procedure.name_proposer import ProposedNames
import app.lib.redis as redis_lib


def generate(session_id: str,
             gender: Gender,
             user_prefs_dict: Dict[str, np.PrefInterface],
             proposed_names: ProposedNames,
             final_names: List[str]):
    names_from_options = set(proposed_names.get_suggest_names_from_option()).intersection(final_names)
    names_from_sibling_names = set(proposed_names.get_suggested_names_from_siblings()).intersection(final_names)
    names_from_embeddings = set(proposed_names.get_suggested_names_from_text()).intersection(final_names)
    names_from_popularity = set(proposed_names.get_suggested_names_from_popularity()).intersection(final_names)

    option_prefs = np.get_option_pref(user_prefs_dict)
    raw_options = {url_param: pref_inst.get_val() for url_param, pref_inst in option_prefs.items()}
    sibling_name_pref = np.get_sibling_name_pref(user_prefs_dict)
    name_reasons = generate_recommend_reasons(gender,
                                              raw_options,
                                              names_from_options,
                                              sibling_name_pref.get_val() if sibling_name_pref else [],
                                              names_from_sibling_names,
                                              names_from_popularity)

    # Write recommendation in redis
    redis_lib.update_name_proposal_reasons(session_id, name_reasons, clear_job_que=False)
    # write the ChatGPT job to create recommendation reasons
    redis_lib.add_recommendation_job(session_id, final_names)


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
