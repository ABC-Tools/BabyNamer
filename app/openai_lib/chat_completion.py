import logging
import openai
import os
import json

from typing import Dict

import openai_lib.prompt as prompt_lib

API_KEY = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(api_key='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')

CONTENT_FORMAT_1 = """"
Please help the user to name the baby, based on the information provided by user.
Please only suggest genuine English names. Please provide 10 name proposals in a JSON format.
{
  "name 1": "the reason why this is a good name, based on the information provided by user.",
  "name 2": "the reason why this is a good name, based on the information provided by user.",
  ...
}
"""

CONTENT_FORMAT_2 = """
You are a helpful assistant to suggest names for newborns based on specific information provided by the user.
Please provide 10 name proposals in a JSON format.

Example response:
{
  "name 1": "the reason why this is a good name, based on the information provided by user.",
  "name 2": "the reason why this is a good name, based on the information provided by user.",
  ...
}
"""


class InvalidResponse(json.decoder.JSONDecodeError):
    pass


def send_and_receive(user_provided_info: Dict[str, str]) -> Dict[str, str]:
    user_prompt = prompt_lib.create_user_prompt(user_provided_info)
    logging.info("User prompt: {}".format(user_prompt))

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
    logging.info('Total used tokens: {}'.format(response.usage.total_tokens))

    try:
        parsed_rsp = json.loads(response.choices[0].message.content)
    except json.decoder.JSONDecodeError as e:
        logging.exception(e, exc_info=True)
        raise e

    # debug
    # import pprint
    # pprint.PrettyPrinter().pprint(parsed_rsp)

    return parsed_rsp
