"""
The general preferences are stored in a hash in Redis, and their values can be only overridden.
- map key: preference url parameter
- map value: serialized string value.

The name fondness is stored in their own hash in redis, which can be updated easily.
- map key: name
- map value: reason
"""
import json
import time
import os
import redis

from typing import Dict
import app.lib.name_pref as np

LAST_PREF_UPDATE_TS_KEY = 'last_pref_update_ts'
LAST_PROPOSAL_TS_KEY = 'last_proposal_update_ts'

redis_host = os.environ.get("REDISHOST", "10.49.86.211")
redis_port = int(os.environ.get("REDISPORT", 6379))
redis_client = redis.StrictRedis(host=redis_host, port=redis_port, charset="utf-8", decode_responses=True)


def update_user_pref(session_id, user_prefs: Dict[str, np.PrefInterface]):
    """
    Update the user preferences in Redis
    """
    if len(user_prefs) == 0:
        return True

    # TODO: detect the changes that liked names are changed to disliked/saved and vice versa
    # TODO: read redis first, and write redis only if there is a diff

    pref_dict = np.class_dict_to_str_dict(user_prefs)

    # add general preferences into redis pipeline
    pipeline = redis_client.pipeline()
    pref_key = get_pref_key(session_id)
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
    all_prefs = np.str_dict_to_class_dict(raw_general_pref)

    return all_prefs


def update_user_sentiments(session_id, name_sentiments: np.UserSentiments):
    """
    Update the user preferences in Redis
    """
    if not name_sentiments:
        return True

    # TODO: detect the changes that liked names are changed to disliked/saved and vice versa
    # TODO: read redis first, and write redis only if there is a diff

    name_sentiments_key = get_user_sentiments_key(session_id)
    # Collapse the second level dictionary into string, such that we can write it into redis
    name_sentiments_str = {}
    for name, sentiments_dict in name_sentiments.get_native_val().items():
        name_sentiments_str[name] = json.dumps(sentiments_dict)

    pipeline = redis_client.pipeline()
    pipeline.hset(name_sentiments_key, mapping=name_sentiments_str)
    # Add expiration the last update time
    pipeline.zadd(LAST_PREF_UPDATE_TS_KEY, mapping={session_id: int(time.time())})
    pipeline.execute()

    return True


def get_user_sentiments(session_id: str) -> np.UserSentiments:
    """
    :return: NameSentiments_instance
    """
    # fetch preferences
    pipeline = redis_client.pipeline()
    user_sentiments_key = get_user_sentiments_key(session_id)
    pipeline.hgetall(user_sentiments_key)

    responses = pipeline.execute()

    # Parse and add NameSentiments preference
    raw_user_sentiments = responses[0]
    if not raw_user_sentiments:
        return None

    # Parse the dictionary string
    name_sentiments_dict = {}
    for name, dict_str in raw_user_sentiments.items():
        name_sentiments_dict[name] = json.loads(dict_str)

    name_sentiments = np.UserSentiments.create_from_dict(name_sentiments_dict)
    return name_sentiments


def get_sentiment_for_name(session_id: str, name) -> Dict[str, str]:
    user_sentiments_key = get_user_sentiments_key(session_id)
    sentiment_str = redis_client.hget(user_sentiments_key, name)
    if not sentiment_str:
        return {}

    return json.loads(sentiment_str)


def update_name_proposals(session_id, proposals: Dict[str, str]):
    pipeline = redis_client.pipeline()

    proposal_key = get_name_proposals_key(session_id)
    pipeline.hset(proposal_key, mapping=proposals)
    pipeline.zadd(LAST_PROPOSAL_TS_KEY, mapping={session_id: int(time.time())})

    pipeline.execute()


def get_name_proposals(session_id) -> Dict[str, str]:
    """
    :return: a dictionary like
    {
        "Asher": "Asher is a modern and trendy name...",
        "Caleb": "Caleb is a stylish and contemporary ...",
        "Ethan": "Ethan is..."
    }
    """
    proposal_key = get_name_proposals_key(session_id)
    return redis_client.hgetall(proposal_key)


def get_proposal_for_name(session_id, name) -> str:
    proposal_key = get_name_proposals_key(session_id)
    return redis_client.hget(proposal_key, name)


def get_last_pref_update_time(session_id) -> int:
    last_ts = redis_client.zscore(LAST_PREF_UPDATE_TS_KEY, session_id)
    return last_ts if last_ts else 0


def get_last_proposal_time(session_id) -> int:
    last_ts = redis_client.zscore(LAST_PROPOSAL_TS_KEY, session_id)
    return last_ts if last_ts else 0


def get_pref_key(session_id):
    return 'pref-{}'.format(session_id)


def get_user_sentiments_key(session_id):
    return 'user-sentiments-{}'.format(session_id)


def get_name_proposals_key(session_id):
    return 'name-proposals-{}'.format(session_id)
