"""Career foresight: predict where THIS career is heading and train toward it.

The base scorer is greedy -- it picks whatever training yields the most raw stat THIS turn.
That ignores the shape of the career ahead: a long-distance stayer and a sprinter want very
different final builds, and the bot should bend training toward the one it's actually running.

This module reads what the game already tells us about the uma -- distance/style aptitudes,
current stats, the in-game stat caps, the turn -- and produces a CareerForecast:

  * archetype     : a human label for the career direction ("Long / End Closer")
  * stat_targets  : per-stat [Speed, Stamina, Power, Guts, Wit] goals the build should aim for,
                    derived from the apt distances (blended) + running style, clamped to the
                    real in-game caps. These feed straight into _score_command as the soft
                    targets, so the existing cap-attenuation ladder + under-target balance boost
                    steer every training turn toward the predicted profile instead of raw gain.
  * trajectory    : per-stat on-track / behind / ahead vs where the build should be by this turn
  * summary       : one-line "predicted direction" for logs / UI

It is deliberately data-driven and side-effect free: forecast(data, preset) -> CareerForecast.
If anything is missing it falls back to all-9999 targets (a no-op that reverts to raw scoring).
"""

import json
from pathlib import Path

from career_bot.presets import resolve_running_style

STAT_NAMES = ["Speed", "Stamina", "Power", "Guts", "Wit"]
# Support-card type -> stat index, for counting the deck composition.
SUPPORT_TYPE_INDEX = {"Speed": 0, "Stamina": 1, "Power": 2, "Guts": 3, "Wisdom": 4}
STAT_KEYS = ["speed", "stamina", "power", "guts", "wiz"]
CAP_KEYS = ["max_speed", "max_stamina", "max_power", "max_guts", "max_wiz"]
NO_TARGET = 9999
BASE_CAP = 1200

DISTANCE_APT_KEYS = {
    "short": "proper_distance_short",
    "mile": "proper_distance_mile",
    "middle": "proper_distance_middle",
    "long": "proper_distance_long",
}
STYLE_NAMES = {1: "Front Runner", 2: "Pace Chaser", 3: "Late Surger", 4: "End Closer"}

# Per-distance ideal build [Speed, Stamina, Power, Guts, Wit]. Hand-set from standard
# Umamusume distance theory: sprints are Speed/Power with minimal Stamina; longer races trade
# Speed for the Stamina needed to finish. Values are goals, later clamped to the real caps.
DISTANCE_PROFILES = {
    # Stamina is set to roughly "enough to finish with the bot's recovery-skill purchases", kept
    # deliberately lean on the short/mile end so the soft cap frees training turns for the Speed
    # and Power that actually win those races (it's a soft ceiling, not a hard floor).
    "short":  [1150, 450, 1100, 550, 600],
    "mile":   [1150, 650, 1050, 550, 600],
    "middle": [1150, 900,  980, 600, 650],
    "long":   [1100, 1150, 920, 700, 650],
}
# Running-style nudges (additive, GENTLE so the distance profile still dominates the ordering):
# front-runners need stamina to hold the lead wire; closers want extra power/guts for a late
# burst and can shave a little stamina -- but not enough to outrank stamina on a long race.
STYLE_ADJUST = {
    1: [30, 80, -20, 0, 0],   # Front Runner
    2: [20, 30, 20, 0, 20],   # Pace Chaser
    3: [20, -10, 60, 40, 0],  # Late Surger
    4: [20, -20, 70, 50, 0],  # End Closer
}
APT_GRADE_FLOOR = 5   # only distances at C-aptitude or better count toward the blend
TARGET_FLOOR = 350    # never drive a stat target below this


class CareerForecast:
    """The predicted direction of a career. Read-only value object."""

    def __init__(self, stat_targets, archetype="", key_style=0, apt_distances=None,
                 trajectory=None, summary="", turn=0, active=True):
        self.stat_targets = stat_targets            # [5] soft targets for the scorer
        self.archetype = archetype                  # e.g. "Long / End Closer"
        self.key_style = key_style                  # 1-4
        self.apt_distances = apt_distances or []    # [(category, grade), ...] best-first
        self.trajectory = trajectory or []          # [{stat, current, expected, target, status}]
        self.summary = summary
        self.turn = turn
        self.active = active                        # False -> targets are the 9999 no-op

    def to_dict(self):
        return {
            "archetype": self.archetype,
            "key_style": STYLE_NAMES.get(self.key_style, ""),
            "apt_distances": self.apt_distances,
            "stat_targets": {STAT_NAMES[i]: self.stat_targets[i] for i in range(5)},
            "trajectory": self.trajectory,
            "summary": self.summary,
            "turn": self.turn,
            "active": self.active,
        }


def _inactive(turn=0, reason="no data"):
    return CareerForecast([NO_TARGET] * 5, summary=f"Career forecast unavailable ({reason})",
                          turn=turn, active=False)


class CareerForecaster:
    def __init__(self, base_dir=None):
        self.base_dir = base_dir
        self._support_map_cache = None

    def _support_map(self):
        if self._support_map_cache is None:
            self._support_map_cache = {}
            try:
                p = Path(self.base_dir) / "data" / "support_list.json"
                loaded = json.loads(p.read_text(encoding="utf-8"))
                self._support_map_cache = loaded if isinstance(loaded, dict) else {}
            except Exception:
                self._support_map_cache = {}
        return self._support_map_cache

    def _deck_type_counts(self, chara, preset):
        """Deck composition as [Speed, Stamina, Power, Guts, Wit] support-card counts. Prefers
        the runtime-computed preset['_deck_type_counts'] (set at career start); otherwise derives
        it from the deck's support_card_array + support_list.json types. Friend/Pal-type cards
        don't match a stat type, so they're naturally excluded from the stat counts."""
        pc = (preset or {}).get("_deck_type_counts")
        if isinstance(pc, (list, tuple)) and len(pc) >= 5:
            try:
                return [int(x or 0) for x in pc[:5]]
            except (TypeError, ValueError):
                pass
        counts = [0] * 5
        smap = self._support_map()
        for card in (chara or {}).get("support_card_array") or []:
            info = smap.get(str(card.get("support_card_id") or ""))
            if info:
                idx = SUPPORT_TYPE_INDEX.get(info.get("type"))
                if idx is not None:
                    counts[idx] += 1
        return counts

    def forecast(self, data, preset=None):
        """Predict the career direction from the live chara_info. Always returns a CareerForecast;
        on any missing/garbage data it returns an inactive (no-op) forecast so the caller can fall
        straight back to raw scoring."""
        try:
            return self._forecast(data or {}, preset or {})
        except Exception as exc:  # never let foresight break a run
            return _inactive(reason=f"error: {exc}")

    def _forecast(self, data, preset):
        chara = data.get("chara_info") or {}
        if not chara:
            return _inactive(reason="no chara_info")
        turn = int(chara.get("turn") or 0)

        # 1. Distance aptitude blend (only C+ distances count; weight by grade above the floor).
        apt = {}
        for cat, key in DISTANCE_APT_KEYS.items():
            apt[cat] = int(chara.get(key) or 0)
        ranked = sorted(((c, g) for c, g in apt.items() if g > 0), key=lambda x: (-x[1], x[0]))
        weighted = {c: max(0, g - (APT_GRADE_FLOOR - 1)) for c, g in apt.items() if g >= APT_GRADE_FLOOR}
        if not weighted:
            # No C+ distance aptitude. Only trust a genuine standout (a clear top grade); for a
            # uniformly low/flat spread, default to the balanced 'middle' profile rather than
            # letting the alphabetical tie-break in `ranked` pick the long (max-stamina) profile.
            if ranked and ranked[0][1] >= 2 and (len(ranked) < 2 or ranked[0][1] > ranked[1][1]):
                best = ranked[0][0]
            else:
                best = "middle"
            weighted = {best: 1}

        profile = [0.0] * 5
        total_w = float(sum(weighted.values()))
        for cat, w in weighted.items():
            base = DISTANCE_PROFILES.get(cat, DISTANCE_PROFILES["middle"])
            for i in range(5):
                profile[i] += base[i] * (w / total_w)

        # 2. Running-style nudge.
        style = resolve_running_style(preset, chara)
        for i, adj in enumerate(STYLE_ADJUST.get(style, [0, 0, 0, 0, 0])):
            profile[i] += adj

        caps = [int(chara.get(CAP_KEYS[i]) or BASE_CAP) for i in range(5)]

        # 2b. Deck-aware stat policy: Speed is always maxed; Stamina and Power are pushed to a
        #     1100 baseline ONLY when the deck has enough support cards of that type to train it
        #     efficiently (>= 2 by default). Stats with no support keep their aptitude target.
        deck_counts = self._deck_type_counts(chara, preset)
        deck_targets = []
        # On by default; only an explicit False disables it. NOTE: an explicit per-preset
        # expect_attribute/stat_targets Speed cap still wins in the scorer (mant.py min(game_cap,
        # soft_target)), so "Speed maxed" means "up to the game cap unless the user capped it lower".
        if preset.get("deck_stat_policy", True) is not False:
            profile[0] = max(profile[0], caps[0])  # Speed -> maxed (clamped to the real cap below)
            thr = int(preset.get("secondary_stat_card_threshold") or 2)
            baseline = float(preset.get("secondary_stat_baseline") or 1100)
            for idx, label in ((1, "Stamina"), (2, "Power")):
                if idx < len(deck_counts) and deck_counts[idx] >= thr:
                    profile[idx] = max(profile[idx], baseline)
                    deck_targets.append(label)

        # 3. Clamp to the real in-game caps (raised by inheritance) and a sane floor.
        targets = [int(max(TARGET_FLOOR, min(profile[i], caps[i]))) for i in range(5)]

        # 4. Trajectory: where each stat should be by now vs where it is. Stats accumulate faster
        #    LATE (rainbows ramp up), so the expected-progress curve is back-loaded (convex,
        #    exponent > 1) and only reaches the target near the final training turn (~76). Judged
        #    after the opening turns. Purely informational -- the stat targets already steer
        #    training; this just narrates the predicted direction in logs/UI (scorer never reads it).
        trajectory = []
        denom = 76.0
        frac = min(1.0, (turn / denom) ** 1.25) if turn > 0 else 0.0
        for i in range(5):
            current = int(chara.get(STAT_KEYS[i]) or 0)
            expected = int(targets[i] * frac)
            if turn < 8 or targets[i] <= 0:
                status = "early"
            elif current >= expected * 1.08:
                status = "ahead"
            elif current < expected * 0.80:
                status = "behind"
            else:
                status = "on track"
            trajectory.append({"stat": STAT_NAMES[i], "current": current,
                               "expected": expected, "target": targets[i], "status": status})

        # 5. Labels + human summary. The label reflects the profile actually used (dominant
        #    contributor to the blend), so a flat/low-aptitude uma reads "Middle", not the
        #    alphabetical "Long" tie-break.
        primary = max(weighted, key=weighted.get)
        apt_distances = [(c, g) for c, g in ranked]
        style_name = STYLE_NAMES.get(style, "?")
        archetype = f"{primary.capitalize()} / {style_name}"
        behind = [t["stat"] for t in trajectory if t["status"] == "behind"]
        tgt_str = " ".join(f"{STAT_NAMES[i][:3].upper()} {targets[i]}" for i in range(5))
        strong = [s for s, g in apt_distances if g >= APT_GRADE_FLOOR]
        focus = ", ".join(strong[:2]) if strong else f"no strong aptitude -> {primary}"
        deck_str = (f" Deck [Spd {deck_counts[0]} Sta {deck_counts[1]} Pow {deck_counts[2]}]"
                    if any(deck_counts) else "")
        policy = f" Speed maxed; 1100 secondaries: {', '.join(deck_targets) or 'none'}." if preset.get("deck_stat_policy", True) is not False else ""
        summary = f"Direction: {archetype} (apt: {focus}).{deck_str} Build target -> {tgt_str}.{policy}"
        if behind and turn >= 8:
            summary += f" Behind on: {', '.join(behind)}."

        return CareerForecast(targets, archetype=archetype, key_style=style,
                              apt_distances=apt_distances, trajectory=trajectory,
                              summary=summary, turn=turn, active=True)
