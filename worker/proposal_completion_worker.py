"""
Redis Queue is an alternative approach; but Redis Queue is single-tasked, which is not
effective for ChatGPT conversation, because the conversation is very slow and IO heavy
"""
import json
import logging
import time
from typing import List
import asyncio
import os

import tiktoken
import openai
import redis.asyncio as redis_async

import app.lib.redis as redis_lib
import app.openai_lib.prompt as prompt
import app.lib.name_pref as np
import app.lib.origin_and_short_meaning as osm
import app.lib.name_meaning as nm


tiktoken_encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
client = openai.AsyncOpenAI(api_key='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', timeout=15)

redis_host = os.environ.get("REDISHOST", "10.49.86.211")
redis_port = int(os.environ.get("REDISPORT", 6379))

pending_task_count = 0


async def main_loop():
    redis_client = await redis_async.StrictRedis(host=redis_host, port=redis_port, decode_responses=True)

    logging.info('background worker starts...')
    while True:
        blpop_val = await redis_client.blpop(
            redis_lib.PROPOSAL_REASON_JOB_QUEUE_KEY, timeout=1 * 60)
        if blpop_val:
            key, job_str = blpop_val
            if pending_task_count >= 100:
                logging.warning('Skip the task for session ({}) because of too many pending tasks: {}'.format(
                    job_str, pending_task_count
                ))
                continue

            asyncio.create_task(handle_job_with_exception(job_str))
        else:
            logging.info('Live pulse from background worker. And number of active tasks: {}'
                         .format(pending_task_count))


async def handle_job_with_exception(job_str):
    global pending_task_count
    pending_task_count += 1
    try:
        start_ts = time.time()
        logging.debug('Start to process the job for {}'.format(job_str))
        await handle_job(job_str)
        logging.debug('Complete the job for {} after {} seconds'.format(job_str, time.time() - start_ts))

        pending_task_count -= 1
    except Exception as e:
        logging.exception(e, exc_info=True)
        logging.error('Failed to handle job for {}'.format(job_str))

        pending_task_count -= 1


async def handle_job(job_str):
    job_info = json.loads(job_str)
    session_id = job_info['session_id']
    proposed_names = job_info['names']

    gender, user_context = create_user_description(session_id)
    if not gender:
        logging.error("Missing gender information for {}".format(session_id))
        return

    # send requests in parallel
    group_size = 3
    request_num = (len(proposed_names) // group_size) + (1 if (len(proposed_names) % group_size) else 0)
    futures = []
    for i in range(request_num):
        task_names = proposed_names[(i * group_size):((i+1) * group_size)]
        futures.append(
            asyncio.create_task(
                send_one_request(session_id, gender, user_context, task_names))
        )
    await asyncio.gather(*futures, return_exceptions=True)

    # check failure and print message
    for i, future in enumerate(futures):
        if future.exception():
            logging.exception(future.exception(), exc_info=True)
            logging.error('Failed to handle proposed names for session {}: {}'.format(
                session_id, proposed_names[i * group_size:i * (group_size+1)]))


async def send_one_request(session_id, gender, user_context, proposed_names):
    name_descriptions = create_name_descriptions(gender, proposed_names)

    completion_text = '''
Write reasons for every name listed in below list about why the name is good for the user's newborn, based on the user provided preference, and
based on the descriptions of the names.
Please provide the reasons in a JSON format. 

Example response:
{{
  "name 1": "2~5 sentences about why this is a good name, based on the information provided by user and based on the description of the name.",
  "name 2": "2~5 sentences about why this is a good name, based on the information provided by user and based on the description of the name.",
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
    logging.debug('The response is {}'.format(parsed_rsp))

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
    asyncio.run(main_loop())
