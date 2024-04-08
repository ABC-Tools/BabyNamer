import logging
import os
import redis

from app.lib.common import Gender

redis_host = os.environ.get("REDISHOST", "10.49.86.211")
redis_port = int(os.environ.get("REDISPORT", 6379))
redis_client = redis.StrictRedis(host=redis_host, port=redis_port, charset="utf-8", decode_responses=True)


def create_consolidated_facts():
    import app.lib.name_meaning as nm
    import app.lib.origin_and_short_meaning as osm
    import app.lib.similar_names as sn
    import app.lib.name_statistics as ns

    gpt_meaning_origin = get_fetched_names_meaning_origin()

    for gender in [Gender.BOY, Gender.GIRL]:
        for name in ns.NAME_STATISTICS.get_popular_names(gender, count=8000):
            consolidated_facts = {}

            meaning = nm.NAME_MEANING.get(name, gender).strip()
            origin, short_meaning = osm.ORIGIN_SHORT_MEANING.get(name, gender)
            origin = origin.strip()
            short_meaning = short_meaning.strip()

            if not meaning:
                meaning = gpt_meaning_origin[str[gender]].get(name, {}).get("long meaning", '')
                logging.debug('name {} Using gpt long meaning: {}'.format(name, meaning))
            if not origin:
                origin = gpt_meaning_origin[str[gender]].get(name, {}).get("origin", '')
                logging.debug('name {} Using gpt origin: {}'.format(name, origin))
            if not short_meaning:
                short_meaning = gpt_meaning_origin[str[gender]].get(name, {}).get("short meaning", '')
                logging.debug('name {} Using gpt short meaning: {}'.format(name, short_meaning))

            if not meaning and not origin and not short_meaning:
                logging.debug('name {} is empty; skip'.format(name)
                continue
