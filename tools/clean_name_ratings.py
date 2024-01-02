import json
import math
from collections import OrderedDict
from typing import Dict, Any, Union, List

from app.lib.common import Gender, canonicalize_name, canonicalize_gender
import app.lib.name_statistics as ns

source_file = '/Users/santan/Downloads/behindthename/ratings.json'
target_file = '/Users/santan/gitspace/BabyNamer/app/data/ratings.json'
target_stats_file = '/Users/santan/gitspace/BabyNamer/app/data/ratings_stats.json'

ALL_RATINGS = [("A Good Name", "A Bad Name"), ("Masculine", "Feminine"), ("Classic", "Modern"),
               ("Mature", "Youthful"), ("Formal", "Informal"), ("Upper Class", "Common"),
               ("Urban", "Natural"), ("Wholesome", "Devious"), ("Strong", "Delicate"),
               ("Refined", "Rough"), ("Strange", "Boring"), ("Simple", "Complex"),
               ("Serious", "Comedic"), ("Nerdy", "Unintellectual")
               ]


def compute():
    rating_list = load_file()
    rating_dict = process_raw(rating_list)
    boy_rating_stats = collect_stats(rating_dict, Gender.BOY)
    girl_rating_stats = collect_stats(rating_dict, Gender.GIRL)

    with open(target_file, 'w') as fout:
        json.dump(list(rating_dict.values()), fout)

    print('boy rating_stats\n', boy_rating_stats)
    print('girl rating_stats\n', girl_rating_stats)

    rating_stats_dict = {
        'boy': boy_rating_stats,
        'girl': girl_rating_stats
    }
    with open(target_stats_file, 'w') as fout:
        json.dump(rating_stats_dict, fout)


def collect_stats(rating_dict: Dict[str, Union[str, List]], target_gender: Gender):
    stats_data = []
    for i in range(0, len(ALL_RATINGS)):
        stats_data.append([])

    for record in rating_dict.values():
        gender = canonicalize_gender(record['gender'])
        if gender != target_gender:
            continue

        votes = int(record['votes'])

        for i in range(0, len(ALL_RATINGS)):
            rating = record['rating'][i]

            rating_type1 = ALL_RATINGS[i][0]
            score1 = percentage_to_float(rating[rating_type1])
            mean = score1
            variance = score1 * (1 - score1) / votes

            stats_data[i].append((mean, variance, votes))

    stats_result = []
    for i in range(0, len(ALL_RATINGS)):
        total_votes = 0
        total_score = 0
        total_var = 0
        for score_record in stats_data[i]:
            mean, variance, votes = score_record
            total_score += mean * votes
            total_votes += votes
            total_var += max(0, (votes - 1)) * variance

        # print('total_votes: {}, total_score: {}, total_var: {}'.format(total_votes, total_score, total_var))

        final_mean = total_score / total_votes
        final_var = total_var / (total_votes - len(stats_data[i]))
        final_stand_dev = math.sqrt(final_var)

        stats_result.append([ALL_RATINGS[i][0], ALL_RATINGS[i][1], final_mean, final_stand_dev])

    print('total votes for gender: {}: {}'.format(str(target_gender), total_votes))

    return stats_result


def process_raw(rating_list):
    result_dict = OrderedDict()
    for record in rating_list:
        raw_name = record['name']
        name = canonicalize_name(raw_name)
        votes = int(record['voted_people'])

        # Infer gender
        masculine_score = get_masculine_score(record['rating'])
        if masculine_score > 0.5:
            inferred_gender = Gender.BOY
        elif masculine_score < 0.5:
            inferred_gender = Gender.GIRL
        else:
            inferred_gender = ns.NAME_STATISTICS.guess_gender(name)

        # construct new record with canonicalized name and votes
        new_record = record.copy()
        new_record['name'] = name
        new_record['gender'] = str(inferred_gender)
        del new_record['voted_people']
        new_record['votes'] = votes
        if (name, inferred_gender) in result_dict:
            existing_record = result_dict[(name, inferred_gender)]
            new_masculine_score = get_masculine_score(existing_record['rating'])
            if new_masculine_score >= masculine_score:
                new_record['gender'] = str(Gender.GIRL)
                result_dict[(name, Gender.GIRL)] = new_record

                existing_record['gender'] = str(Gender.BOY)
                result_dict[(name, Gender.BOY)] = existing_record
            else:
                new_record['gender'] = str(Gender.BOY)
                result_dict[(name, Gender.BOY)] = new_record

                existing_record['gender'] = str(Gender.GIRL)
                result_dict[(name, Gender.GIRL)] = existing_record
        else:
            result_dict[(name, inferred_gender)] = new_record

    return result_dict


def get_masculine_score(rating_record: List[Dict[str, str]]) -> float:
    masculine_record = next(x for x in rating_record if "Masculine" in x)
    return percentage_to_float(masculine_record["Masculine"])


def load_file():
    """
    [
        {
             "name": "liam",
             "rating": [
                    {"A Good Name": "69%", "A Bad Name": "31%"},
                    {"Masculine": "92%", "Feminine": "8%"},
                    {"Classic": "46%", "Modern": "54%"},
                    {"Mature": "36%", "Youthful": "64%"},
                    {"Formal": "41%", "Informal": "59%"},
                    {"Upper Class": "43%", "Common": "57%"},
                    {"Urban": "40%", "Natural": "60%"},
                    {"Wholesome": "66%", "Devious": "34%"},
                    {"Strong": "67%", "Delicate": "33%"},
                    {"Refined": "62%", "Rough": "38%"},
                    {"Strange": "52%", "Boring": "48%"},
                    {"Simple": "75%", "Complex": "25%"},
                    {"Serious": "53%", "Comedic": "47%"},
                    {"Nerdy": "53%", "Unintellectual": "47%"}
              ],
              "voted_people": "875"
         },
        {
            "name": "olivia",
            "rating": ...
        }
    ]
    """
    with open(source_file) as fin:
        return json.load(fin)


def percentage_to_float(x: str):
    return float(x.strip().strip('%')) / 100


def float_to_percentage(x: float):
    return "{}%".format(round(x * 100))
