from domain.types import get_formatted_event_or_thing_types_by_value
from models.pc_object import PcObject
from utils.logger import logger
from utils.test_utils import create_thing

MOCK_NAMES = [
    "Anaconda",
    "Borneo",
    "D--",
    "Funky",
    "Sun",
    "Topaz"
]

def create_industrial_things():
    logger.info('create_industrial_things')

    things_by_name = {}

    types_by_value = get_formatted_event_or_thing_types_by_value()

    thing_types = [t for t in types_by_value.values() if t['type'] == 'Thing']

    mock_count = -1
    for thing_type in thing_types:

        # WE JUST PARSE THE MOCK NAMES
        # WITH A COUNTER AND RESET THE COUNTER
        # TO ZERO WHEN WE REACH ITS LAST ITEM
        mock_count += 1
        if mock_count > len(MOCK_NAMES) - 1:
            mock_count = 0

        name = thing_type['value'] + " / " + MOCK_NAMES[mock_count]
        things_by_name[name] = create_thing(
            is_national=True,
            thing_name=name,
            thing_type=thing_type['value'],
            url='https://ilestencoretemps.fr/'
            if types_by_value[thing_type['value']]['onlineOnly']
            else None)

    PcObject.check_and_save(*things_by_name.values())

    return things_by_name
