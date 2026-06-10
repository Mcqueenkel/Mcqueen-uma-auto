import json
import threading
from pathlib import Path


class EventManager:
    # Stat keys recorded when observing what an event choice actually did.
    OUTCOME_KEYS = ("speed", "stamina", "power", "guts", "wiz", "skill_point", "vital", "motivation")

    def __init__(self, base_dir):
        self.base_dir = Path(base_dir)
        self.outcomes = {}
        self._lock = threading.Lock()
        # Built-in "good/bad" DB (read-only, lives under data/). The user's manual
        # overrides, the seen-event log and the observed per-choice outcomes live under
        # uma_runtime/ so we never touch the regenerated data/ files.
        self._overrides_path = self.base_dir / "uma_runtime" / "event_overrides.json"
        self._seen_path = self.base_dir / "uma_runtime" / "events_seen.json"
        self._choice_outcomes_path = self.base_dir / "uma_runtime" / "event_choice_outcomes.json"
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
                    # Some events vary their option count between sightings; keep the max so
                    # the UI never hides an option (and observed data for it) it once showed.
                    "num_choices": max(int(num_choices), int(entry.get("num_choices") or 0)),
                    "picked": int(picked),
                    "source": source,
                    "count": int(entry.get("count") or 0) + 1,
                    "choice_items": [int(c.get("receive_item_id") or 0) for c in choices],
                    # The game's select_index per position THIS sighting. NOT stable across
                    # sightings (e.g. "Victory!" shows subsets of 1..4), so outcomes/labels
                    # are keyed by select_index and mapped to positions via this list.
                    "choice_selects": [int(c.get("select_index") or 0) for c in choices],
                })
                seen[story_id] = entry
                self._seen_path.parent.mkdir(parents=True, exist_ok=True)
                self._seen_path.write_text(
                    json.dumps(seen, ensure_ascii=False, indent=1), encoding="utf-8"
                )
        except Exception:
            pass

    # Cap fields per stat: a delta recorded while the BEFORE value already sits at its cap
    # is truncated by the game (e.g. +30 heal at 95/100 vital records as +5), which would
    # bias the running average one-directionally -- those keys are skipped instead.
    OUTCOME_CAP_KEYS = {"speed": "max_speed", "stamina": "max_stamina", "power": "max_power",
                        "guts": "max_guts", "wiz": "max_wiz", "vital": "max_vital"}
    MOTIVATION_CAP = 5

    def record_choice_outcome(self, story_id, select_index, before_chara, after_chara):
        """Learn what an event choice actually DID: diff the chara stats around the
        check_event call and fold the delta into a running average per (event, choice).
        These observations become the choice descriptions in the EVENT CHOICES panel --
        neither master.mdb nor the live payload carries choice text/effects, so what the
        bot has seen happen is the one exact, self-maintaining source. Random outcomes
        (success/fail events) wash out in the average; `n` tells the user the sample size.

        Keyed by the game's SELECT_INDEX, not the position in choice_array: the same
        event presents varying/sparse select sets across sightings (verified in real
        logs), so position would blend genuinely different choices. Safe to fail
        silently; never raises into the career loop."""
        try:
            story_id = str(story_id or "")
            select_index = int(select_index or 0)
            if not story_id or select_index <= 0:
                return
            if not isinstance(before_chara, dict) or not isinstance(after_chara, dict):
                return
            if not after_chara.get("turn"):
                return  # response without real chara state -> nothing observable
            delta = {}
            for key in self.OUTCOME_KEYS:
                try:
                    before = int(before_chara.get(key) or 0)
                    d = int(after_chara.get(key) or 0) - before
                except (TypeError, ValueError):
                    continue
                # Skip cap-truncated observations (one-directional bias, see OUTCOME_CAP_KEYS).
                cap_key = self.OUTCOME_CAP_KEYS.get(key)
                if cap_key:
                    try:
                        cap = int(before_chara.get(cap_key) or 0)
                    except (TypeError, ValueError):
                        cap = 0
                    if cap and before >= cap:
                        continue
                elif key == "motivation" and before >= self.MOTIVATION_CAP:
                    continue
                if d:
                    delta[key] = d
            with self._lock:
                db = {}
                if self._choice_outcomes_path.exists():
                    try:
                        db = json.loads(self._choice_outcomes_path.read_text(encoding="utf-8")) or {}
                    except Exception:
                        db = {}
                entry = db.setdefault(story_id, {})
                slot = entry.get(str(select_index)) or {"n": 0, "avg": {}}
                n = int(slot.get("n") or 0)
                avg = dict(slot.get("avg") or {})
                keys = set(avg) | set(delta)
                slot["avg"] = {k: round((float(avg.get(k, 0.0)) * n + delta.get(k, 0)) / (n + 1), 2) for k in keys}
                slot["n"] = n + 1
                slot["last"] = delta
                entry[str(select_index)] = slot
                self._choice_outcomes_path.parent.mkdir(parents=True, exist_ok=True)
                # Atomic write: the API reads this file per request; a mid-write read
                # must never see a torn/empty JSON.
                tmp = self._choice_outcomes_path.with_suffix(".json.tmp")
                tmp.write_text(json.dumps(db, ensure_ascii=False, indent=1), encoding="utf-8")
                import os
                os.replace(tmp, self._choice_outcomes_path)
        except Exception:
            pass

    def choice_outcomes(self):
        """Read-only view of the observed per-choice outcomes ({story_id: {idx: {n, avg, last}}})."""
        try:
            if self._choice_outcomes_path.exists():
                return json.loads(self._choice_outcomes_path.read_text(encoding="utf-8")) or {}
        except Exception:
            pass
        return {}

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
