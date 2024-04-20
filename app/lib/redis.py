"""
The general preferences are stored in a hash in Redis, and their values can be only overridden.
- map key: preference url parameter
- map value: serialized string value.

The name fondness is stored in their own hash in redis, which can be updated easily.
- map key: name
- map value: reason
"""
import json
import logging
import time
import os
import redis

from typing import Dict, List
import app.lib.name_pref as np
from app.lib.name_sentiments import UserSentiments

LAST_PREF_UPDATE_TS_KEY = 'last_pref_update_ts'

redis_host = os.environ.get("REDISHOST", "10.49.86.211")
redis_port = int(os.environ.get("REDISPORT", 6379))
redis_client = redis.StrictRedis(host=redis_host, port=redis_port, charset="utf-8", decode_responses=True)

TWO_WEEKS_IN_SECONDS = 2 * 7 * 24 * 60


def get_pref_key(session_id):
    return 'pref-{}'.format(session_id)


def get_last_pref_update_time(session_id) -> int:
    last_ts = redis_client.zscore(LAST_PREF_UPDATE_TS_KEY, session_id)
    return last_ts if last_ts else 0


def update_user_pref(session_id, user_prefs: Dict[str, np.PrefInterface], delete_before_updating=False):
    """
    Update the user preferences in Redis
    """
    if len(user_prefs) == 0:
        return True

    pref_dict = np.class_dict_to_str_dict(user_prefs)

    # add general preferences into redis pipeline
    pipeline = redis_client.pipeline()
    pref_key = get_pref_key(session_id)
    if delete_before_updating:
        pipeline.delete(pref_key)
    pipeline.hset(pref_key, mapping=pref_dict)
    # Add expiration the last update time
    pipeline.zadd(LAST_PREF_UPDATE_TS_KEY, mapping={session_id: int(time.time())})
    pipeline.execute()

    return True


def get_user_pref(session_id: str):
    """
    :return: a dictionary of preferences like
    {
        "gender": Gender_instance,
        "family_name": FamilyName_instance,
        ...
        "name_sentiments": NameSentiments_instance
    }
    """
    # fetch preferences
    pipeline = redis_client.pipeline()
    pref_key = get_pref_key(session_id)
    pipeline.hgetall(pref_key)
    responses = pipeline.execute()

    # convert general preferences
    raw_general_pref = responses[0]
    logging.debug('raw_general_pref from redis: {}'.format(raw_general_pref))
    all_prefs = np.str_dict_to_class_dict(raw_general_pref)

    return all_prefs


"""
Two data structures to maintain the sentiments
1. a hash map, with name as column key and a string of dictionary (including sentiment and also the reason/comment).
2. a sorted set to track the time when the name sentiment was added. This is used to prevent sending too much comment
   to chatgpt
"""


def get_user_sentiments_hash_key(session_id):
    return 'sentiment-{}'.format(session_id)


def get_user_sentiments_sset_key(session_id):
    return 'sentiment-sset-{}'.format(session_id)


def update_user_sentiments(session_id, name_sentiments: UserSentiments):
    """
    Update the user preferences in Redis
    """
    if not name_sentiments:
        return True

    # Collapse the second level dictionary into string, such that we can write it into redis
    cur_ts = int(time.time())
    name_sentiments_str = {}
    name_ts = {}
    for name, sentiments_dict in name_sentiments.get_native_val().items():
        name_sentiments_str[name] = json.dumps(sentiments_dict)
        name_ts[name] = cur_ts

    pipeline = redis_client.pipeline()

    name_sentiments_key = get_user_sentiments_hash_key(session_id)
    pipeline.hset(name_sentiments_key, mapping=name_sentiments_str)

    user_sentiments_sset_key = get_user_sentiments_sset_key(session_id)
    pipeline.zadd(user_sentiments_sset_key, name_ts)
    logging.debug(f'sorted set: {name_ts}')

    pipeline.execute()

    return True


def get_user_sentiments(session_id: str, max_count: int = 20) -> UserSentiments:
    """
    :return: NameSentiments_instance
    """
    # fetch preferences
    pipeline = redis_client.pipeline()
    user_sentiments_key = get_user_sentiments_hash_key(session_id)
    pipeline.hgetall(user_sentiments_key)
    user_sentiments_sset_key = get_user_sentiments_sset_key(session_id)
    pipeline.zrevrange(user_sentiments_sset_key, 0, max_count - 1)
    responses = pipeline.execute()

    # Parse and add NameSentiments preference
    raw_user_sentiments = responses[0]
    if not raw_user_sentiments:
        return UserSentiments.create_from_dict({})

    # Get the list of the latest names
    latest_names = responses[1]
    logging.debug(f'latest names from sorted set: {latest_names}')

    # Parse the dictionary string
    name_sentiments_dict = {}
    for name, dict_str in raw_user_sentiments.items():
        if name not in latest_names:
            continue

        name_sentiments_dict[name] = json.loads(dict_str)

    name_sentiments = UserSentiments.create_from_dict(name_sentiments_dict)
    return name_sentiments


def get_sentiment_for_name(session_id: str, name) -> Dict[str, str]:
    user_sentiments_key = get_user_sentiments_hash_key(session_id)
    sentiment_str = redis_client.hget(user_sentiments_key, name)
    if not sentiment_str:
        return {}

    return json.loads(sentiment_str)


"""
Track names displayed to a specific user, so we don't show the same names again
Use a user-specific sorted set which stores the name displayed before
"""
MAX_NUM_OF_TRACKED_NAMES = 80


def get_displayed_names_key(session_id):
    return 'proposal-{}'.format(session_id)


def append_displayed_names(session_id: str, names: List[str]):
    if not names:
        return

    pipeline = redis_client.pipeline()

    # trim the sorted set if needed
    proposal_key = get_displayed_names_key(session_id)
    displayed_names_count = redis_client.zcard(proposal_key)
    trim_count = displayed_names_count + len(names) - MAX_NUM_OF_TRACKED_NAMES
    if trim_count > 0:
        pipeline.zremrangebyrank(proposal_key, 0, trim_count)

    # put displayed names in a sorted set
    pipeline.expire(proposal_key, time=TWO_WEEKS_IN_SECONDS)
    cur_ts = int(time.time())
    pipeline.zadd(proposal_key, {x: cur_ts for x in names})

    pipeline.execute()


def get_displayed_names(session_id, max_count=100) -> List[str]:
    """
    :return: a list like ["Asher", "Caleb", "Ethan":]
    """
    proposal_key = get_displayed_names_key(session_id)
    return redis_client.zrevrange(proposal_key, 0, max_count)


"""
Write a job for background job to generate recommend reasons
- name proposal reason job: a shared list for the background job to fetch 
- name proposal reason: a user-specific hash with the name as key and with the reason as value
"""


PROPOSAL_REASON_JOB_QUEUE_KEY = 'reason_job_que'


def get_recommendation_reason_key(session_id):
    return 'proposal-reason-{}'.format(session_id)


def add_recommendation_job(session_id: str, proposed_names: List[str]):
    # filter out names which already had recommendation reason
    names_reasons = get_proposal_reasons(session_id)
    names_need_recommend_reason = []
    for name in proposed_names:
        if name in names_reasons:
            continue
        names_need_recommend_reason.append(name)

    if not names_need_recommend_reason:
        logging.debug('no recommend reason is required for session: {}'.format(session_id))
        return

    job_que_str = create_job_string(session_id, names_need_recommend_reason)
    pipeline = redis_client.pipeline()
    pipeline.rpush(PROPOSAL_REASON_JOB_QUEUE_KEY, job_que_str)
    pipeline.expire(PROPOSAL_REASON_JOB_QUEUE_KEY, time=TWO_WEEKS_IN_SECONDS)
    pipeline.execute()

    logging.debug('Writing job with session id {} to job queue: {}'.format(
        session_id, job_que_str))


def create_job_string(session_id: str, names: List[str]) -> str:
    output_dict = {
        'session_id': session_id,
        'names': names
    }
    return json.dumps(output_dict)


def update_name_proposal_reasons(session_id, proposal_reasons: Dict[str, str], clear_job_que=True):
    if not proposal_reasons:
        return

    pipeline = redis_client.pipeline()

    proposal_reason_key = get_recommendation_reason_key(session_id)
    pipeline.hset(proposal_reason_key, mapping=proposal_reasons)
    pipeline.expire(proposal_reason_key, time=TWO_WEEKS_IN_SECONDS)

    if clear_job_que:
        pipeline.lrem(PROPOSAL_REASON_JOB_QUEUE_KEY, 1, session_id)

    pipeline.execute()


def get_proposal_reason_for_name(session_id, name) -> str:
    proposal_key = get_recommendation_reason_key(session_id)
    return redis_client.hget(proposal_key, name)


def get_proposal_reasons(session_id) -> Dict[str, str]:
    proposal_key = get_recommendation_reason_key(session_id)
    return redis_client.hgetall(proposal_key)
