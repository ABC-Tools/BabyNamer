import logging
import time
from typing import Dict

import openai

from app.lib.common import Gender
import app.openai_lib.prompt as prompt
import app.lib.name_pref as np
from app.lib.name_sentiments import UserSentiments

client = openai.OpenAI(api_key='')


def create_single_embedding(msg: str):
    start_ts = time.time()
    resp = client.with_options(max_retries=2, timeout=1.0)\
        .embeddings\
        .create(input=[msg], model="text-embedding-ada-002")
    logging.debug('Fetch embedding from OpenAI using {} seconds'.format(time.time() - start_ts))
    return resp.data[0].embedding


def create_embedding_from_pref_sentiments(gender: Gender,
                                          user_prefs_dict: Dict[str, np.PrefInterface],
                                          user_sentiments: UserSentiments):
    # create the paragraphs for user preferences and sentiments
    user_pref_str = prompt.create_text_from_user_pref(user_prefs_dict)
    user_sentiments_str = prompt.create_summary_of_user_sentiments(user_sentiments)
    text = """
Look for a name for a {gender} newborn, based on the following user preferences and sentiments.

{user_pref_str}
{user_sentiments_str}
    """.format(gender=str(gender), user_pref_str=user_pref_str, user_sentiments_str=user_sentiments_str)

    return create_single_embedding(text)
