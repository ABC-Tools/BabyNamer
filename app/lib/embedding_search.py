import logging
import time

import faiss
import os
import json

import numpy as np
from app.lib.common import Gender, get_app_root_dir
import app.openai_lib.embedding_client as embedding_client


class FaissSearch:

    def __init__(self):
        start_ts = time.time()
        boy_name_list, boy_index = FaissSearch.build_index(Gender.BOY)
        girl_name_list, girl_index = FaissSearch.build_index(Gender.GIRL)
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

    def search(self, gender: Gender, msg: str, num_of_result=10):
        embedding = embedding_client.create_single_embedding(msg)
        embedding_nparray = np.asarray([embedding])
        distances, indices = self._index[gender].search(embedding_nparray, num_of_result)

        logging.debug('Indices of result : {}, with distance of {}'.format(indices[0], distances[0]))

        result_names = [self._name_list[gender][i] for i in indices[0]]

        return result_names

    @staticmethod
    def build_index(gender):
        name_embedding_list = FaissSearch.load_file(gender)

        name_list = [x['name'] for x in name_embedding_list]
        embedding_list = [x['embedding'] for x in name_embedding_list]

        embedding_index = faiss.IndexFlatL2(len(embedding_list[0]))
        embedding_index.add(np.asarray(embedding_list))
        logging.debug('loaded index for {}; is_trained: {}, ntotal: {}'.format(
            str(gender), embedding_index.is_trained, embedding_index.ntotal))
        return name_list, embedding_index

    @staticmethod
    def load_file(gender: Gender):
        filename = FaissSearch.get_source_file(gender)
        with open(filename, 'r') as fp:
            return json.load(fp)

    @staticmethod
    def get_source_file(gender: Gender):
        if gender == Gender.BOY:
            return os.path.join(get_app_root_dir(), 'data', 'name_embedding-boy.txt')
        else:
            return os.path.join(get_app_root_dir(), 'data', 'name_embedding-girl.txt')


FAISS_SEARCH = FaissSearch()

