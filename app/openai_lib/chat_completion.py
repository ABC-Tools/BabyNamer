import logging
import openai
import os
import json

API_KEY = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(api_key='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')


class InvalidResponse(json.decoder.JSONDecodeError):
    pass


def send_and_receive(user_input):
    response = client.with_options(max_retries=5, timeout=60).chat.completions.create(
        model="gpt-3.5-turbo-1106",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": """"
Please help the user to name the baby, based on the information provided by user. 
Please provide 10 name proposals in a JSON format, like
{
  "name_1": "the reason why this is a good name",
  "name_2": "the reason why this is a good name",
  ...
}
            """
             },
            {
                "role": "user",
                "content": user_input
            }
        ]
    )

    stop_reason = response.choices[0].finish_reason
    if stop_reason != 'stop':
        logging.warning('The stop reason is %s'.format(stop_reason))
    logging.info('Total used tokens: %s'.format(response.usage.total_tokens))

    try:
        parsed_rsp = json.loads(response.choices[0].message.content)
    except json.decoder.JSONDecodeError as e:
        logging.exception(e, exc_info=True)
        raise e

    # debug
    # import pprint
    # pprint.PrettyPrinter().pprint(parsed_rsp)

    return parsed_rsp
