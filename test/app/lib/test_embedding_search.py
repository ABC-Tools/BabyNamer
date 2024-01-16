import json
import unittest
import os

import app.lib.embedding_search as es
from app.lib.common import Gender
from test.test_lib import get_test_root_dir
import app.lib.name_meaning as nm


class TestFaissSearch(unittest.TestCase):

    def test_embedding_search(self):
        filename = os.path.join(get_test_root_dir(), 'app', 'lib', 'data', 'eb_i_like_french_name.json')
        with open(filename, 'r') as fp:
            eb = json.load(fp)

        result = es.FAISS_SEARCH.search_with_embedding(Gender.BOY, eb)
        # print('search result: {}'.format(result))
        self.assertTrue(all(0.0 <= x <= 1.0 for x in result.values()),
                        'Not all embedding distance is within 0 and 1: {}'.format(result))
        self.assertTrue(all(x > 0.7 for x in result.values()),
                        'The cosine similarity score is less than 0.6: {}'.format(result))

        first_key = next(iter(result.keys()))
        description = nm.NAME_MEANING.get(first_key, 'boy')
        # print('description: {}'.format(description))
        self.assertTrue('France' in description or 'French' in description,
                        'The description has no keyword of either France or French: {}'.format(description))


if __name__ == '__main__':
    unittest.main()
