import logging
from typing import Dict

from app.lib.common import Gender, canonicalize_gender
from app.lib import name_pref as np
from app.lib.name_sentiments import UserSentiments, Sentiment
import app.lib.name_rating as nr


def create_summary_of_user_sentiments(user_sentiments: UserSentiments) -> str:
    if not user_sentiments:
        return ''

    # create the paragraphs for user sentiments
    formatted_prefs = []

    liked_template = 'User {sentiment} the name of {name}{reason_clause}.'
    disliked_template = 'User {sentiment} the name of {name}{reason_clause}.'
    saved_template = 'User {sentiment} the name of {name} as a favorite{reason_clause}.'

    for name, sentiment_dict in user_sentiments.get_val().items():
        if sentiment_dict['sentiment'] == Sentiment.LIKED:
            template = liked_template
        elif sentiment_dict['sentiment'] == Sentiment.DISLIKED:
            template = disliked_template
        elif sentiment_dict['sentiment'] == Sentiment.SAVED:
            template = saved_template
        else:
            raise ValueError('Unexpected sentiment: {}'.format(sentiment_dict['sentiment']))

        if 'reason' in sentiment_dict and sentiment_dict['reason']:
            reason_clause = ', because {}'.format(sentiment_dict['reason'])
        else:
            reason_clause = ''

        pref_str = template.format(
            meaning=user_sentiments.__class__.get_pref_meaning(),
            sentiment=str(sentiment_dict['sentiment']),
            name=name,
            reason_clause=reason_clause)

        formatted_prefs.append(pref_str)

    return '\n'.join(formatted_prefs)


def create_text_from_user_pref(user_prefs_dict: Dict[str, np.PrefInterface]) -> str:
    # create the paragraphs for user preferences
    formatted_prefs = []
    for pref in user_prefs_dict.values():
        if isinstance(pref, np.Origin):
            pref_str = 'User\' family origin is {value}. Please suggest a few names related to {value}.'\
                .format(value=pref.get_val_str())
            formatted_prefs.append(pref_str)
        elif isinstance(pref, np.OtherPref):
            pref_str = 'User also says: {value}.'.format(value=pref.get_val())
            formatted_prefs.append(pref_str)
        elif isinstance(pref, np.StyleChoice) or isinstance(pref, np.MaturityChoice) or \
                isinstance(pref, np.FormalityChoice) or isinstance(pref, np.ClassChoice) or \
                isinstance(pref, np.EnvironmentChoice) or isinstance(pref, np.MoralChoice) or \
                isinstance(pref, np.StrengthChoice) or isinstance(pref, np.TextureChoice) or \
                isinstance(pref, np.CreativityChoice) or isinstance(pref, np.ComplexityChoice) or \
                isinstance(pref, np.ToneChoice) or isinstance(pref, np.IntellectualChoice):
            choice = pref.get_val_str()
            pref_str = 'In terms of {meaning}, user prefers {choice} names.'.format(
                meaning=pref.__class__.get_pref_meaning(), choice=choice)
            formatted_prefs.append(pref_str)
        else:
            logging.warning('skip user preference of {type} with value of {value}'.format(
                type=pref.get_url_param_name(), value=pref.get_val()
            ))

    return '\n'.join(formatted_prefs)


def create_rating_description(name: str, gender: Gender):
    gender = canonicalize_gender(gender)
    rating_dict = nr.NAME_RATING.get_feature_percentiles(name, gender)
    if not rating_dict:
        return ''

    all_sentences = []
    for rating_url_param, val_dict in rating_dict.items():
        leading_part = rating_url_param.replace('_', ' ').replace('option', 'rating')
        parts = []
        for option, val_tuple in val_dict.items():
            zscore = val_tuple[3]
            percentile_float = val_tuple[4]
            if zscore < 0 or percentile_float >= 0.4:
                continue

            template = 'this name is considered as {option} ' \
                       '(the {direction} {rank_percent} {option} name across all {gender} names).'
            parts.append(template.format(
                option=option.lower(),
                direction=val_tuple[1],
                rank_percent=val_tuple[2],
                gender=str(gender)
            ))

        if parts:
            sentence = '{leading}: {description}'.format(
                leading=leading_part, description=' '.join(parts)
            )
            all_sentences.append(sentence)

    return '\n'.join(all_sentences)
