import unittest

from app.lib.name_sentiments import UserSentiments
from app.openai_lib import chat_completion as cc
from app.lib import name_pref as np


class TestChatCompletion(unittest.TestCase):

    def test_check_proposed_names(self):
        prefs = {
            np.OtherPref.get_url_param_name():
                np.OtherPref.create("Please suggest names with more than 6 letters")
        }

        sentiments_dict = {
            'George': {
                "sentiment": 'disliked',
                "reason": "Please suggest name starting with letter M"
            }
        }
        sentiments = UserSentiments.create_from_dict(sentiments_dict)

        result = cc.check_proposed_names(
            ["Ethan", "Madison", "Maxwell", "Max"],
            prefs,
            sentiments,
            max_count=20
        )
        self.assertTrue(result == ["Madison", "Maxwell"], "the actual resul is {}".format(result))

