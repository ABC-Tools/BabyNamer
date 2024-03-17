import logging
from typing import Dict, List, Tuple

from app.procedure.name_proposer import ProposedNames


def rank_names(proposed_names: ProposedNames) -> List[Tuple[str, float]]:
    norm_suggest_names_from_option = normalize_scores(proposed_names.get_suggest_names_from_option())
    norm_suggested_names_from_text = normalize_scores(proposed_names.get_suggested_names_from_text())
    norm_suggested_names_from_siblings = normalize_scores(proposed_names.get_suggested_names_from_siblings())
    norm_suggested_names_from_popularity = normalize_scores(proposed_names.get_suggested_names_from_popularity())

    logging.debug('norm_suggest_names_from_option: {}'.format(norm_suggest_names_from_option))
    logging.debug('suggested_names_from_text: {}'.format(norm_suggested_names_from_text))
    logging.debug('suggested_names_from_siblings: {}'.format(norm_suggested_names_from_siblings))
    logging.debug('suggested_names_from_popularity: {}'.format(norm_suggested_names_from_popularity))

    all_names = set(norm_suggest_names_from_option)\
        .union(norm_suggested_names_from_text) \
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

