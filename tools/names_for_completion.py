import json

import app.lib.name_statistics as ns

stats = ns.NameStatistics(start_year=2012, end_year=2022)

result = {
    'boy': stats.get_popular_names('boy', count=100000),
    'girl': stats.get_popular_names('girl', count=100000)
}

with open('/Users/santan/gitspace/BabyNamer/app/data/names_for_completion.json', 'w') as fp:
    json.dump(result, fp)
