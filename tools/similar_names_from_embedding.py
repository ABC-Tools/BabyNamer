import json

from app.lib.common import Gender, canonicalize_name
import app.lib.embedding_search as es
import app.lib.name_statistics as ns
import app.lib.similar_names as sn


output_file = '/Users/santan/gitspace/BabyNamer/app/data/similar_names_from_embedding.json'


def create_similar_names():
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
