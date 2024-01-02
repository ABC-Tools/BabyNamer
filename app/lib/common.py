
import time
import datetime
import os

from enum import Enum
from typing import Union


class Gender(Enum):
    GIRL = 1
    BOY = 2

    def __str__(self):
        return f'{self.name}'.lower()


def canonicalize_name(raw_name: str):
    name = raw_name.strip()
    name = ''.join([i for i in name if i.isalpha()])
    return name.lower().capitalize()


def canonicalize_gender(gender: Union[str, Gender]):
    if isinstance(gender, Gender):
        return gender

    if not gender or gender.lower() in ['none']:
        return None

    if gender.lower() in ['f', 'female', 'girl', 'g']:
        return Gender.GIRL

    if gender.lower() in ['m', 'male', 'boy', 'b']:
        return Gender.BOY

    raise ValueError('Invalid gender string: {}'.format(gender))


def fprint(s: str):
    print('{ts}  {str}'.format(
        ts=datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'),
        str=s
    ))


def get_app_root_dir():
    return os.path.dirname(                         # app
        os.path.dirname(os.path.abspath(__file__))  # app/lib
    )


def percentage_to_float(x: str):
    return float(x.strip().strip('%')) / 100


def float_to_percentage(x: float, min_val=0):
    return "{}%".format(max(min_val, round(x * 100)))
