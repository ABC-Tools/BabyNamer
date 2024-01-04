"""
The information scraped from https://nameberry.com/popular-names/nameberry/boys/all is not well organized,
because there is no easy to convert HTML (which is visual) into well-formatted text.
We use ChatGpt to convert fragmented text (usually in a list) into a paragraph.

Two input files:
- /Users/santan/Downloads/nameberry/parse_results.json
- /Users/santan/Downloads/babynames/babynames_meaning.json
"""
import logging

import openai
import os
import json

from app.lib.common import Gender, canonicalize_gender, canonicalize_name
import app.lib.name_statistics as ns

client = openai.OpenAI(api_key='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', max_retries=5)

intput_json_file1 = '/Users/santan/Downloads/nameberry/parse_results_new.json'
intput_json_file2 = '/Users/santan/Downloads/babynames/babynames_meaning.json'
# to make file appendable, we simply append records
output_json_file = '/Users/santan/gitspace/BabyNamer/app/data/name_meaning_new.txt'


def get_rewrite(d1, d2):
    user_prompt = """
Please use 1~5 sentences to rewrite the description for a name, based on the provide content as below.
The rewritten description will be used by the parents to choose names for their newborns. Therefore, please
be positive and get the parents excited!

Content:
{}
{}
    """.format(d1, d2)

    response = client.with_options(max_retries=1, timeout=60).chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {
                "role": "system",
                "content": "You are a good expert to write exciting descriptions for names, "
                           "to help parents to choose the best names for their newborns."
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ]
    )

    stop_reason = response.choices[0].finish_reason
    if stop_reason != 'stop':
        logging.warning('The stop reason is {}'.format(stop_reason))
    logging.debug("User prompt: {}".format(user_prompt))
    logging.debug('Total used tokens: {}'.format(response.usage.total_tokens))

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


def rewrite():
    input_dict1, input_dict2 = load_input_files()
    logging.info('length of names from nameberry: boy: {}, girl: {}'.format(
        len(input_dict1[Gender.BOY]), len(input_dict1[Gender.GIRL])))
    logging.info('length of names from babynames: boy: {}, girl: {}'.format(
        len(input_dict2[Gender.BOY]), len(input_dict2[Gender.GIRL])))
    existing_dict = loaded_list_to_dict(load_output_content())
    logging.info('length of existing_dict: {}'.format(len(existing_dict)))

    boy_names = set(input_dict1[Gender.BOY].keys()).union(
        input_dict2[Gender.BOY].keys()
    )
    girl_names = set(input_dict1[Gender.GIRL].keys()).union(
        input_dict2[Gender.GIRL].keys()
    )
    all_names = {
        Gender.BOY: list(boy_names),
        Gender.GIRL: list(girl_names)
    }

    count = 0
    total_tokens = 0
    cutoff = 200000
    with open(output_json_file, 'a') as fp:
        for gender in [Gender.BOY, Gender.GIRL]:
            for name in all_names[gender]:
                # skip if it has been rewritten before
                if (name, gender) in existing_dict:
                    logging.debug('Name {} {} has been rewritten before; skip '.format(name, gender))
                    continue

                # rewrite using GPT
                d1 = input_dict1[gender].get(name, '')
                d2 = input_dict2[gender].get(name, {}).get('description', '')
                description, used_token = get_rewrite(d1, d2)
                total_tokens += used_token
                logging.info('rewriting for {} {} using {} tokens: {}'.format(name, str(gender), used_token, description))

                # append to output file
                record = {name: {}}
                record[name]['description'] = description
                record[name]['gender'] = str(gender)
                fp.write(json.dumps(record) + "\n")

                count += 1
                if count >= cutoff:
                    break

                if count % 1000 == 0:
                    fp.flush()
                    os.fsync(fp)

            if count >= cutoff:
                break

    logging.info('used {} tokens'.format(total_tokens))
    logging.info("existing records: {}, new records: {}".format(len(existing_dict.keys()), count))


def load_input_files():
    with open(intput_json_file1, 'r') as fin1:
        input_list_1 = json.load(fin1)

    input_dict1 = {
        Gender.GIRL: {},
        Gender.BOY: {}
    }
    for record_dict in input_list_1:
        raw_name = list(record_dict.keys())[0]
        name = canonicalize_name(raw_name)
        gender = record_dict[raw_name]['gender']
        if gender:
            gender = canonicalize_gender(gender)
        else:
            gender = ns.NAME_STATISTICS.guess_gender(name)

        description = record_dict[raw_name]['description']
        input_dict1[gender][name] = description

    with open(intput_json_file2, 'r') as fin2:
        input_list_2 = json.load(fin2)

    input_dict2 = {
        Gender.GIRL: {},
        Gender.BOY: {}
    }
    for record in input_list_2:
        name = canonicalize_name(record['name'])
        raw_gender = record['gender']

        if raw_gender and raw_gender.lower() in ['neutral']:
            input_dict2[Gender.BOY][name] = {
                "origin": record["origin"],
                "short_meaning": record["short_meaning"],
                "description": record["long_meaning"]
            }
            input_dict2[Gender.GIRL][name] = {
                "origin": record["origin"],
                "short_meaning": record["short_meaning"],
                "description": record["long_meaning"]
            }
            continue

        if raw_gender:
            gender = canonicalize_gender(raw_gender)
        else:
            gender = ns.NAME_STATISTICS.guess_gender(name)
        input_dict2[gender][name] = {
            "origin": record["origin"],
            "short_meaning": record["short_meaning"],
            "description": record["long_meaning"]
        }

    return input_dict1, input_dict2


def loaded_list_to_dict(name_list):
    result = {}
    for name_dict in name_list:
        # there is one JSON dictionary in each element
        raw_name = list(name_dict.keys())[0]
        val_dict = name_dict[raw_name]

        name = canonicalize_name(raw_name)
        gender = canonicalize_gender(val_dict.get('gender', ''))

        # this is only for dedup; therefore the content does not matter
        result[(name, gender)] = {}

    return result
