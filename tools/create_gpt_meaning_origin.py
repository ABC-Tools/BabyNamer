import json
import logging
import os.path
from typing import List

import openai

from app.lib.common import Gender, canonicalize_name

gpt_result_file_path_template = '/Users/santan/gitspace/BabyNamer/tools/tmp/names_meaning_origin_gpt_{gender}.json'
names_without_meaning_origin_file_path = '/Users/santan/gitspace/BabyNamer/tools/tmp/names_without_meaning_origin.json'
client = openai.OpenAI(api_key='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', max_retries=5)
consumed_tokens = 0


def get_names_without_meaning_origin():
    if os.path.isfile(names_without_meaning_origin_file_path):
        with open(names_without_meaning_origin_file_path, 'r') as fp:
            return json.load(fp)

    import app.lib.name_statistics as ns
    import app.lib.name_meaning as nm
    import app.lib.origin_and_short_meaning as osm

    result = {
        str(Gender.BOY): [],
        str(Gender.GIRL): []
    }

    for gender in [Gender.BOY, Gender.GIRL]:
        for name in ns.NAME_STATISTICS.get_popular_names(gender, count=8000):
            meaning = nm.NAME_MEANING.get(name, gender).strip()
            origin, short_meaning = osm.ORIGIN_SHORT_MEANING.get(name, gender)
            origin = origin.strip()
            short_meaning = short_meaning.strip()
            if not meaning or not origin or not short_meaning:
                result[str(gender)].append(name)

    with open(names_without_meaning_origin_file_path, 'w') as fp:
        json.dump(result, fp)


def fetch_meaning_origin(gender: str, names: List[str]):
    global consumed_tokens

    user_prompt = """
You are a good assistant to help newborn's parents to understand the origin and the meaning of {gender} names.
For each given name in the list of names, write its origin, a short meaning with a few words, and a long meaning with
a few sentences. For the long meaning, please be positive and get the parents excited!

The list of names: {name_list}.

Please return the result in Json format, like
{{
    "name1": {{
        "origin": "...",
        "short meaning": "...",
        "long meaning": "..."
    }}
}}

If you are not sure about the origin or the short meaning or the long meaning, please leave it empty.
""".format(gender=gender, name_list=",".join(names))
    logging.debug("User prompt: {}".format(user_prompt))

    response = client.with_options(max_retries=1, timeout=60).chat.completions.create(
        # model="gpt-3.5-turbo-1106",
        model="gpt-4-1106-preview",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "You are a good assistant to help newborn's parents to understand the origin and "
                           "the meaning of names."
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
    logging.info('ChatGPT raw output: {}'.format(response.choices[0].message.content))
    consumed_tokens += response.usage.total_tokens
    logging.debug('Total used tokens: {} and accumulated consumed tokens: {}'.format(
        response.usage.total_tokens, consumed_tokens))

    try:
        parsed_rsp = json.loads(response.choices[0].message.content)
    except json.decoder.JSONDecodeError as e:
        logging.exception(e, exc_info=True)
        logging.info("Failed to parse the GPT result of {}; skip".format(names))
        return {}

    return parsed_rsp


def get_fetched_names():
    result = {
        str(Gender.BOY): set(),
        str(Gender.GIRL): set()
    }
    for gender in [Gender.BOY, Gender.GIRL]:
        gpt_result_file_path = gpt_result_file_path_template.format(gender=str(gender))
        if not os.path.isfile(gpt_result_file_path):
            continue

        with open(gpt_result_file_path, 'r') as fp:
            for line in fp:
                if not line.strip():
                    continue

                parsed_line = json.loads(line)
                for name in parsed_line.keys():
                    result[str(gender)].add(canonicalize_name(name))

    return result


def fetch_gpt_meaning_origin():
    names_without_meaning_origin = get_names_without_meaning_origin()
    fetched_names = get_fetched_names()

    names_to_fetch = {
        str(Gender.BOY): set(names_without_meaning_origin[str(Gender.BOY)]).difference(
            fetched_names[str(Gender.BOY)]),
        str(Gender.GIRL): set(names_without_meaning_origin[str(Gender.GIRL)]).difference(
            fetched_names[str(Gender.GIRL)])
    }

    count = 0
    for gender in [Gender.BOY, Gender.GIRL]:
        name_list = list(names_to_fetch[str(gender)])
        logging.info('{gender} has fetched {count} names'.format(
            gender=Gender.BOY, count=len(fetched_names[str(gender)])))
        logging.info("{gender} has {count} names to fetch".format(gender=Gender.BOY, count=len(name_list)))
        batch_size = 3

        with open(gpt_result_file_path_template.format(gender=str(gender)), 'a') as fp:
            for i in range((len(name_list) // batch_size) + (len(name_list) % batch_size)):
                name_batch = name_list[(i * batch_size):((i + 1) * batch_size)]
                logging.debug('Name batch: {}'.format(name_batch))
                if len(name_batch) == 0:
                    continue

                gpt_result = fetch_meaning_origin(str(gender), name_batch)
                if gpt_result:
                    fp.write(json.dumps(gpt_result) + "\n")

                count += batch_size
                logging.debug('Processed {count} over {total}'.format(count=count, total=len(name_list)))
                # if count >= 2000:
                #    return


def get_fetched_names_meaning_origin():
    missing_names = []

    result = {
        str(Gender.BOY): {},
        str(Gender.GIRL): {}
    }
    for gender in [Gender.BOY, Gender.GIRL]:
        gpt_result_file_path = gpt_result_file_path_template.format(gender=str(gender))
        if not os.path.isfile(gpt_result_file_path):
            logging.error('Unable to find file: {}'.format(gpt_result_file_path))
            return

        logging.info(f'Load file: {gpt_result_file_path}')
        with open(gpt_result_file_path, 'r') as fp:
            for line in fp:
                if not line.strip():
                    continue

                parsed_line = json.loads(line)
                for name, facts in parsed_line.items():
                    origin = facts.get('origin', '').strip()
                    origin = '' if origin.lower() == 'unknown' else origin

                    short_meaning = facts.get('short meaning', '').strip()
                    meaning = facts.get('long meaning', '').strip()
                    '''
                    meaning = meaning.replace("’", "'")\
                                     .replace("—", "-")\
                                     .replace("‘", "'")\
                                     .replace("’", "'")\
                                     .replace("ó", "o")
                    '''

                    if not origin and not short_meaning and not meaning:
                        missing_names.append(name)
                        continue

                    result[str(gender)][name] = {}
                    # rename keys
                    if origin:
                        result[str(gender)][name]['origin'] = origin
                    if facts.get('short meaning', ''):
                        result[str(gender)][name]['short_meaning'] = short_meaning
                    if facts.get('long meaning', ''):
                        result[str(gender)][name]['meaning'] = meaning

        logging.info(f'Missing names: {missing_names}')

    return result


def get_manual_overwrite():
    with open('/Users/santan/gitspace/BabyNamer/tools/tmp/meaning_origin_overwrites.json', 'r') as fp:
        return json.load(fp)


def get_manual_overwrites():
    merged_result = get_fetched_names_meaning_origin()
    manual_overwrite = get_manual_overwrite()
    if 'boy' not in manual_overwrite:
        manual_overwrite['boy'] = {}
    if 'girl' not in manual_overwrite:
        manual_overwrite['girl'] = {}

    gender = Gender.GIRL
    try:
        for name, facts in merged_result[str(gender)].items():
            origin = facts.get('origin', '')
            if name in manual_overwrite[str(gender)] and \
                    "origin" in manual_overwrite[str(gender)][name]:
                origin = manual_overwrite[str(gender)][name]['origin']

            if len(origin) > 20:
                print(f"{name}'s origin is too long: \"{origin}\"; suggest new one. Enter if no change;"
                      " give an empty space if you want to be empty.")
                s = input("New Origin: ")
                if not s:
                    continue

                s = s.strip()
                if name not in manual_overwrite[str(gender)]:
                    manual_overwrite[str(gender)][name] = {}
                manual_overwrite[str(gender)][name]['origin'] = s
    except KeyboardInterrupt:
        logging.info("Interrupted; save file and existing...")

    with open('/Users/santan/gitspace/BabyNamer/tools/tmp/meaning_origin_overwrites.json', 'w') as fp:
        json.dump(manual_overwrite, fp, indent=4)


def merge_results(write=False):
    merged_result = get_fetched_names_meaning_origin()
    manual_overwrite = get_manual_overwrite()

    import app.lib.name_meaning as nm
    import app.lib.origin_and_short_meaning as osm

    for gender in [Gender.BOY, Gender.GIRL]:
        gender_merged_result = merged_result[str(gender)]

        # merge meaning
        for name, description in nm.NAME_MEANING.__name_meaning__[gender].items():
            if description:
                if name not in gender_merged_result:
                    gender_merged_result[name] = {}
                gender_merged_result[name]["meaning"] = description

        # merge short meaning and origin
        for name, origin_sm in osm.ORIGIN_SHORT_MEANING.__osm__[gender].items():
            origin = origin_sm.get('origin', '')
            if origin:
                if name not in gender_merged_result:
                    gender_merged_result[name] = {}
                gender_merged_result[name]["origin"] = origin
            short_meaning = origin_sm.get('short_meaning', '')
            if short_meaning:
                if name not in gender_merged_result:
                    gender_merged_result[name] = {}
                gender_merged_result[name]["short_meaning"] = short_meaning

        # merge manual overwrite
        for name, values in manual_overwrite[str(gender)].items():
            for key, val in values.items():
                gender_merged_result[name][key] = val
                # logging.debug("Overwrite {name} {key} with new value: {value}".format(name=name, key=key, value=val))

        logging.info('{gender} has {count} records'.format(gender=gender, count=len(gender_merged_result)))
        file_path = '/Users/santan/gitspace/BabyNamer/tools/tmp/origin_meaning_{gender}.json'.format(
            gender=str(gender))
        if write:
            with open(file_path, 'w') as fp:
                json.dump(gender_merged_result, fp)


if __name__ == "__main__":
    merge_results()
    # get_manual_overwrites()
    # meaning_origin = get_fetched_names_meaning_origin()
    # print(len(meaning_origin['boy']))
    # print(meaning_origin['boy']['Zuko'])
    # print(meaning_origin[str(Gender.BOY)]["Kemuel"])