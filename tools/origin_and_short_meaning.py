import json

source_file = '/Users/santan/Downloads/babynames/babynames_meaning.json'
output_file = '/Users/santan/gitspace/BabyNamer/app/data/origin_and_short_meaning'


def load_file():
    with open(source_file, 'r') as fin:
        return json.load(fin)


def convert():
    """
    the input is like:
    [
        {"name": "liam", "gender": "Male", "origin": "Irish",
         "short_meaning": "Desired Helmet/Protector",
         "long_meaning": "The name Liam is primarily..."
        },
        {...}
    ]
    """
    orig_list = load_file()
    new_list = []
    for record in orig_list:
        new_record = {
            'name': record['name'],
            'gender': record['gender'],
            'origin': record['origin'],
            'short_meaning': record['short_meaning']
        }
        new_list.append(new_record)

    with open(output_file, 'w') as fout:
        json.dump(new_list, fout)
