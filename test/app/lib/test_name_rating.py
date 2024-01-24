import unittest

import app.lib.name_rating as nr
from app.lib.common import Gender


class TestNameRating(unittest.TestCase):

    def test_get_feature_scores(self):
        feature_scores = nr.NAME_RATING.get_feature_scores('Kaitlyn', 'girl')
        self.assertTrue('style_option' in feature_scores)
        self.assertTrue(feature_scores['style_option']['characteristics'] == ['Classic', 'Modern'])
        self.assertTrue(feature_scores['style_option']['score'] == 10)

        self.assertTrue('maturity_option' in feature_scores)
        self.assertTrue('formality_option' in feature_scores)
        self.assertTrue('class_option' in feature_scores)
        self.assertTrue('environment_option' in feature_scores)
        self.assertTrue('moral_option' in feature_scores)
        self.assertTrue('strength_option' in feature_scores)
        self.assertTrue('texture_option' in feature_scores)
        self.assertTrue('creativity_option' in feature_scores)
        self.assertTrue('complexity_option' in feature_scores)
        self.assertTrue('tone_option' in feature_scores)
        self.assertTrue('intellectual_option' in feature_scores)

        self.assertTrue('overall_option' not in feature_scores)
        self.assertTrue('gender_option' not in feature_scores)

    def test_suggest(self):
        option = {'style_option': 'Classic', 'texture_option': 'Refined'}

        result = nr.NAME_RATING.suggest('boy', option, count=10)
        print('Suggested names: {}'.format(result))

        self.assertTrue(all(0.0 <= x <= 1.0 for x in result.values()),
                        'Not all embedding distance is within 0 and 1: {}'.format(result))
        self.assertTrue(all(x > 0.9 for x in result.values()),
                        'The cosine similarity score is less than 0.6: {}'.format(result))

        first_name = next(iter(result.keys()))
        classic_percentile = nr.NAME_RATING._get_percentile(
            Gender.BOY, first_name, 'style_option', "Classic", "Modern", 'Classic')
        self.assertTrue(classic_percentile < 0.1,
                        'Classic score percentile for {} is not less than 0.1: {}'.format(
                            first_name, classic_percentile))

        refined_percentile = nr.NAME_RATING._get_percentile(
            Gender.BOY, first_name, 'texture_option', "Refined", "Rough", 'Refined')
        self.assertTrue(refined_percentile < 0.1,
                        'Refined score percentile for {} is not less than 0.1: {}'.format(
                            first_name, refined_percentile))

        feature_percentiles = nr.NAME_RATING.get_feature_percentiles(first_name, Gender.BOY)
        self.assertTrue(feature_percentiles['style_option']['Classic'][1] == 'top',
                        'Classic score percentile for {} is not top: {}'.format(
                            first_name, feature_percentiles['style_option']['Classic']))
        self.assertTrue(feature_percentiles['texture_option']['Refined'][1] == 'top',
                        'Refined score percentile for {} is not top: {}'.format(
                            first_name, feature_percentiles['texture_option']['Refined']))
