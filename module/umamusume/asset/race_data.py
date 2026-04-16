import csv
import os.path

from bot.base.common import ImageMatchConfig
from bot.base.resource import Template
from module.umamusume.asset import REF_SUITABLE_RACE

RACE_TEMPLATE_MATCH_ACCURACY = 0.71

RACE_LIST: dict[int, list] = {}
UMAMUSUME_RACE_TEMPLATE_PATH = "/umamusume/race"

PERIOD_TO_RACES = {}
RACE_GRADE = {}
RACE_ID_TO_TURN: dict[int, int] = {}

def _load_all_race_data():
    with open('resource/umamusume/data/race.csv', 'r', encoding="utf-8") as file:
        reader = csv.reader(file)
        for row in reader:
            if len(row) >= 6:
                race_id = int(row[1])
                race_name = row[3]
                grade = row[5].strip()
                time_period = int(row[0])

                path = "resource" + UMAMUSUME_RACE_TEMPLATE_PATH + "/" + str(race_id) + ".png"
                if os.path.isfile(path):
                    t = Template(
                        str(race_id),
                        UMAMUSUME_RACE_TEMPLATE_PATH,
                        ImageMatchConfig(match_accuracy=RACE_TEMPLATE_MATCH_ACCURACY),
                    )
                    race_info = (race_id, race_name, t)
                    RACE_LIST[race_id] = race_info

                if time_period not in PERIOD_TO_RACES:
                    PERIOD_TO_RACES[time_period] = []
                PERIOD_TO_RACES[time_period].append(race_id)

                if grade:
                    RACE_GRADE[race_id] = grade
                    
                RACE_ID_TO_TURN[race_id] = time_period 
                   

    RACE_LIST[0] = (0, "suitable", REF_SUITABLE_RACE)


_load_all_race_data()


def get_races_for_period(time_period: int) -> list[int]:
    return PERIOD_TO_RACES.get(time_period, [])


def is_g1_race(race_id):
    return RACE_GRADE.get(race_id, '') == 'G1'


def is_g2_race(race_id):
    return RACE_GRADE.get(race_id, '') == 'G2'


def is_g3_race(race_id):
    return RACE_GRADE.get(race_id, '') == 'G3'

def compute_race_chains(extra_race_list: list[int]) -> dict[int, tuple[int, int]]:
    
    #Maps races to their position in the chain 
    race_turns = sorted({
        RACE_ID_TO_TURN[race_id]
        for race_id in extra_race_list
        if race_id in RACE_ID_TO_TURN
    })

    chain_map: dict[int, tuple[int, int]] = {}
    i = 0
    while i < len(race_turns):
        j = i
        while j + 1 < len(race_turns) and race_turns[j + 1] == race_turns[j] + 1:
            j += 1
        chain_length = j - i + 1
        for pos, turn in enumerate(race_turns[i:j + 1], start=1):
            chain_map[turn] = (pos, chain_length)
        i = j + 1

    return chain_map