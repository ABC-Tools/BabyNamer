import json

import app.lib.name_meaning as nm
from app.lib.common import Gender

result = {
    'boy': sorted(list(nm.NAME_MEANING.__name_meaning__[Gender.BOY].keys())),
    'girl': sorted(list(nm.NAME_MEANING.__name_meaning__[Gender.GIRL].keys()))
}

with open('/Users/santan/gitspace/BabyNamer/app/data/names_for_completion.json', 'w') as fp:
    json.dump(result, fp)
