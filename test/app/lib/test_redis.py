import json
import logging
import unittest

import fakeredis

import app.lib.redis as redis_lib


class TestRedis(unittest.TestCase):
    def setUp(self) -> None:
        logging.getLogger().setLevel(logging.DEBUG)
        redis_lib.redis_client = fakeredis.FakeRedis(charset="utf-8", decode_responses=True)

    def test_add_job(self):
        redis_lib.add_job('12345', ['Liam', 'Kaysen', 'Georgios', 'Jaydon', 'Jorge'])
        result = json.loads(redis_lib.redis_client.lpop(redis_lib.PROPOSAL_REASON_JOB_QUEUE_KEY))
        self.assertTrue(result['session_id'] == '12345')
        self.assertTrue(result['names'] == ['Liam', 'Kaysen', 'Georgios', 'Jaydon', 'Jorge'])

    def test_add_job_with_existing_recommendations(self):
        redis_lib.update_name_proposal_reasons('123456',
                                               {
                                                   'Liam': "A popular name",
                                                   'Jorge': 'A Cute name'
                                               })
        redis_lib.add_job('123456', ['Liam', 'Kaysen', 'Georgios', 'Jaydon', 'Jorge'])
        result = json.loads(redis_lib.redis_client.lpop(redis_lib.PROPOSAL_REASON_JOB_QUEUE_KEY))
        self.assertTrue(result['session_id'] == '123456')
        self.assertTrue(result['names'] == ['Kaysen', 'Georgios', 'Jaydon'])
