import json
import re
from pathlib import Path


EXCLUDED_KEYS = {
    "facility_period_configs",
    "facility_ratios",
}

RENAMES = {
    "race_list": "extra_race_list",
    "skill_priority_list": "learn_skill_list",
    "skill_blacklist": "learn_skill_blacklist",
    "blacklistedSkills": "learn_skill_blacklist",
    "extraWeight": "extra_weight",
    "scoreValue": "score_value",
    "baseScore": "base_score",
    "statValueMultiplier": "stat_value_multiplier",
    "witSpecialMultiplier": "wit_special_multiplier",
    "cureAsapConditions": "cure_asap_conditions",
}

MANT_SCENARIO_ID = 4
URA_SCENARIO_ID = 1

# Optional behavior knobs a preset file may set; passed through serialization verbatim so
# they actually reach the strategy (everything else is whitelisted). Defaults live in code.
TUNABLE_KEYS = (
    # train-vs-race gate
    "race_skip_train_stat", "race_skip_min_fans", "race_value_base", "race_value_g2_bonus",
    "race_value_camp_mult", "race_value_junior_bonus",
    # turn-quality lookahead
    "turn_quality_lookahead", "turn_quality_rest_boost", "turn_quality_weak_ratio",
    "turn_quality_strong_ratio",
    # career foresight + rainbow scoring
    "career_foresight", "rainbow_unlock_lookahead", "rainbow_unlock_band_lo",
    "rainbow_unlock_bonus", "rainbow_unlock_cap", "rainbow_explicit", "rainbow_bonus",
    "rainbow_stack_bonus", "rainbow_useful_ref", "stat_balance", "stat_balance_threshold",
    "stat_balance_boost",
    # running style + skills
    "auto_running_style", "running_style_min_grade", "skill_fit_gate",
    "skill_fit_distance_min_grade", "skill_dump_leftover", "score_skill_points",
    "skill_point_weight",
    # safety/energy/mood + misc
    "failure_hard_cap", "mood_target_recreate", "mood_recreate_max_score",
    "junior_bond_rush", "buy_notepads", "ura_force_races",
)

# Sentinel meaning "no user-imposed soft cap on this stat". The scorer then attenuates
# toward the stat's REAL in-game cap, which the game sends per-stat in chara_info
# (max_speed/max_stamina/max_power/max_guts/max_wiz) -- 1200 by default but raised by blue
# inheritance factors / scenario bonuses to 1300-1600. Using the real cap (mant.py) is what
# fixes the old dead-code bug WITHOUT throttling a cap-raised uma at a flat 1200.
NO_STAT_TARGET = 9999


def _resolve_stat_targets(raw):
    """Optional per-stat SOFT targets [Speed, Stamina, Power, Guts, Wit].

    By default there is none (sentinel 9999) and the scorer attenuates each stat toward its
    REAL in-game cap from chara_info. A preset can set a TIGHTER soft cap for a focused build
    via "expect_attribute" / "stat_targets" (5 positive ints), e.g. [9999, 600, 9999, 700, 600]
    to stop pouring score into Stamina/Guts/Wit past those values even though the game would
    allow more -- the scorer takes min(real_game_cap, soft_target) as the effective ceiling."""
    if isinstance(raw, dict):
        val = raw.get("expect_attribute")
        if val is None:
            val = raw.get("stat_targets")
        if isinstance(val, list) and len(val) == 5:
            out = []
            for v in val:
                iv = as_int(v, NO_STAT_TARGET)
                out.append(iv if iv > 0 else NO_STAT_TARGET)
            return out
    return [NO_STAT_TARGET] * 5


RUNNING_STYLE_APT_KEYS = {
    1: "proper_running_style_nige",    # Front Runner
    2: "proper_running_style_senko",   # Pace Chaser
    3: "proper_running_style_sashi",   # Late Surger
    4: "proper_running_style_oikomi",  # End Closer
}


def resolve_running_style(preset, chara_info):
    """Effective race running style (1-4) for an uma.

    Honors the preset's chosen style UNLESS its aptitude is poor -- then it runs the style the
    uma is actually best at (highest proper_running_style_* grade), so a preset built for one
    uma doesn't force a bad style on a borrowed/different runner. Aptitude grades are 1(G)..8(S);
    the default threshold 6 = B keeps a B+ preset style and only switches away from C-or-worse.
    Set preset "auto_running_style": false to always force the preset style; tune the threshold
    with "running_style_min_grade". Falls back to the raw preset style if no aptitude data."""
    raw = preset.get("running_style") if isinstance(preset, dict) else None
    try:
        pref = int(raw)
    except (TypeError, ValueError):
        pref = 0
    chara_info = chara_info or {}
    apts = {s: as_int(chara_info.get(k), 0) for s, k in RUNNING_STYLE_APT_KEYS.items()}
    if not any(apts.values()):
        return pref if pref in (1, 2, 3, 4) else 0
    if not (preset or {}).get("auto_running_style", True):
        # Explicitly opted out of auto-pick: keep the preset style verbatim (0/invalid falls
        # through to the downstream "in (1,2,3,4)" guard, leaving the game's current style).
        return pref if pref in (1, 2, 3, 4) else 0
    min_grade = as_int((preset or {}).get("running_style_min_grade"), 6)
    if pref in (1, 2, 3, 4) and apts.get(pref, 0) >= min_grade:
        return pref
    # Pick the best-aptitude style; tie-break toward the preset preference, then lower index.
    return max((1, 2, 3, 4), key=lambda s: (apts.get(s, 0), s == pref, -s))


def _resolve_scenario_id(raw):
    """Pick a preset's scenario. Defaults to MANT (4) so existing presets are unchanged;
    a preset opts into URA Finale by setting "scenario": "ura" (or 1)."""
    val = None
    if isinstance(raw, dict):
        val = raw.get("scenario")
        if val is None:
            val = raw.get("scenario_id")
    s = str(val).strip().lower() if val is not None else ""
    if s in ("1", "ura", "ura_finale", "ura finale", "urafinale", "finale"):
        return URA_SCENARIO_ID
    return MANT_SCENARIO_ID


def slugify(value):
    text = re.sub(r"[^a-zA-Z0-9._ -]+", "", str(value or "").strip())
    text = re.sub(r"\s+", " ", text).strip()
    return text or "preset"


def split_csv(value):
    if isinstance(value, list):
        return value
    return [part.strip() for part in str(value or "").split(",") if part.strip()]


def normalize_skill_list(value):
    rows = value if isinstance(value, list) else []
    result = []
    for row in rows:
        if isinstance(row, list):
            parts = []
            for item in row:
                parts.extend(split_csv(item))
        else:
            parts = split_csv(row)
        if parts:
            result.append(parts)
    return result


def as_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_race_list(value):
    result = []
    for item in value if isinstance(value, list) else []:
        race_id = as_int(item, None)
        if race_id is not None:
            result.append(race_id)
    return result


def serialize_preset(raw):
    data = dict(raw or {})
    serialized = {}

    serialized["name"] = slugify(data.get("name") or "preset")
    serialized["running_style"] = as_int(data.get("running_style"), 1)
    serialized["learn_skill_list"] = normalize_skill_list(data.get("learn_skill_list"))

    blacklist = []
    blacklist.extend(split_csv(data.get("blacklistedSkills")))
    blacklist.extend(split_csv(data.get("skill_blacklist")))
    blacklist.extend(split_csv(data.get("learn_skill_blacklist")))
    serialized["learn_skill_blacklist"] = list(dict.fromkeys(blacklist))

    serialized["extra_race_list"] = normalize_race_list(data.get("extra_race_list", data.get("race_list", [])))
    serialized["learn_skill_threshold"] = as_int(data.get("learn_skill_threshold"), 888)

    # Persist explicit per-stat targets only when the user actually set them, so default
    # presets stay clean but a focused-build override survives a save round-trip (the old
    # code dropped it here, then hardcoded 9999 in hydrate, so a user target never landed).
    if data.get("expect_attribute") is not None or data.get("stat_targets") is not None:
        serialized["expect_attribute"] = _resolve_stat_targets(data)

    # Behavior tunables: optional knobs the strategy/scorer reads at runtime. Persist them
    # verbatim when the preset file sets them -- serialize otherwise whitelists fields, which
    # silently stripped every such knob and made the documented preset overrides unreachable.
    for key in TUNABLE_KEYS:
        if data.get(key) is not None:
            serialized[key] = data[key]

    return serialized

def hydrate_preset(raw):
    data = serialize_preset(raw)

    scenario_id = _resolve_scenario_id(raw)
    data["scenario_id"] = scenario_id
    data["scenario"] = scenario_id
    data["cure_asap_conditions"] = ["Migraine", "Night Owl", "Skin Outbreak", "Slacker", "Slow Metabolism", "(Practice poor isn't worth a turn to cure)"]
    data["expect_attribute"] = _resolve_stat_targets(raw)
    data["score_value"] = [[0.11, 0.1, 0.006, 0.09], [0.11, 0.1, 0.006, 0.09], [0.11, 0.1, 0.006, 0.09], [0.03, 0.05, 0.006, 0.09], [0, 0, 0.006, 0]]
    data["base_score"] = [0, 0, 0, 0, 0]
    data["stat_value_multiplier"] = [0.01, 0.01, 0.01, 0.01, 0.01, 0.005]
    data["extra_weight"] = [[0, 0, 0, 0, 0]] * 4
    data["npc_score_value"] = [[0.05, 0.05, 0.05], [0.05, 0.05, 0.05], [0.05, 0.05, 0.05], [0.03, 0.05, 0.05], [0, 0, 0.05]]
    data["special_training"] = [0.095, 0.095, 0.095, 0.095, 0]
    data["spirit_explosion"] = [[0.16, 0.16, 0.16, 0.06, 0.11]] * 5
    data["wit_special_multiplier"] = [1.57, 1.37]
    data["compensate_failure"] = True
    data["summer_score_threshold"] = 0.34
    data["motivation_threshold_year1"] = 3
    data["motivation_threshold_year2"] = 4
    data["motivation_threshold_year3"] = 4
    data["prioritize_recreation"] = False
    data["pal_thresholds"] = []
    data["pal_friendship_score"] = [0.08, 0.057, 0.018]
    data["pal_card_multiplier"] = 0.1
    data["rest_threshold"] = 48
    data["manual_purchase_at_end"] = False
    data["mant_config"] = {}

    return data

class PresetStore:
    def __init__(self, base_dir):
        self.base_dir = Path(base_dir)
        self.preset_dir = self.base_dir / "data" / "presets"

    def ensure(self):
        self.preset_dir.mkdir(parents=True, exist_ok=True)

    def read_all(self):
        self.ensure()
        loaded = {}
        for path in self._source_files():
            try:
                data = hydrate_preset(json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                continue
            loaded[data["name"]] = data
        return sorted(loaded.values(), key=lambda item: item["name"].lower())

    def read_one(self, name):
        wanted = str(name or "").strip().lower()
        for preset in self.read_all():
            if preset["name"].lower() == wanted:
                return preset
        return None

    def write(self, preset):
        self.ensure()
        serialized_data = serialize_preset(preset)
        path = self.preset_dir / f"{slugify(serialized_data['name'])}.json"
        path.write_text(json.dumps(serialized_data, ensure_ascii=False, indent=2), encoding="utf-8")
        return hydrate_preset(serialized_data)

    def delete(self, name):
        path = self.preset_dir / f"{slugify(name)}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    def _source_files(self):
        if self.preset_dir.exists():
            return list(self.preset_dir.glob("*.json"))
        return []
