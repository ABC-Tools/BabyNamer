import logging
import openai
import os
import json
import time

from typing import Dict
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


def send_and_receive(user_prefs: Dict[str, np.PrefInterface]) -> Dict[str, str]:
    user_prompt = create_user_prompt(user_prefs)

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
