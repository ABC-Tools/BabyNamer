"""
Redis Queue is an alternative approach; but Redis Queue is single-tasked, which is not
effective for ChatGPT conversation, because the conversation is very slow and IO heavy
"""
import json
import logging
import time
from typing import List
import asyncio

import tiktoken
import openai

import app.lib.redis as redis_lib
import app.openai_lib.prompt as prompt
import app.lib.name_pref as np
import app.lib.origin_and_short_meaning as osm
import app.lib.name_meaning as nm


tiktoken_encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
client = openai.AsyncOpenAI(api_key='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')


def main_loop():
    print('background worker starts...')
    while True:
        key, session_id = redis_lib.redis_client.blpop(
            redis_lib.PROPOSAL_REASON_JOB_QUEUE_KEY, timeout=15 * 60)
        if session_id:
            asyncio.run(handle_job(session_id))
        else:
            logging.info('Live pulse from background worker')


async def handle_job_with_exception(session_id):
    try:
        start_ts = time.time()
        logging.info('Start to process the job for {}'.format(session_id))
        await handle_job(session_id)
        logging.info('Complete the job for {} after {} seconds'.format(session_id, time.time() - start_ts))

        raise ValueError('test')
    except Exception as e:
        logging.exception(e, exc_info=True)
        logging.error('Failed to handle job for {}'.format(session_id))


async def handle_job(session_id):
    proposed_names = redis_lib.get_name_proposals(session_id)
    if not proposed_names:
        logging.warning('Missing proposed names for the job with session id {}'.format(session_id))
        return

    gender, user_context = create_user_description(session_id)
    if not gender:
        logging.warning("Missing gender information for {}".format(session_id))
        return

    name_descriptions = create_name_descriptions(gender, proposed_names)

    completion_text = '''
Write reasons why the list of names are good candidates for user's newborn, based on the user provided preference, and
based on the descriptions of the names. Please suggest names without asking questions.
Please provide the reasons in a JSON format. 

Example response:
{{
  "name 1": "1~4 sentences about why this is a good name, based on the information provided by user and based on the description of the name.",
  "name 2": "1~4 sentences about why this is a good name, based on the information provided by user and based on the description of the name.",
  ...
}}

The list of names: {proposed_names}.

{user_context}
    '''.format(proposed_names=', '.join(proposed_names), user_context=user_context)

    token_num = count_tokens(completion_text)
    for description in name_descriptions:
        new_token_num = count_tokens(description)
        if token_num + new_token_num >= 16000:
            break

        completion_text = completion_text + "\n\n" + description
        token_num += new_token_num

    start_ts = time.time()
    resp = await client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "user",
                "content": completion_text,
            }
        ]
    )

    stop_reason = resp.choices[0].finish_reason
    if stop_reason != 'stop':
        logging.warning('The stop reason is {}'.format(stop_reason))
    logging.info('Total used tokens: {} and elapse time: {} seconds'.format(
        resp.usage.total_tokens, int(time.time()) - start_ts))

    parsed_rsp = json.loads(resp.choices[0].message.content)

    redis_lib.update_name_proposal_reasons(session_id, parsed_rsp)


def create_user_description(session_id):
    # Fetch all preferences and sentiments from redis
    user_prefs_dict = redis_lib.get_user_pref(session_id)
    user_sentiments = redis_lib.get_user_sentiments(session_id)
    gender_pref = user_prefs_dict.get(np.GenderPref.get_url_param_name(), None)
    if not gender_pref:
        return None, ''
    gender = gender_pref.get_val()

    user_pref_str = prompt.create_text_from_user_pref(user_prefs_dict)
    user_sentiments_str = prompt.create_text_from_user_sentiments(user_sentiments)
    user_context = '''
The user provided preference:
{user_pref_str}
{user_sentiments_str}
The end of user provided preference
    '''.format(user_pref_str=user_pref_str, user_sentiments_str=user_sentiments_str)

    return gender, user_context


def create_name_descriptions(gender, proposed_names) -> List[str]:
    # create description of each name
    name_descriptions = []
    for name in proposed_names:
        origin, short_meaning = osm.ORIGIN_SHORT_MEANING.get(name, gender)
        if origin or short_meaning:
            os_description = f'origin: {origin}\n short meaning: {short_meaning}'.format(
                origin=origin, short_meaning=short_meaning
            )
        else:
            os_description = ''
        overall_description = nm.NAME_MEANING.get(name, gender)
        # rating_description = prompt.create_rating_description(name, gender)
        whole_description = '''
The description of name "{name}":
{os_description}
{overall_description}
The end of the description of name "{name}"
        '''.format(name=name, os_description=os_description,
                   overall_description=overall_description)
        name_descriptions.append(whole_description)

    return name_descriptions


def count_tokens(text: str) -> int:
    return len(tiktoken_encoding.encode(text))


if __name__ == "__main__":
    main_loop()
