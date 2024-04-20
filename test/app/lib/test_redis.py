import json
import logging
import time
import unittest

import fakeredis

import app.lib.redis as redis_lib
from app.lib.name_sentiments import UserSentiments, Sentiment


class TestRedis(unittest.TestCase):
    def setUp(self) -> None:
        logging.getLogger().setLevel(logging.DEBUG)
        redis_lib.redis_client = fakeredis.FakeRedis(charset="utf-8", decode_responses=True)

    def test_add_job(self):
        redis_lib.add_recommendation_job('12345', ['Liam', 'Kaysen', 'Georgios', 'Jaydon', 'Jorge'])
        result = json.loads(redis_lib.redis_client.lpop(redis_lib.PROPOSAL_REASON_JOB_QUEUE_KEY))
        self.assertTrue(result['session_id'] == '12345')
        self.assertTrue(result['names'] == ['Liam', 'Kaysen', 'Georgios', 'Jaydon', 'Jorge'])

    def test_add_job_with_existing_recommendations(self):
        redis_lib.update_name_proposal_reasons('123456',
                                               {
                                                   'Liam': "A popular name",
                                                   'Jorge': 'A Cute name'
                                               })
        redis_lib.add_recommendation_job('123456', ['Liam', 'Kaysen', 'Georgios', 'Jaydon', 'Jorge'])
        result = json.loads(redis_lib.redis_client.lpop(redis_lib.PROPOSAL_REASON_JOB_QUEUE_KEY))
        self.assertTrue(result['session_id'] == '123456')
        self.assertTrue(result['names'] == ['Kaysen', 'Georgios', 'Jaydon'])

    def test_name_sentiments(self):
        session_id = '12345'
        sentiments = UserSentiments.create_from_dict({
            'Thomas': {'sentiment': 'liked', 'reason': 'abc'},
            'Ethan': {'sentiment': 'disliked'},
            'Katie': {'sentiment': 'saved', 'reason': 'abc'}
        })
        redis_lib.update_user_sentiments(session_id, sentiments)

        result = redis_lib.get_user_sentiments(session_id)
        result = result.get_val()
        self.assertTrue(len(result) == 3, 'Should get 3 results back but get {} result'.format(len(result)))

        self.assertTrue(result['Thomas']['sentiment'] == Sentiment.LIKED)
        self.assertTrue(result['Thomas']['reason'] == 'abc')
        self.assertTrue(result['Ethan']['sentiment'] == Sentiment.DISLIKED)
        self.assertTrue('reason' not in result['Ethan'], str(result['Ethan']))
        self.assertTrue(result['Katie']['sentiment'] == Sentiment.SAVED)

    def test_max_name_sentiments(self):
        session_id = '12345'
        sentiments1 = UserSentiments.create_from_dict({
            'Thomas': {'sentiment': 'liked', 'reason': 'abc'},
            'Ethan': {'sentiment': 'disliked'},
            'Katie': {'sentiment': 'saved', 'reason': 'abc'},
            'George': {'sentiment': 'liked', 'reason': 'abc'},
            'Gio': {'sentiment': 'liked', 'reason': 'abc'},
            'Jorge': {'sentiment': 'liked', 'reason': 'abc'},
        })
        redis_lib.update_user_sentiments(session_id, sentiments1)

        time.sleep(1)
        sentiments2 = UserSentiments.create_from_dict({
            'Ethan': {'sentiment': 'disliked'},     # repeating
            'Liam': {'sentiment': 'liked', 'reason': 'abc'},
            'Jaydon': {'sentiment': 'liked', 'reason': 'abc'},
            'Georgios': {'sentiment': 'liked', 'reason': 'abc'},
            'Kaysen': {'sentiment': 'liked', 'reason': 'abc'},
        })
        redis_lib.update_user_sentiments(session_id, sentiments2)

        result = redis_lib.get_user_sentiments(session_id, max_count=5)
        result = result.get_val()
        self.assertTrue(len(result) == 5,
                        'Should get 5 results back but get {} result: {}'.format(len(result), result))

        self.assertTrue('Ethan' in result)
        self.assertTrue('Liam' in result)
        self.assertTrue('Jaydon' in result)
        self.assertTrue('Georgios' in result)
        self.assertTrue('Kaysen' in result)
