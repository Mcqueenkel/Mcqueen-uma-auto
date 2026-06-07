import json
import threading
from pathlib import Path


class EventManager:
    def __init__(self, base_dir):
        self.base_dir = Path(base_dir)
        self.outcomes = {}
        self._lock = threading.Lock()
        # Built-in "good/bad" DB (read-only, lives under data/). The user's manual
        # overrides and the seen-event log live under uma_runtime/ so we never touch
        # the regenerated data/ files.
        self._overrides_path = self.base_dir / "uma_runtime" / "event_overrides.json"
        self._seen_path = self.base_dir / "uma_runtime" / "events_seen.json"
        self._load()

    def _load(self):
        path = self.base_dir / "data" / "event_outcomes.json"
        if not path.exists():
            return
        try:
            self.outcomes = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass

    def _read_overrides(self):
        """User's manual per-event choice overrides: {story_id: choice_index}."""
        try:
            if self._overrides_path.exists():
                return json.loads(self._overrides_path.read_text(encoding="utf-8")) or {}
        except Exception:
            pass
        return {}

    def _record_seen(self, story_id, event, num_choices, picked, source):
        """Log every multi-choice event the bot meets so the UI can list them and let
        the user set an override. Keyed by story_id; safe to fail silently."""
        try:
            choices = ((event.get("event_contents_info") or {}).get("choice_array") or [])
            with self._lock:
                seen = {}
                if self._seen_path.exists():
                    try:
                        seen = json.loads(self._seen_path.read_text(encoding="utf-8")) or {}
                    except Exception:
                        seen = {}
                entry = seen.get(story_id) or {}
                known = self.outcomes.get(story_id) or {}
                entry.update({
                    "story_id": story_id,
                    "event_name": known.get("event_name") or entry.get("event_name") or "",
                    "num_choices": int(num_choices),
                    "picked": int(picked),
                    "source": source,
                    "count": int(entry.get("count") or 0) + 1,
                    "choice_items": [int(c.get("receive_item_id") or 0) for c in choices],
                })
                seen[story_id] = entry
                self._seen_path.parent.mkdir(parents=True, exist_ok=True)
                self._seen_path.write_text(
                    json.dumps(seen, ensure_ascii=False, indent=1), encoding="utf-8"
                )
        except Exception:
            pass

    def choose(self, event):
        story_id = str(event.get("story_id", ""))

        if story_id == "400004002":
            return 2

        choices = ((event.get("event_contents_info") or {}).get("choice_array") or [])
        if not choices:
            return 0
        num = len(choices)

        # 1) User override wins (manual per-event pick from the EVENT CHOICES tab).
        ov = self._read_overrides().get(story_id)
        if ov is not None:
            try:
                idx = int(ov)
                if 0 <= idx < num:
                    self._record_seen(story_id, event, num, idx, "override")
                    return idx
            except (TypeError, ValueError):
                pass

        # 2) Built-in good/bad DB.
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
                    self._record_seen(story_id, event, num, i, "db")
                    return i

        # 3) Fallback: second choice when available, else the only one.
        fallback = 1 if num > 1 else 0
        self._record_seen(story_id, event, num, fallback, "fallback")
        return fallback
