from dataclasses import dataclass


@dataclass
class Decision:
    action: str
    payload: dict
    reason: str


class ScenarioStrategy:
    scenario_id = 0

    def next_decision(self, state, preset):
        raise NotImplementedError
