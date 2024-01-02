"""
BSON is not significant smaller than JSON

/Users/santan/Downloads/nameberry/parse_results_new.json
/Users/santan/Downloads/babynames/babynames_meaning.json
"""
import logging
import time
from typing import Dict

import openai
import os
import json

from app.lib.common import canonicalize_name, canonicalize_gender, Gender
import app.lib.name_statistics as ns
import app.lib.name_rating as nr

client = openai.OpenAI(api_key='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')

intput_json_file1 = '/Users/santan/Downloads/nameberry/parse_results_new.json'
intput_json_file2 = '/Users/santan/Downloads/babynames/babynames_meaning.json'


def create_embeddings(gender: str):
    gender = canonicalize_gender(gender)

    input_dict1, input_dict2 = load_input_files()

    count = 0
    msg_threshold = 5000

    msg_list = []
    name_list = []
    gender_list = []

    result_list = []
    popular_names = ns.NAME_STATISTICS.get_popular_names(gender, count=5000)
    for rank, name in enumerate(popular_names):
        name = canonicalize_name(name)

        # logging.debug('work on {}'.format(name))
        rank_descrption = 'In terms of popularity, this name is ranked {rank} among' \
                          ' the {total} {gender} names in the last 3 years.'.format(
            rank=rank, total=len(popular_names), gender=str(gender)
        )
        rating_description = create_rating_description(name, gender)
        description1 = input_dict1[gender].get(name, '')
        description2 = create_text_from_input2(input_dict2[gender].get(name, {}))
        if not rating_description and not description1 and not description2:
            logging.info('No record for {} with gender of {}'.format(name, str(gender)))
            continue

        msg = '{}\n{}\n{}\n{}'.format(rank_descrption, description2, description1, rating_description)
        msg_list.append(msg)
        name_list.append(name)
        gender_list.append(gender)

        if len(msg_list) >= 7:
            start_ts = time.time()
            resp = client.embeddings.create(input=msg_list, model="text-embedding-ada-002")
            logging.debug('Take {} seconds for {} embeddings for the names of {}. Used token: {}.'
                          ' Current count: {}'.format(
                time.time() - start_ts, len(msg_list), name_list, resp.usage.total_tokens, count + len(msg_list)))

            write_output(result_list, resp.data, name_list, gender_list)

            count += len(msg_list)

            msg_list = []
            name_list = []
            gender_list = []

        # logging.debug('count: {}, msg_list: {}'.format(count, len(msg_list)))
        if count >= msg_threshold:
            break

    if len(msg_list) > 0:
        resp = client.embeddings.create(input=msg_list, model="text-embedding-ada-002")
        write_output(result_list, resp.data, name_list, gender_list)
        logging.info('Finished last {}'.format(name_list))

        count += len(msg_list)

        logging.info('Total records: {}'.format(count))

    write_embeddings_to_files(gender, result_list)


def write_embeddings_to_files(gender, result_list):
    if gender == Gender.BOY:
        output_json_file = '/Users/santan/gitspace/BabyNamer/app/data/name_embedding-boy.txt'
        output_bson_file = '/Users/santan/gitspace/BabyNamer/app/data/name_embedding-boy.bson'
    else:
        output_json_file = '/Users/santan/gitspace/BabyNamer/app/data/name_embedding-girl.txt'
        output_bson_file = '/Users/santan/gitspace/BabyNamer/app/data/name_embedding-girl.bson'

    with open(output_json_file, 'w') as fp:
        json.dump(result_list, fp)

    """
    with open(output_bson_file, 'wb') as fp:
        # BSON requires the top level to be dictionary
        tmp_dict = {'': result_list}
        fp.write(bson.dumps(tmp_dict))
    
    # read:
    with open(output_bson_file, 'rb') as fp:
        result = bson.loads(fp.read())
    """


def create_rating_description(name: str, gender: Gender):
    gender = canonicalize_gender(gender)
    rating_dict = nr.NAME_RATING.get_feature_percentiles(name, gender)
    if not rating_dict:
        return ''

    all_sentences = []
    for rating_url_param, val_dict in rating_dict.items():
        leading_part = rating_url_param.replace('_', ' ').replace('option', 'rating')
        parts = []
        for option, val_tuple in val_dict.items():
            template = '{vote_percent} people consider this name {option} ' \
                       '(the {direction} {rank_percent} {option} name across all {gender} names).'
            parts.append(template.format(
                vote_percent=val_tuple[0],
                option=option.lower(),
                direction=val_tuple[1],
                rank_percent=val_tuple[2],
                gender=str(gender)
            ))
        sentence = '{leading}: {description}'.format(
            leading=leading_part, description=' '.join(parts)
        )
        all_sentences.append(sentence)

    return '\n'.join(all_sentences)


def write_output(result_list, resp_data, name_list, gender_list):
    for i in range(len(name_list)):
        output_dict = {
            'name': name_list[i],
            'embedding': resp_data[i].embedding
        }
        result_list.append(output_dict)


def create_text_from_input2(record2: Dict[str, str]):
    if not record2:
        return ''

    return """
origin: {origin}
short meaning: {short_meaning}
{description1}
        """.format(
        origin=record2["origin"],
        short_meaning=record2["short_meaning"],
        description1=record2["description"]
    )


def load_output_content():
    result = {
        Gender.BOY: {},
        Gender.GIRL: {}
    }
    if not os.path.isfile(output_json_file):
        return result

    with open(output_json_file, 'r') as fp:
        for line in fp:
            line = line.strip()
            content_dict = json.loads(line)

            name = canonicalize_name(content_dict['name'])
            gender = content_dict['gender']
            # embedding = json.loads(content_dict['embedding'])

            result[gender][name] = []

    return result


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
