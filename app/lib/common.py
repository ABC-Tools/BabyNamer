
import time
import datetime
import os

from enum import Enum


class Gender(Enum):
    GIRL = 1
    BOY = 2

    def __str__(self):
        return f'{self.name}'.lower()


def canonicalize_name(raw_name: str):
    name = raw_name.strip()
    name = ''.join([i for i in name if i.isalpha()])
    return name.lower().capitalize()


def canonicalize_gender(gender: str):
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
