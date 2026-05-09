import json
from pathlib import Path


class EventManager:
    def __init__(self, base_dir):
        self.base_dir = Path(base_dir)
        self.outcomes = {}
        self._load()

    def _load(self):
        path = self.base_dir / "data" / "event_outcomes.json"
        if not path.exists():
            return
        try:
            self.outcomes = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass

    def choose(self, event):
        story_id = str(event.get("story_id", ""))
        choices = ((event.get("event_contents_info") or {}).get("choice_array") or [])
        if not choices:
            return 0

        outcome_data = self.outcomes.get(story_id)

        if not outcome_data and len(story_id) >= 3:
            suffix = story_id[-3:]
            for k, v in self.outcomes.items():
                if k.endswith(suffix):
                    outcome_data = v
                    break

        if outcome_data:
            outcomes = outcome_data.get("outcomes", {})
            for i, choice in enumerate(choices):
                select_index = str(choice.get("select_index", ""))
                if outcomes.get(select_index) == "good":
                    return i

        if len(choices) > 1:
            return 1
        return 0
