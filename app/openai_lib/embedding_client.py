from typing import Dict

import openai

from app.lib.common import Gender
import app.openai_lib.prompt as prompt
import app.lib.name_pref as np

client = openai.OpenAI(api_key='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')


def create_single_embedding(msg: str):
    resp = client.with_options(max_retries=2, timeout=1.0)\
        .embeddings\
        .create(input=[msg], model="text-embedding-ada-002")
    return resp.data[0].embedding


def creat_embedding_from_pref_sentiments(gender: Gender,
                                         user_prefs_dict: Dict[str, np.PrefInterface],
                                         user_sentiments: np.UserSentiments):
    # create the paragraphs for user preferences and sentiments
    user_pref_str = prompt.create_text_from_user_pref(user_prefs_dict)
    user_sentiments_str = prompt.create_text_from_user_sentiments(user_sentiments)
    text = """
Look for a name for a {gender} newborn, based on the following user preferences and sentiments.

{user_pref_str}
{user_sentiments_str}
    """.format(gender=str(gender), user_pref_str=user_pref_str, user_sentiments_str=user_sentiments_str)

    return create_single_embedding(text)
