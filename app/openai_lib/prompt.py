from typing import Dict

from app.lib.common import Gender, canonicalize_gender
from app.lib import name_pref as np
import app.lib.name_rating as nr


def create_user_prompt(user_prefs_dict: Dict[str, np.PrefInterface],
                       user_sentiments: np.UserSentiments) -> str:
    user_prefs = user_prefs_dict.values()
    # Create the start of prompt
    factors = [pref.__class__.get_pref_meaning() for pref in user_prefs]
    if user_sentiments:
        factors.append(np.UserSentiments.get_pref_meaning())
    if len(factors) == 0:
        prompt_beginning = 'Suggest English names for a newborn.'
    else:
        prompt_beginning = "Suggest good English names for a newborn considering {}.".format(', '.join(factors))

    # create the paragraphs for user preferences
    user_pref_str = create_text_from_user_pref(user_prefs_dict)
    user_sentiments_str = create_text_from_user_sentiments(user_sentiments)

    return '''
{prompt_beginning}

{user_pref_str}
{user_sentiments_str}

Please suggest names without asking questions. Please provide 10 name proposals in a JSON format.

Example response:
{{
  "name 1": "2~5 sentences about why this is a good name, based on the information provided by user and based on the meaning of the name.",
  "name 2": "2~5 sentences about why this is a good name, based on the information provided by user and based on the meaning of the name.",
  ...
}}
'''.format(prompt_beginning=prompt_beginning, user_pref_str=user_pref_str, user_sentiments_str=user_sentiments_str)


def create_text_from_user_sentiments(user_sentiments: np.UserSentiments) -> str:
    if not user_sentiments:
        return ''

    # create the paragraphs for user sentiments
    formatted_prefs = []

    liked_template = '{meaning}: user {sentiment} the name of {name}{reason_clause}. ' \
                     'Please recommend a few names similar to {name} if possible.'
    disliked_template = '{meaning}: user {sentiment} the name of {name}{reason_clause}. ' \
                        'Please do not recommend names similar to {name} if possible.'
    saved_template = '{meaning}: user {sentiment} the name of {name} as a favorite{reason_clause}. ' \
                     'Please recommend a few more names similar to {name}.'
    for name, sentiment_dict in user_sentiments.get_val().items():
        if sentiment_dict['sentiment'] == np.Sentiment.LIKED:
            template = liked_template
        elif sentiment_dict['sentiment'] == np.Sentiment.DISLIKED:
            template = disliked_template
        elif sentiment_dict['sentiment'] == np.Sentiment.SAVED:
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
        if isinstance(pref, np.GenderPref) or isinstance(pref, np.MotherName) \
                or isinstance(pref, np.FatherName):
            pref_str = '{meaning}: {value}.'.format(meaning=pref.__class__.get_pref_meaning(),
                                                    value=pref.get_val_str())
            formatted_prefs.append(pref_str)
        elif isinstance(pref, np.FamilyName):
            pref_str = '{meaning}: {value}. Please suggest a few names which complement the {meaning}.' \
                .format(meaning=pref.__class__.get_pref_meaning(), value=pref.get_val_str())
            formatted_prefs.append(pref_str)
        elif isinstance(pref, np.Origin):
            pref_str = '{meaning}: {value}. Please suggest a few names which has the connection with {value}.' \
                .format(meaning=pref.__class__.get_pref_meaning(), value=pref.get_val_str())
            formatted_prefs.append(pref_str)
        elif isinstance(pref, np.SiblingNames):
            names_str = ', '.join(pref.get_val())
            pref_str = "{meaning}: {value}. Please suggest a few names which complement or are similar" \
                       " in style or theme to these {meaning}." \
                .format(meaning=pref.__class__.get_pref_meaning(), value=names_str)
            formatted_prefs.append(pref_str)
        elif isinstance(pref, np.NamesToAvoid):
            names_str = ', '.join(pref.get_val())
            pref_str = '{meaning}: {value}.'.format(meaning=pref.__class__.get_pref_meaning(), value=names_str)
            formatted_prefs.append(pref_str)
        elif isinstance(pref, np.OtherPref):
            pref_str = 'Other info user provided: {value}.'.format(value=pref.get_val())
            formatted_prefs.append(pref_str)
        elif isinstance(pref, np.StyleChoice) or isinstance(pref, np.MaturityChoice) or \
                isinstance(pref, np.FormalityChoice) or isinstance(pref, np.ClassChoice) or \
                isinstance(pref, np.EnvironmentChoice) or isinstance(pref, np.MoralChoice) or \
                isinstance(pref, np.StrengthChoice) or isinstance(pref, np.TextureChoice) or \
                isinstance(pref, np.CreativityChoice) or isinstance(pref, np.ComplexityChoice) or \
                isinstance(pref, np.ToneChoice) or isinstance(pref, np.IntellectualChoice):
            choice = pref.get_val_str()
            pref_str = '{meaning}: user prefers {choice} names.'.format(
                meaning=pref.__class__.get_pref_meaning(), choice=choice)
            formatted_prefs.append(pref_str)
        else:
            raise ValueError('Unexpected user preference: {}'.format(pref.__class__.get_url_param_name()))

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
