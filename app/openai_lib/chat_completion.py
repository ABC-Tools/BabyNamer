import logging
import openai
import os
import json
import time

from typing import Dict, List
from app.lib import name_pref as np
from .prompt import create_user_prompt

API_KEY = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(api_key='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')

CONTENT_FORMAT_1 = """"
Please help the user to name the baby, based on the information provided by user.
"""

CONTENT_FORMAT_2 = """
You are a helpful assistant to suggest names for newborns based on specific information provided by the user.
"""


class InvalidResponse(json.decoder.JSONDecodeError):
    pass


def check_proposed_names(proposed_names: List[str],
                         user_prefs: Dict[str, np.PrefInterface],
                         user_sentiments: np.UserSentiments,
                         max_count: int):
    system_msg = "You are a helpful assistant to identify good names which meet the requirements from user's input"

    sentiment_summary = create_summary_of_user_sentiments(user_sentiments)
    other_pref = user_prefs.get(np.OtherPref.get_url_param_name()) .get_val() \
        if np.OtherPref.get_url_param_name() in user_prefs else ""
    if not sentiment_summary.strip() and not other_pref.strip():
        return proposed_names[:max_count]

    user_prompt = """
Please identify good names which meet the requirements from user's input.

please review the below proposed names, identify the top {max_count} names which meet the requirements 
from user's input, and return such {max_count} good names in a json format, like
{{
    "good names": ["name_1", "name_2", ...]
}}

The proposed names are ordered by priority. If possible, please return names from the beginning of
the proposed names which meet user's requirements.

If there are less {max_count} names from the proposed names which meet the requirements from user's input,
please suggest other names which meet the requirements from user's input, so {max_count} names are returned.

Proposed name: {proposed_names}
User's input:
{other_pref}
{sentiment_summary}
    """.format(proposed_names=proposed_names[:2*max_count],
               sentiment_summary=sentiment_summary,
               other_pref=other_pref,
               max_count=max_count)

    logging.debug(f"user_prompt: {user_prompt}")

    start_ts = int(time.time())
    response = client.with_options(max_retries=5, timeout=60).chat.completions.create(
        # GPT 3.5 seems not able to reason well
        # model="gpt-3.5-turbo-1106",
        model="gpt-4-1106-preview",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": system_msg
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ]
    )

    stop_reason = response.choices[0].finish_reason
    if stop_reason != 'stop':
        logging.warning('The stop reason is {}'.format(stop_reason))
    logging.info('Total used tokens: {} and elapse time: {} seconds'.format(
        response.usage.total_tokens, int(time.time()) - start_ts))

    logging.info('ChatGPT raw output: {}'.format(response.choices[0].message.content))
    try:
        parsed_rsp = json.loads(response.choices[0].message.content)
        final_names = parsed_rsp.get("good names", [])
    except json.decoder.JSONDecodeError as e:
        logging.exception(e, exc_info=True)
        raise e

    return final_names


def create_summary_of_user_sentiments(user_sentiments: np.UserSentiments) -> str:
    if not user_sentiments:
        return ''

    # create the paragraphs for user sentiments
    formatted_prefs = []

    liked_template = 'User {sentiment} the name of {name}{reason_clause}.'
    disliked_template = 'User {sentiment} the name of {name}{reason_clause}.'
    saved_template = 'User {sentiment} the name of {name} as a favorite{reason_clause}.'

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


def send_and_receive(user_prefs: Dict[str, np.PrefInterface], user_sentiments: np.UserSentiments) -> Dict[str, str]:
    user_prompt = create_user_prompt(user_prefs, user_sentiments)

    logging.info("system prompt: {}".format(CONTENT_FORMAT_2))
    logging.info("User prompt: {}".format(user_prompt))

    start_ts = int(time.time())
    response = client.with_options(max_retries=5, timeout=60).chat.completions.create(
        model="gpt-3.5-turbo-1106",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": CONTENT_FORMAT_2
             },
            {
                "role": "user",
                "content": user_prompt
            }
        ]
    )

    stop_reason = response.choices[0].finish_reason
    if stop_reason != 'stop':
        logging.warning('The stop reason is {}'.format(stop_reason))
    logging.info('Total used tokens: {} and elapse time: {} seconds'.format(
        response.usage.total_tokens, int(time.time()) - start_ts))

    try:
        parsed_rsp = json.loads(response.choices[0].message.content)
    except json.decoder.JSONDecodeError as e:
        logging.exception(e, exc_info=True)
        raise e

    # debug
    # import pprint
    # pprint.PrettyPrinter().pprint(parsed_rsp)

    return parsed_rsp
