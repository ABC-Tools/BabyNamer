from typing import List

import app.lib.name_pref as np


def create_user_prompt(user_prefs: List[np.PrefInterface]) -> str:
    # Create the start of prompt
    factors = [pref.__class__.get_pref_meaning() for pref in user_prefs]
    if len(factors) == 0:
        prompt_beginning = 'Suggest English names for a newborn '
    else:
        prompt_beginning = "Suggest good English names for a newborn considering {}.".format(factors.join(', '))

    # create the paragraphs for user preferences
    formatted_prefs = []
    for pref in user_prefs:
        if isinstance(pref, np.GenderPref) or isinstance(pref, np.FamilyName) or \
                isinstance(pref, np.MotherName) or isinstance(pref, np.FatherName) or \
                isinstance(pref, np.Origin) or isinstance(pref, np.NameStyle):
            pref_str = '{meaning}: {value}'.format(meaning=pref.__class__.get_pref_meaning(),
                                                   value=pref.get_val_str())
            formatted_prefs.append(pref_str)
        elif isinstance(pref, np.SiblingNames):
            names_str = pref.get_val().join(', ')
            pref_str = "{meaning}: {value}. Please suggest names which complement or are similar" \
                       " in style or theme to these siblings' names".format(
                            meaning=pref.__class__.get_pref_meaning(), value=names_str)
            formatted_prefs.append(pref_str)
        elif isinstance(pref, np.NamesToAvoid):
            names_str = pref.get_val().join(', ')
            pref_str = '{meaning}: {value}'.format(meaning=pref.__class__.get_pref_meaning(), value=names_str)
            formatted_prefs.append(pref_str)
        elif isinstance(pref, np.NameSentiments):
            for name, sentiment_dict in pref.get_val().items():
                if 'reason' in sentiment_dict and sentiment_dict['reason']:
                    pref_str = '{meaning}: {sentiment} {name}, because {reason}'.format(
                        meaning=pref.__class__.get_pref_meaning(),
                        sentiment=str(sentiment_dict['sentiment']),
                        name=name,
                        reason=sentiment_dict['reason'])
                else:
                    pref_str = '{meaning}: {sentiment} {name}'.format(
                        meaning=pref.__class__.get_pref_meaning(),
                        sentiment=str(sentiment_dict['sentiment']),
                        name=name)
                formatted_prefs.append(pref_str)
        else:
            raise ValueError('Unexpected user preference: {}'.format(pref.__class__.get_url_param_name()))

    user_pref_str = formatted_prefs.join('\n')

    return '''
{prompt_beginning}

{user_info_str}

Please suggest names without asking questions. Please provide 10 name proposals in a JSON format.

Example response:
{
  "name 1": "the reason why this is a good name, based on the information provided by user.",
  "name 2": "the reason why this is a good name, based on the information provided by user.",
  ...
}
    '''.format(prompt_beginning=prompt_beginning, user_info_str=user_pref_str)
