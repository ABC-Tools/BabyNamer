import json
import logging
import os
import unittest
from unittest.mock import patch, MagicMock

import fakeredis

import app.lib.redis as redis_lib
import app.procedure.suggest_names as sn
import app.procedure.name_proposer as n_proposer
import app.lib.name_pref as np
from app.lib.common import Gender
from test.test_lib import get_test_root_dir


class TestSuggestNames(unittest.TestCase):
    def setUp(self) -> None:
        logging.getLogger().setLevel(logging.DEBUG)
        redis_lib.redis_client = fakeredis.FakeRedis(charset="utf-8", decode_responses=True)

    def test_suggest_names_no_pref(self):
        names = sn.suggest('12345', Gender.BOY)
        self.assertTrue(names[0] == 'Liam', names)
        self.assertTrue(names[1] == 'Noah', names)

        redis_names = redis_lib.get_displayed_names('12345')
        self.assertTrue('Liam' in redis_names, redis_names)
        self.assertTrue('Noah' in redis_names, redis_names)

    def test_suggest_names_sibling_name(self):
        sibling_name_pref = np.SiblingNames.create('["Kaitlyn", "Kayden"]')
        redis_lib.update_user_pref('112233', {np.SiblingNames.get_url_param_name(): sibling_name_pref})

        names = sn.suggest('112233', Gender.BOY)
        self.assertTrue('Liam' in names)
        self.assertTrue('Kaden' in names)

        # suggestion from similar names
        reason = redis_lib.get_proposal_reason_for_name('112233', 'Kaden')
        self.assertTrue('complements the sibling\'s names' in reason, 'wrong recommendation reason: {}'.format(reason))

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

    @patch('app.openai_lib.chat_completion.check_proposed_names')
    def test_filter_out_displayed_names(self, check_proposed_names_mock):
        def no_op_func(filtered_names, user_prefs_dict, user_sentiments, max_count):
            return filtered_names[:max_count]
        check_proposed_names_mock.side_effect = no_op_func
        option = {'style_option': 'Classic', 'texture_option': 'Rough'}
        style = np.StyleChoice.create(option['style_option'])
        texture = np.TextureChoice.create(option['texture_option'])

        sibling_name = np.SiblingNames.create('["Liam"]')
        redis_lib.update_user_pref('654321',
                                   {np.StyleChoice.get_url_param_name(): style,
                                    np.TextureChoice.get_url_param_name(): texture,
                                    np.SiblingNames.get_url_param_name(): sibling_name})
        redis_lib.append_displayed_names('654321', ['Ragnar', 'William'])

        names = sn.suggest('654321', Gender.BOY, filter_displayed_names=True, count=10)
        self.assertTrue('Liam' not in names)
        self.assertTrue('Ragnar' not in names)
        self.assertTrue('Joab' in names)

    @patch('app.openai_lib.chat_completion.check_proposed_names')
    def test_suggest_name_from_text(self, check_proposed_names_mock):
        def no_op_func(filtered_names, user_prefs_dict, user_sentiments, max_count):
            return filtered_names[:max_count]
        check_proposed_names_mock.side_effect = no_op_func

        filename = os.path.join(get_test_root_dir(), 'app', 'lib', 'data', 'eb_i_like_french_name.json')
        with open(filename, 'r') as fp:
            eb = json.load(fp)

        with patch('app.openai_lib.embedding_client.client', spec=True) as mock_client:
            with_options_mock = MagicMock()
            mock_client.with_options.return_value = with_options_mock

            resp_mock = MagicMock()
            with_options_mock.embeddings.create.return_value = resp_mock

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
            args, kwargs = with_options_mock.embeddings.create.call_args
            self.assertTrue('I like France' in kwargs['input'][0],
                            'could not locate the info provide by user: "{}" in prompt: {}'.
                            format('I like France', kwargs['input'][0]))
            self.assertTrue('disliked the name of Jasper' in kwargs['input'][0])
            self.assertTrue('saved the name of Jayden as a favorite' in kwargs['input'][0])

            self.assertTrue('Liam' in names)
            self.assertTrue('Jules' in names)

            # suggestion from text
            reason = redis_lib.get_proposal_reason_for_name('67890', 'Jules')
            self.assertTrue(not reason)

    @patch('app.openai_lib.chat_completion.check_proposed_names')
    def test_filter_out_name_from_sentiments(self, check_proposed_names_mock):
        def no_op_func(filtered_names, user_prefs_dict, user_sentiments, max_count):
            return filtered_names[:max_count]
        check_proposed_names_mock.side_effect = no_op_func

        filename = os.path.join(get_test_root_dir(), 'app', 'lib', 'data', 'eb_i_like_french_name.json')
        with open(filename, 'r') as fp:
            eb = json.load(fp)

        with patch('app.openai_lib.embedding_client.client', spec=True) as mock_client:
            with_options_mock = MagicMock()
            mock_client.with_options.return_value = with_options_mock

            resp_mock = MagicMock()
            with_options_mock.embeddings.create.return_value = resp_mock

            resp_mock.data = [MagicMock()]
            resp_mock.data[0].embedding = eb

            other_pref = np.OtherPref.create('I like France')
            sibling_pref = np.SiblingNames.create('["Francis"]')
            redis_lib.update_user_pref('67891',
                                       {np.OtherPref.get_url_param_name(): other_pref,
                                        np.SiblingNames.get_url_param_name(): sibling_pref})

            sentiments = np.UserSentiments.create(
                json.dumps(
                    {
                        "Liam": {"sentiment": "liked", "reason": "sounds good"},
                        "Pascal": {"sentiment": "disliked", "reason": "my neighbor uses this name"},
                        "Claude": {"sentiment": "saved"}
                    }
                )
            )
            redis_lib.update_user_sentiments('67891', sentiments)

            names = sn.suggest('67891', Gender.BOY)
            print('Suggested names: {}'.format(names))

            self.assertTrue('Liam' not in names)
            self.assertTrue('Jules' in names)
            self.assertTrue('Pascal' not in names)
            self.assertTrue('Claude' not in names)
            self.assertTrue('Francis' not in names)

    def test_suggest_name_using_sibling_names(self):
        name_scores = n_proposer.suggest_name_using_sibling_names(Gender.BOY, ['Kaitlyn'])
        self.assertTrue(all(x > 0.7 for x in name_scores.values()),
                        'The  similarity score is less than 0.6: {}'.format(name_scores))

