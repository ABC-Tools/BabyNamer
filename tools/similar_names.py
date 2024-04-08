import json
import logging
import os

from app.lib.common import Gender, canonicalize_name, get_app_root_dir
import app.lib.name_statistics as ns
import app.lib.similar_names as sn


output_file = '/Users/santan/gitspace/BabyNamer/app/data/similar_names_from_embedding.json'


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

    with open(output_file, 'w') as fp:
        json.dump(result, fp)


def convert_format_of_old_similar_names_file():
    result = {
        str(Gender.BOY): {},
        str(Gender.GIRL): {}
    }
    for name_gender, similar_names in sn.SIMILAR_NAMES.__similar_names__.items():
        name, gender = name_gender
        name = canonicalize_name(name)
        if not gender:
            gender = ns.NAME_STATISTICS.guess_gender(name)

        result[str(gender)][name] = similar_names

    with open('/Users/santan/gitspace/BabyNamer/app/data/similar_names.json', 'w') as fp:
        json.dump(result, fp)


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


def merge_similar_names():
    file1 = os.path.join(get_app_root_dir(), 'data', 'similar_names_from_embedding.json')
    sn1 = load_file(file1)

    file2 = os.path.join(get_app_root_dir(), 'data', 'similar_names.json')
    sn2 = load_file(file2)

    merge_result = {
        str(Gender.BOY): {**sn2[Gender.BOY], **sn1[Gender.BOY]},
        str(Gender.GIRL): {**sn2[Gender.GIRL], **sn1[Gender.GIRL]}
    }

    with open('/Users/santan/gitspace/BabyNamer/tools/tmp/similar_names_merged.json', 'w') as fp:
        json.dump(merge_result, fp)


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


if __name__ == "__main__":
    # merge_similar_names()
    load_file('/Users/santan/gitspace/BabyNamer/tools/tmp/similar_names_merged.json')
