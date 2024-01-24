import json
import logging
import os
import unittest
from unittest.mock import patch, MagicMock

import fakeredis

import app.lib.redis as redis_lib
import app.openai_lib.embedding_client
import app.procedure.suggest_names as sn
import app.lib.name_pref as np
from app.lib.common import Gender
from test.test_lib import get_test_root_dir


class TestSuggestNames(unittest.TestCase):
    def setUp(self) -> None:
        logging.getLogger().setLevel(logging.DEBUG)
        redis_lib.redis_client = fakeredis.FakeRedis(charset="utf-8", decode_responses=True)

    def test_suggest_names_no_pref(self):
        names = sn.suggest('12345', Gender.BOY)
        self.assertTrue(names[0] == 'Liam')
        self.assertTrue(names[1] == 'Noah')

        redis_names = redis_lib.get_name_proposals('12345')
        self.assertTrue(redis_names[0] == 'Liam')
        self.assertTrue(redis_names[1] == 'Noah')

        reason = redis_lib.get_proposal_reason_for_name('12345', 'Liam')
        self.assertTrue('ranked #1' in reason, 'wrong recommendation reason: {}'.format(reason))

    def test_suggest_names_sibling_name(self):
        sibling_name_pref = np.SiblingNames.create('["Kaitlyn", "Kayden"]')
        redis_lib.update_user_pref('112233', {np.SiblingNames.get_url_param_name(): sibling_name_pref})

        names = sn.suggest('112233', Gender.BOY)
        self.assertTrue('Liam' in names)
        self.assertTrue('Kaden' in names)

        # suggestion from top names
        reason = redis_lib.get_proposal_reason_for_name('112233', 'Liam')
        self.assertTrue('ranked #1' in reason, 'wrong recommendation reason: {}'.format(reason))

        # suggestion from similar names
        reason = redis_lib.get_proposal_reason_for_name('112233', 'Kaden')
        self.assertTrue('similar to the sibling names' in reason, 'wrong recommendation reason: {}'.format(reason))

    def test_suggest_names_options(self):
        option = {'style_option': 'Classic', 'texture_option': 'Rough'}
        style = np.StyleChoice.create(option['style_option'])
        texture = np.TextureChoice.create(option['texture_option'])

        redis_lib.update_user_pref('654321',
                                   {np.StyleChoice.get_url_param_name(): style,
                                    np.TextureChoice.get_url_param_name(): texture})

        names = sn.suggest('654321', Gender.BOY, count=10)
        self.assertTrue('Liam' in names)
        self.assertTrue('Ragnar' in names)

        # suggestion from top names
        reason = redis_lib.get_proposal_reason_for_name('654321', 'Liam')
        self.assertTrue('ranked #1' in reason, 'wrong recommendation reason: {}'.format(reason))

        # suggestion from similar names
        reason = redis_lib.get_proposal_reason_for_name('654321', 'Ragnar')
        self.assertTrue('the top 1% Classic name' in reason, 'wrong recommendation reason: {}'.format(reason))
        self.assertTrue('the top 1% Rough name' in reason, 'wrong recommendation reason: {}'.format(reason))

    def test_filter_out_name(self):
        option = {'style_option': 'Classic', 'texture_option': 'Rough'}
        style = np.StyleChoice.create(option['style_option'])
        texture = np.TextureChoice.create(option['texture_option'])

        sibling_name = np.SiblingNames.create('["Liam"]')
        redis_lib.update_user_pref('654321',
                                   {np.StyleChoice.get_url_param_name(): style,
                                    np.TextureChoice.get_url_param_name(): texture,
                                    np.SiblingNames.get_url_param_name(): sibling_name})

        names = sn.suggest('654321', Gender.BOY, count=10)
        self.assertTrue('Liam' not in names)
        self.assertTrue('Ragnar' in names)

    def test_suggest_name_from_text(self):
        filename = os.path.join(get_test_root_dir(), 'app', 'lib', 'data', 'eb_i_like_french_name.json')
        with open(filename, 'r') as fp:
            eb = json.load(fp)

        with patch('app.openai_lib.embedding_client.client', spec=True) as mock_client:
            mock_client.embeddings = MagicMock()

            resp_mock = MagicMock()
            mock_client.embeddings.create.return_value = resp_mock

            resp_mock.data = [MagicMock()]
            resp_mock.data[0].embedding = eb

            other_pref = np.OtherPref.create('I like France')
            redis_lib.update_user_pref('67890', {np.OtherPref.get_url_param_name(): other_pref})

            sentiments = np.UserSentiments.create(
                json.dumps(
                    {
                        "Aron": {"sentiment": "liked", "reason": "sounds good"},
                        "Jasper": {"sentiment": "disliked", "reason": "my neighbor uses this name"},
                        "Jayden": {"sentiment": "saved"}
                    }
                )
            )
            redis_lib.update_user_sentiments('67890', sentiments)

            names = sn.suggest('67890', Gender.BOY)
            args, kwargs = mock_client.embeddings.create.call_args
            self.assertTrue('I like France' in kwargs['input'][0],
                            'could not locate the info provide by user: "{}" in prompt: {}'.
                            format('I like France', kwargs['input'][0]))
            self.assertTrue('disliked the name of Jasper' in kwargs['input'][0])
            self.assertTrue('saved the name of Jayden as a favorite' in kwargs['input'][0])

            self.assertTrue('Liam' in names)
            self.assertTrue('Jules' in names)

            # suggestion from top names
            reason = redis_lib.get_proposal_reason_for_name('67890', 'Liam')
            self.assertTrue('ranked #1' in reason, 'wrong recommendation reason: {}'.format(reason))

            # suggestion from text
            reason = redis_lib.get_proposal_reason_for_name('67890', 'Jules')
            self.assertTrue(not reason)

    def test_name_letter_similarity(self):
        score = sn.letter_wise_similarity('Kaitlyn', 'Katie')
        self.assertTrue(score >= 0.8,
                        'The similarity between Katie and Kaitlin is {}'.format(score))

        score = sn.letter_wise_similarity('Kaitlyn', 'Kaitlin')
        self.assertTrue(score > 0.8,
                        'The similarity between Katie and Kaitlin is {}'.format(score))

        score = sn.letter_wise_similarity('Kaitlyn', 'Katelyn')
        self.assertTrue(score > 0.8,
                        'The similarity between Katie and Katelyn is {}'.format(score))

        score = sn.letter_wise_similarity('Kaitlyn', 'Caitlin')
        self.assertTrue(score > 0.7,
                        'The similarity between Katie and Caitlin is {}'.format(score))

        score = sn.letter_wise_similarity('Kaitlyn', 'Kailyn')
        self.assertTrue(score > 0.8,
                        'The similarity between Katie and Kailyn is {}'.format(score))

    def test_suggest_name_using_sibling_names(self):
        name_scores = sn.suggest_name_using_sibling_names(Gender.BOY, ['Kaitlyn'])
        self.assertTrue(all(x > 0.7 for x in name_scores.values()),
                        'The  similarity score is less than 0.6: {}'.format(name_scores))

