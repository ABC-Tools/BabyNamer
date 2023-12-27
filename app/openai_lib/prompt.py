from typing import Dict

from app.lib import name_pref as np


def create_user_prompt(user_prefs_dict: Dict[str, np.PrefInterface]) -> str:
    user_prefs = user_prefs_dict.values()
    # Create the start of prompt
    factors = [pref.__class__.get_pref_meaning() for pref in user_prefs]
    if len(factors) == 0:
        prompt_beginning = 'Suggest English names for a newborn.'
    else:
        prompt_beginning = "Suggest good English names for a newborn considering {}.".format(', '.join(factors))

    # create the paragraphs for user preferences
    formatted_prefs = []
    for pref in user_prefs:
        if isinstance(pref, np.GenderPref) or isinstance(pref, np.MotherName) \
                or isinstance(pref, np.FatherName) or isinstance(pref, np.NameStyle):
            pref_str = '{meaning}: {value}.'.format(meaning=pref.__class__.get_pref_meaning(),
                                                    value=pref.get_val_str())
            formatted_prefs.append(pref_str)
        elif isinstance(pref, np.FamilyName):
            pref_str = '{meaning}: {value}. Please suggest a few names which complement the {meaning}.'\
                .format(meaning=pref.__class__.get_pref_meaning(), value=pref.get_val_str())
            formatted_prefs.append(pref_str)
        elif isinstance(pref, np.Origin):
            pref_str = '{meaning}: {value}. Please suggest a few names which has the connection with {value}.'\
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
        elif isinstance(pref, np.NameSentiments):
            liked_template = '{meaning}: user {sentiment} the name of {name}{reason_clause}. ' \
                             'Please recommend a few names similar to {name} if possible.'
            disliked_template = '{meaning}: user {sentiment} the name of {name}{reason_clause}. ' \
                                'Please do not recommend names similar to {name} if possible.'
            saved_template = '{meaning}: user {sentiment} the name of {name}{reason_clause}. ' \
                             'Please recommend a few more names similar to {name}.'
            for name, sentiment_dict in pref.get_val().items():
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
                    meaning=pref.__class__.get_pref_meaning(),
                    sentiment=str(sentiment_dict['sentiment']),
                    name=name,
                    reason_clause=reason_clause)

                formatted_prefs.append(pref_str)
        else:
            raise ValueError('Unexpected user preference: {}'.format(pref.__class__.get_url_param_name()))

    user_pref_str = '\n'.join(formatted_prefs)

    return '''
{prompt_beginning}

{user_info_str}

Please suggest names without asking questions. Please provide 20 name proposals in a JSON format.

Example response:
{{
  "name 1": "2~5 sentences about why this is a good name, based on the information provided by user and based on the meaning of the name.",
  "name 2": "2~5 sentences about why this is a good name, based on the information provided by user and based on the meaning of the name.",
  ...
}}
'''.format(prompt_beginning=prompt_beginning, user_info_str=user_pref_str)
