import logging
import time
from typing import Union, List, Dict

import faiss
import os
import json

import numpy as np
from app.lib.common import Gender, get_app_root_dir, canonicalize_gender, canonicalize_name
import app.openai_lib.embedding_client as embedding_client


class FaissSearch:

    def __init__(self):
        start_ts = time.time()
        boy_name_list, boy_index, boy_name_embedding_dict = FaissSearch.build_index(Gender.BOY)
        girl_name_list, girl_index, girl_name_embedding_dict = FaissSearch.build_index(Gender.GIRL)
        logging.info('FaissSearch; loading time: {} seconds with {} boy records and {} girl records'.format(
            time.time() - start_ts, len(boy_name_list), len(girl_name_list)
        ))
        self._name_list = {
            Gender.BOY: boy_name_list,
            Gender.GIRL: girl_name_list
        }
        self._index = {
            Gender.BOY: boy_index,
            Gender.GIRL: girl_index
        }
        self._name_embedding_dict = {
            Gender.BOY: boy_name_embedding_dict,
            Gender.GIRL: girl_name_embedding_dict
        }

    def search(self, gender: Union[str, Gender], msg: str, num_of_result=10):
        gender = canonicalize_gender(gender)
        embedding = embedding_client.create_single_embedding(msg)
        return self.search_with_embedding(gender, embedding, num_of_result)

    def get_embeddings(self, gender: Union[str, Gender], name: str):
        gender = canonicalize_gender(gender)
        name = canonicalize_name(name)
        return self._name_embedding_dict[gender].get(name, [])

    def similar_names(self, gender: Union[str, Gender],
                      name: str,
                      target_gender: Union[str, Gender] = None,
                      num_of_result=10) -> Dict[str, float]:
        gender = canonicalize_gender(gender)
        target_gender = canonicalize_gender(target_gender)
        name = canonicalize_name(name)
        embedding = self._name_embedding_dict[gender].get(name, [])
        if not embedding:
            return []

        if target_gender and target_gender != gender:
            # search for similar names as siblings
            return self.search_with_embedding(target_gender, embedding, num_of_result)
        else:
            result = self.search_with_embedding(gender, embedding, num_of_result + 1)
            del result[name]
            return result

    def search_with_embedding(self, gender: Gender, embedding: List[float], num_of_result=10)\
            -> Dict[str, float]:
        embedding_nparray = np.asarray([embedding])
        start_ts = time.time()
        distances, indices = self._index[gender].search(embedding_nparray, num_of_result)

        max_display_num = min(num_of_result, 10)
        logging.debug('search_with_embedding took {} seconds : {}, with distance of {}'.format(
            time.time() - start_ts, indices[0][0:max_display_num], distances[0][0:max_display_num]))

        result_names = [self._name_list[gender][i] for i in indices[0]]
        return {name: score for name, score in zip(result_names, distances[0])}

    @staticmethod
    def build_index(gender):
        name_embedding_list = FaissSearch.load_file(gender)

        name_list = [x['name'] for x in name_embedding_list]
        embedding_list = [x['embedding'] for x in name_embedding_list]
        name_embedding_dict = {x['name']: x['embedding'] for x in name_embedding_list}
        # embedding_index = faiss.IndexFlatL2(len(embedding_list[0]))
        embedding_index = faiss.IndexFlatIP(len(embedding_list[0]))
        embedding_index.add(np.asarray(embedding_list))
        logging.debug('loaded index for {}; is_trained: {}, ntotal: {}'.format(
            str(gender), embedding_index.is_trained, embedding_index.ntotal))
        return name_list, embedding_index, name_embedding_dict

    @staticmethod
    def load_file(gender: Gender):
        filename = FaissSearch.get_source_file(gender)
        with open(filename, 'r') as fp:
            return json.load(fp)

    @staticmethod
    def get_source_file(gender: Gender):
        if gender == Gender.BOY:
            return os.path.join(get_app_root_dir(), 'data', 'name_embedding-concise_rating-boy.txt')
        else:
            return os.path.join(get_app_root_dir(), 'data', 'name_embedding-concise_rating-girl.txt')


FAISS_SEARCH = FaissSearch()
