import logging

from typing import Dict, Tuple

ATTRIBUTE_NAME = "attribute_name"
REQUIRED_KEY = 'required'
ALLOWED_VALUES = 'allowed_values'
TEMPLATE = 'template'

PARAM_TEMPLATES = {
    'gender': {
        REQUIRED_KEY: True,
        ALLOWED_VALUES: ['male', 'female', 'boy', 'girl'],
        ATTRIBUTE_NAME: 'gender',
        TEMPLATE: "the baby is {}."
    },
    'origin': {
        REQUIRED_KEY: False,
        ATTRIBUTE_NAME: 'family origin',
        TEMPLATE: 'my family comes from the country of {}. Please propose English names only. '
                  'Ideally, the proposed name has some connection with {}.'
    },
    'sibling_name': {
        REQUIRED_KEY: False,
        ATTRIBUTE_NAME: "sibling's name",
        TEMPLATE: "the newborn's sibling has a name of {}. Ideally the proposed name has some connection with {}."
    },
    'other': {
        REQUIRED_KEY: False,
        ATTRIBUTE_NAME: "other provided information",
        TEMPLATE: '{}.'
    }
}


def validate_prompt_input(user_param: Dict[str, str]) -> Tuple[bool, str] :
    # check required parameter
    for key, meta_info in PARAM_TEMPLATES.items():
        if key not in user_param:
            if meta_info.get(REQUIRED_KEY, False):
                err_msg = 'Missing required param: {}'.format(key)
                logging.info(err_msg)
                return False, err_msg
            else:
                continue

        val = user_param[key]
        if ALLOWED_VALUES in meta_info and val not in meta_info[ALLOWED_VALUES]:
            err_msg = 'Parameter {} allows only value of {}, but get {}'.format(
                key, meta_info[ALLOWED_VALUES], val)
            logging.info(err_msg)
            return False, err_msg

        return True, None


def create_user_prompt(user_info: Dict[str, str]) -> str:
    sentence_list = []

    provided_keys = user_info.keys()
    if 'sibling_name' in provided_keys:
        prompt_beginning = 'Suggest English names for a newborn '
    else:
        prompt_beginning = "Suggest English names for a newborn that complement or" \
                           "are similar in style or theme to the sibling's name"

    provided_keys_without_sibling_name = [x for x in provided_keys if x != 'sibling_name']
    if len(provided_keys_without_sibling_name) > 0:
        prompt_beginning = '{}, considering {}'.format(
            prompt_beginning, ' '.join(provided_keys_without_sibling_name))

    for key, val in user_info.items():
        if key not in PARAM_TEMPLATES.keys():
            logging.warning('Prompt creation; unexpected key: {} and val: {}'.format(key, val))
            continue

        template = PARAM_TEMPLATES[key][TEMPLATE]
        sentence_list.append(template.replace('{}', val))

    user_info_str = ' '.join(sentence_list)

    return '''
{prompt_beginning}.
{user_info_str}
Please suggest names without asking questions.
    '''.format(prompt_beginning=prompt_beginning, user_info_str=user_info_str)
