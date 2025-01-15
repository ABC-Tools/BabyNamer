import logging
import openai
import os
import json
import time

from typing import Dict, List, Set
from app.lib import name_pref as np
from app.lib.name_sentiments import UserSentiments
import app.openai_lib.prompt as prompt
from app.lib.common import Gender

API_KEY = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(api_key='')


class InvalidResponse(json.decoder.JSONDecodeError):
    pass


def check_proposed_names(proposed_names: List[str],
                         user_prefs: Dict[str, np.PrefInterface],
                         user_sentiments: UserSentiments,
                         max_count: int):
    system_msg = "You are a helpful assistant to identify good names which meet the requirements from user's input"

    sentiment_summary = prompt.create_summary_of_user_sentiments(user_sentiments)
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
    response = client.with_options(max_retries=2, timeout=15).chat.completions.create(
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


def propose_names(gender: Gender,
                  user_prefs: Dict[str, np.PrefInterface],
                  user_sentiments: UserSentiments,
                  names_to_avoid: Set[str],
                  max_count: int):
    system_msg = "You are a helpful assistant to propose names for a newborn based on user's input"

    sentiment_summary = prompt.create_summary_of_user_sentiments(user_sentiments)
    pref_summary = prompt.create_text_from_user_pref(user_prefs)

    user_prompt = """
Please propose {max_count} names for a {gender} newborn based on user's input.

Return the {max_count} good names in a json format, like
{{
    "names": ["name_1", "name_2", ...]
}}.

User's input:
{pref_summary}
{sentiment_summary}

Please do not suggest the following names:
{names_to_avoid}
    """.format(gender=gender,
               sentiment_summary=sentiment_summary,
               pref_summary=pref_summary,
               max_count=max_count,
               names_to_avoid=names_to_avoid)

    logging.debug(f"user_prompt: {user_prompt}")

    start_ts = int(time.time())
    response = client.with_options(max_retries=2, timeout=15).chat.completions.create(
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
        final_names = parsed_rsp.get("names", [])
    except json.decoder.JSONDecodeError as e:
        logging.exception(e, exc_info=True)
        raise e

    return final_names
