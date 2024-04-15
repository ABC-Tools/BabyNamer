import json
import logging
import os

from typing import List

import openai

from app.lib.common import Gender, canonicalize_name, get_app_root_dir
import app.lib.name_statistics as ns
import app.lib.similar_names as sn

gpt_result_file_path_template = '/Users/santan/gitspace/BabyNamer/tools/tmp/similar_names_gpt_{gender}.json'
embedding_output_file = '/Users/santan/gitspace/BabyNamer/app/data/similar_names_from_embedding.json'
client = openai.OpenAI(api_key='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', max_retries=5)
consumed_tokens = 0


def create_similar_names():
    import app.lib.embedding_search as es

    result = {
        str(Gender.BOY): {},
        str(Gender.GIRL): {}
    }
    for name_gender, similar_names in sn.SIMILAR_NAMES.__similar_names__.items():
        name, gender = name_gender
        name = canonicalize_name(name)
        if not gender:
            gender = ns.NAME_STATISTICS.guess_gender(name)

        embedding_similar_names = es.FAISS_SEARCH.similar_names(gender, name, num_of_result=11)
        if embedding_similar_names:
            # the first one is always
            result[str(gender)][name] = embedding_similar_names
        else:
            result[str(gender)][name] = similar_names

    with open(embedding_output_file, 'w') as fp:
        json.dump(result, fp)


def fetch_gpt_similar_names(gender: str, names: List[str]):
    global consumed_tokens

    user_prompt = """
You are a good assistant to help parents to identify the similar names of given candidate names for a {gender} newborn.
You will be a given a list of candidate names; for each given candidate name in the list of names, return 20 similar names.

The list of candidate names: {name_list}.

Please return the result in Json format, like
{{
    "candidate name 1 from the list": ["similar name 1", "similar name 2", ...],
    "candidate name 2 from the list": ["similar name 3", "similar name 4", ...],
    ...
}}
""".format(gender=gender, name_list=", ".join(names))
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


def load_file(json_filename):
    with open(json_filename, 'r') as fin:
        data = json.load(fin)

    output = {
        Gender.BOY: data[str(Gender.BOY)],
        Gender.GIRL: data[str(Gender.GIRL)]
    }

    logging.info("similar names: loaded number of boy names: {} and number of girl names: {}".format(
        len(output[Gender.BOY]), len(output[Gender.GIRL])))

    return output


def get_names_without_similar_names():
    sname = load_file('/Users/santan/gitspace/BabyNamer/tools/tmp/similar_names_merged.json')

    import app.lib.name_statistics as ns
    result = {
        str(Gender.BOY): [],
        str(Gender.GIRL): []
    }

    for gender in [Gender.BOY, Gender.GIRL]:
        for name in ns.NAME_STATISTICS.get_popular_names(gender, count=8000):
            if name not in sname[gender]:
                result[str(gender)].append(name)

    return result


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


def merge_result():
    """
    If the result file is very big, we may consider to map names to IDs to reduce memory footprint
    :return:
    """
    existing_sname = load_file('/Users/santan/gitspace/BabyNamer/tools/tmp/similar_names_merged.json')
    existing_sname = {
        str(Gender.BOY): existing_sname[Gender.BOY],
        str(Gender.GIRL): existing_sname[Gender.GIRL]
    }
    logging.info('Existing similar names for {} boy names'.format(len(existing_sname[str(Gender.BOY)])))
    logging.info('Existing similar names for {} girl names'.format(len(existing_sname[str(Gender.GIRL)])))

    gpt_sname = get_fetched_similar_names()
    logging.info('GPT similar names for {} boy names'.format(len(gpt_sname[str(Gender.BOY)])))
    logging.info('GPT similar names for {} girl names'.format(len(gpt_sname[str(Gender.GIRL)])))

    merged_results = {
        str(Gender.BOY): {**existing_sname[str(Gender.BOY)], **gpt_sname[str(Gender.BOY)]},
        str(Gender.GIRL): {**existing_sname[str(Gender.GIRL)], **gpt_sname[str(Gender.GIRL)]}
    }
    logging.info('Gathered similar names for {} boy names'.format(len(merged_results[str(Gender.BOY)])))
    logging.info('Gathered similar names for {} girl names'.format(len(merged_results[str(Gender.GIRL)])))

    with open('/Users/santan/gitspace/BabyNamer/app/data/similar_names_04_13.json', 'w') as fp:
        json.dump(merged_results, fp)


def get_fetched_similar_names():
    result = {
        str(Gender.BOY): {},
        str(Gender.GIRL): {}
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
                for name, sn_list in parsed_line.items():
                    result[str(gender)][name] = sn_list

    return result


def get_gpt_similar_names_all():
    names_without_similar_names = get_names_without_similar_names()
    fetched_names = get_fetched_names()

    names_to_fetch = {
        str(Gender.BOY): set(names_without_similar_names[str(Gender.BOY)]).difference(
            fetched_names[str(Gender.BOY)]),
        str(Gender.GIRL): set(names_without_similar_names[str(Gender.GIRL)]).difference(
            fetched_names[str(Gender.GIRL)])
    }

    count = 0
    for gender in [Gender.BOY, Gender.GIRL]:
        name_list = list(names_to_fetch[str(gender)])
        logging.info('{gender} has fetched {count} names'.format(
            gender=Gender.BOY, count=len(fetched_names[str(gender)])))
        logging.info("{gender} has {count} names to fetch".format(gender=Gender.BOY, count=len(name_list)))
        batch_size = 5

        with open(gpt_result_file_path_template.format(gender=str(gender)), 'a') as fp:
            for i in range((len(name_list) // batch_size) + (len(name_list) % batch_size)):
                name_batch = name_list[(i * batch_size):((i + 1) * batch_size)]
                logging.debug('Name batch: {}'.format(name_batch))
                if len(name_batch) == 0:
                    continue

                gpt_result = fetch_gpt_similar_names(str(gender), name_batch)
                if gpt_result:
                    fp.write(json.dumps(gpt_result) + "\n")

                count += batch_size
                logging.debug('Processed {count} over {total}'.format(count=count, total=len(name_list)))
                # if count >= 100:
                #    return


if __name__ == "__main__":
    merge_result()
