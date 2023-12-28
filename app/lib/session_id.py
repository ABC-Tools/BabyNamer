

import random


def verify_session_id(session_id: str):
    if len(session_id) <= 7:
        raise ValueError("Invalid session id: {}".format(session_id))

    rand_int = int(session_id[0:7])
    return session_id == get_session_id(rand_int)


def get_session_id(rand_int: int) -> str:
    if len(str(rand_int)) > 7:
        raise ValueError("Invalid random integer for session id: {}".format(rand_int))

    calc_result = ((rand_int * 643) % 97832) * 245
    return "{0:07d}".format(rand_int) + str(calc_result)


def create_session_id():
    rand_int = random.randint(0, 10000000)
    return get_session_id(rand_int)
