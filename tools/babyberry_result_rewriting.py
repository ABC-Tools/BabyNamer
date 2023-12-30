"""
The information scraped from https://nameberry.com/popular-names/nameberry/boys/all is not well organized,
because there is no easy to convert HTML (which is visual) into well-formatted text.
We use ChatGpt to convert fragmented text (usually in a list) into a paragraph.

Two input files:
- /Users/santan/Downloads/nameberry/parse_results.json
- /Users/santan/Downloads/babynames/babynames_meaning.json
"""

import openai
import os
import json

import app.lib.common as common_lib
from app.lib.common import fprint

client = openai.OpenAI(api_key='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')

intput_json_file = '/Users/santan/Downloads/nameberry/parse_results.json'
# to make file appendable, we simply append records
output_json_file = '/Users/santan/gitspace/BabyNamer/app/static/name_meaning.txt'


def get_rewrite(data_dict):
    user_prompt = """
JSON: {}.
Now please rewrite a paragraph about the meaning and the origin of the baby name, 
based on above JSON content. If the JSON content mentions gender, please
respect it. Otherwise, please make a best guess of the gender.
    """.format(json.dumps(data_dict))

    response = client.with_options(max_retries=1, timeout=60).chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {
                "role": "system",
                "content": "You are a good assistant to rewrite the meaning and the origin of baby names, "
                           "based on provided content."
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ]
    )

    stop_reason = response.choices[0].finish_reason
    if stop_reason != 'stop':
        fprint('The stop reason is {}'.format(stop_reason))
    fprint("User prompt: {}".format(user_prompt))
    fprint('Total used tokens: {}'.format(response.usage.total_tokens))

    return response.choices[0].message.content, response.usage.total_tokens


def load_output_content():
    result = []
    if not os.path.isfile(output_json_file):
        return result

    with open(output_json_file, 'r') as fp:
        for line in fp:
            line = line.strip()
            content_dict = json.loads(line)

            result.append(content_dict)

    return result


def loaded_list_to_dict(name_list):
    result = {}
    for name_dict in name_list:
        # there is one JSON dictionary in each element
        raw_name = list(name_dict.keys())[0]
        val_dict = name_dict[raw_name]

        name = common_lib.canonicalize_name(raw_name)
        gender = common_lib.canonicalize_gender(val_dict.get_yearly_trend('gender', ''))

        # this is only for dedup; therefore the content does not matter
        result[(name, gender)] = {}

    return result


def load_input_content():
    with open(intput_json_file, 'r') as fp:
        return json.load(fp)


def rewrite_babyberry_data():
    input_list = load_input_content()
    fprint('length of input_list: {}'.format(len(input_list)))
    existing_dict = loaded_list_to_dict(load_output_content())
    fprint('length of existing_dict: {}'.format(len(existing_dict)))

    count = 0
    total_tokens = 0
    with open(output_json_file, 'a') as fp:
        for input_dict in input_list:
            # there is one JSON dictionary in each element
            raw_name = list(input_dict.keys())[0]
            val_dict = input_dict[raw_name]

            name = common_lib.canonicalize_name(raw_name)
            raw_gender = val_dict.get_yearly_trend('gender', '')
            gender = common_lib.canonicalize_gender(raw_gender)

            # skip if it has been rewritten before
            if (name, gender) in existing_dict:
                fprint('Name {} {} has been rewritten before; skip '.format(name, gender))
                continue
            else:
                fprint('Name {} {} is being rewritten '.format(name, gender))

            # rewrite using GPT
            description, used_token = get_rewrite(input_dict)
            total_tokens += used_token
            fprint('rewriting for {} {} using {} tokens: {}'.format(name, str(gender), used_token, description))

            # append to output file
            record = {name: {}}
            record[name]['description'] = description
            if gender:
                record[name]['gender'] = str(gender)
            fp.write(json.dumps(record) + "\n")

            count += 1
            if count >= 1000:
                fprint('used {} tokens'.format(used_token))
                fprint("existing records: {}, new records: {}".format(len(existing_dict.keys()), count))
                break

            if count % 100 == 0:
                fprint("Flush disk")
                fp.flush()
                os.fsync(fp)
