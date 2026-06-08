from career_bot.scenarios.mant import MantStrategy


class UraStrategy(MantStrategy):
    """URA Finale scenario (scenario_id 1).

    URA Finale reuses MantStrategy's entire training brain unchanged. This is sound
    because the two scenarios share the SAME 78-turn calendar byte-for-byte (verified
    against master.mdb single_mode_turn for turn_set 1 vs 4): Junior pre-debut turns
    1-12, summer camps at turns 37-40 and 61-64, and the finals period at turns 73-78
    with the 3 finals on turns 74/76/78. So every MANT calendar constant
    (SUMMER_CAMP_TURNS, the 24/48/72 year boundaries, the turn-77 stop) transfers as-is,
    and the cap-aware command scorer, bond/rainbow logic, rest/recreate/medic gates and
    energy-rescue all carry no MANT-specific data.

    The MANT-only machinery (coin shop, grade points, cleat hammers, megaphones, Glow
    Sticks, Twinkle-Climax race-overwrite) is gated behind `scenario_id == 4` in the
    runner (`_handle_items`, `_race`) and the race planner (rival overwrite), so a URA
    career skips all of it automatically with no further changes.

    The ONE URA-specific behaviour: URA goal races are MANDATORY per-character races --
    missing one fails the whole career -- unlike MANT's generic, easily-cleared goal
    markers. So URA must never trade a chosen race for a strong training. We force this
    by disabling the train-outvalues-race skip (tunable via preset `ura_force_races`).
    """

    scenario_id = 1

    def _train_outvalues_race(self, data, chara, preset, program_id=0):
        # URA goal races are mandatory: by default never skip a race the planner chose in
        # favour of training, or the run can fail a goal. (forced_program already covers
        # race-only turns; this covers turns that offer both race and training.)
        if (preset or {}).get("ura_force_races", True):
            return False
        return super()._train_outvalues_race(data, chara, preset, program_id)
