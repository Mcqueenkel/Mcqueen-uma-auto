from career_bot.events import EventManager
from career_bot.scenarios.base import Decision, ScenarioStrategy
from career_bot.foresight import CareerForecaster


STAT_TARGETS = {
    1: 0,
    2: 1,
    3: 2,
    4: 3,
    5: 4,
    30: 5,
}

# Per-stat REAL in-game cap, sent by the game in chara_info. 1200 by default but blue
# inheritance factors / scenario bonuses raise it (1300-1600), so the scorer reads it live
# instead of assuming 1200 -- otherwise it would refuse to train a stat that can still grow.
STAT_CAP_KEYS = {0: "max_speed", 1: "max_stamina", 2: "max_power", 3: "max_guts", 4: "max_wiz"}
BASE_STAT_CAP = 1200  # fallback only, if chara_info somehow lacks the max_* field

TRAINING_COMMANDS = {101: 0, 105: 1, 102: 2, 103: 3, 106: 4, 601: 0, 602: 1, 603: 2, 604: 3, 605: 4}
TRAINING_NAMES = ["Speed", "Stamina", "Power", "Guts", "Wit"]
SUMMER_CAMP_TURNS = {36, 37, 38, 39, 40, 60, 61, 62, 63, 64}
SUMMER_CONSERVE_TURNS = {35, 36, 59, 60}
# Turn-quality lookahead: turns right before the high-yield summer camps / finals, where energy
# is banked regardless of the board so the uma enters the event near full and spends freely.
PRE_EVENT_BANK_TURNS = {33, 34, 35, 57, 58, 59, 71, 72, 73}
SUMMER_CONSERVE_ENERGY = 60
ENERGY_FAST_MEDIC = 80
ENERGY_MEDIC_GENERAL = 85
RACE_SKIP_TRAIN_STAT = 30
ENERGY_ITEM_VALUES = {2001: 20, 2002: 40, 2003: 65, 2101: 100}  # Vita 20/40/65, Royal Kale Juice
GOOD_LUCK_CHARM_ID = 10001
DECK_PARTNERS = {1, 2, 3, 4, 5, 6}
BAD_EFFECT_NAMES = {
    1: "Night Owl",
    2: "Slacker",
    3: "Skin Outbreak",
    4: "Slow Metabolism",
    5: "Migraine",
    6: "Practice Poor",
}


class MantStrategy(ScenarioStrategy):
    scenario_id = 4

    def __init__(self, race_planner=None):
        self.race_planner = race_planner
        self.event_manager = None
        base_dir = self.race_planner.base_dir if self.race_planner else None
        if base_dir:
            self.event_manager = EventManager(base_dir)
        # Forward-looking career planner: predicts the build this career should aim for and
        # feeds per-stat targets into the scorer, so training follows the predicted direction
        # rather than raw single-turn gain. Recomputed each turn in next_decision.
        self.forecaster = CareerForecaster(base_dir)
        self._forecast = None
        # Turn-quality lookahead: rolling history of each turn's best training score, so the
        # rest gate can tell a weak board from a strong one and bank/spend energy accordingly.
        self._score_history = []
        self._quality_last_turn = -1

    def next_decision(self, state, preset):
        data = state.get("data") or {}
        chara = data.get("chara_info") or {}
        home = data.get("home_info") or {}
        if "single_mode_finish_common" in data:
            return Decision("finish", {"current_turn": chara.get("turn", 0)}, "finished")
        events = data.get("unchecked_event_array") or []
        if events:
            event = events[0] or {}
            choice = self._choice(event)
            payload = {"event_id": event.get("event_id"), "chara_id": event.get("chara_id", 0), "choice_number": choice, "current_turn": chara.get("turn", 0)}
            if choice is None:
                payload = {"event_id": event.get("event_id"), "_event": event, "_current_turn": chara.get("turn", 0)}
            return Decision("event", payload, "event")
        if chara.get("state") == 3:
            return Decision("finish", {"current_turn": chara.get("turn", 0)}, "ready to finish")
        race = data.get("race_start_info")
        playing_state = (chara.get("playing_state") or 0)
        if playing_state == 3:
            return Decision("race_progress", {"current_turn": chara.get("turn", 0), "phase": "start", "race_start_info": race, "chara_info": chara}, "resume race start")
        if playing_state == 5:
            return Decision("finish", {"current_turn": chara.get("turn", 0)}, "goal failed / career end")     
        if race and race.get("program_id") and playing_state in (2, 4):
            return Decision("race_progress", {"current_turn": chara.get("turn", 0), "phase": "start", "race_start_info": race, "chara_info": chara}, "race start")
        # Predict the career direction once per turn so the scorer trains toward the build this
        # uma should end on (apt distance + style), not just the biggest raw stat now. Computed
        # BEFORE the race_planner block, since _train_outvalues_race also scores training.
        if preset.get("career_foresight", True):
            self._forecast = self.forecaster.forecast(data, preset)
        else:
            self._forecast = None
        if self.race_planner:
            forced_program_id = self.race_planner.forced_program(state)
            if forced_program_id:
                return Decision("race", {"program_id": forced_program_id, "current_turn": chara.get("turn", 0), "_strategy": self}, self.race_planner.label(forced_program_id))
            program_id = self.race_planner.choose(state, preset)
            if program_id and not self._train_outvalues_race(data, chara, preset, program_id):
                return Decision("race", {"program_id": program_id, "current_turn": chara.get("turn", 0), "_strategy": self}, self.race_planner.label(program_id))
        command = self._best_command(data, chara, preset)
        if command:
            command_type = command.get("command_type", 1)
            command_id = command.get("command_id")
            command_group_id = command.get("command_group_id", 0)
            reason = self._command_reason(command, chara)
            if command_type == 3:
                command_group_id = command_id
                command_id = 0
            return Decision("command", {
                "command_type": command_type,
                "command_id": command_id,
                "command_group_id": command_group_id,
                "select_id": command.get("select_id", 0),
                "current_turn": chara.get("turn", 0),
                "current_vital": chara.get("vital", 0),
            }, reason)
        return Decision("idle", {}, "no action")

    def _choice(self, event):
        choices = ((event.get("event_contents_info") or {}).get("choice_array") or [])
        if not choices:
            return 0
        if len(choices) > 1:
            return None
        return 0

    def choice_from_rewards(self, rewards, event):
        choices = ((event.get("event_contents_info") or {}).get("choice_array") or [])
        if not choices:
            return 0
        if not rewards:
            return choices[0].get("select_index", 1)
        best_index = 0
        best_score = None
        for i, reward in enumerate(rewards):
            score = self._reward_score(reward)
            if best_score is None or score > best_score:
                best_score = score
                best_index = i
        if best_index < len(choices):
            return choices[best_index].get("select_index", best_index + 1)
        return choices[0].get("select_index", 1)

    def _reward_score(self, reward):
        score = 0.0
        for item in reward.get("params_inc_dec_info_array") or reward.get("effected_parameter_array") or []:
            target = STAT_TARGETS.get(item.get("target_type"))
            value = float(item.get("value") or 0)
            if target is None:
                if item.get("target_type") == 10:
                    score += value * 0.03
                continue
            score += value * (0.02 if target < 5 else 0.01)
        score += float(reward.get("skill_point") or 0) * 0.01
        score += float(reward.get("vital") or 0) * 0.03
        return score

    def _best_command(self, data, chara, preset):
        commands = (data.get("home_info") or {}).get("command_info_array") or []
        enabled = [cmd for cmd in commands if cmd.get("is_enable", 1)]
        rest = self._rest_command(enabled)
        recreation = self._recreation_command(enabled)
        medic = self._medic_command(enabled)
        training = [cmd for cmd in enabled if cmd.get("command_type") == 1 and cmd.get("command_id") in TRAINING_COMMANDS]
        turn = int(chara.get("turn") or 0)
        vital = int(chara.get("vital") or 0)
        motivation = int(chara.get("motivation") or 3)
        bad_status = self._has_curable_bad_status(chara, preset)
        if not training:
            if medic and bad_status and vital <= ENERGY_MEDIC_GENERAL:
                return medic
            return rest or recreation
        scored = [(self._score_command(cmd, data, chara, preset), cmd) for cmd in training]
        if 48 < turn <= 72:
            stat_keys = ["speed", "stamina", "power", "guts", "wiz"]
            highest_idx = max(range(5), key=lambda idx: int(chara.get(stat_keys[idx]) or 0))
            scored = [(score * 0.95 if TRAINING_COMMANDS.get(cmd.get("command_id"), 0) == highest_idx and score > 0 else score, cmd) for score, cmd in scored]
        if turn <= 24 and preset.get("junior_bond_rush", True):
            # Junior bond-rush: on non-race training turns, prioritize the training
            # that gathers the most not-yet-maxed support partners (building toward
            # rainbow) over taking an existing rainbow, using the normal score only
            # as a tiebreak. The score magnitude is kept intact so the rest/medic/
            # recreation thresholds below behave exactly as before.
            best_score, best = max(scored, key=lambda row: (self._bondable_count(row[1], chara), row[0]))
        else:
            best_score, best = max(scored, key=lambda row: row[0])
        rest_threshold = int(preset.get("rest_threshold") or 48)
        # Turn-quality lookahead: bank energy on a weak board (rest sooner), push on a strong one.
        # Clamp below max_vital so a rest can always lift energy back above it (no rest deadlock).
        eff_rest = min(self._turn_quality_threshold(best_score, preset, turn),
                       int(chara.get("max_vital") or 100) - 5)
        self._record_turn_quality(turn, best_score)
        failure = int(best.get("failure_rate") or 0)
        if medic and bad_status and vital <= ENERGY_FAST_MEDIC:
            return medic
        if medic and bad_status and vital <= ENERGY_MEDIC_GENERAL:
            return medic
        if turn in SUMMER_CAMP_TURNS and recreation and (vital <= rest_threshold or failure >= 35 or best_score < 0):
            return recreation
        if self._should_recreate(recreation, preset, turn, motivation, vital, best_score):
            return recreation
        if rest and (vital <= eff_rest or failure >= 35 or best_score < 0):
            if not self._can_rescue_training(data, chara, preset, best, best_score, vital, failure, rest_threshold):
                return rest
            # else: a strong/rainbow turn we can charm or energy-up into. Don't rest
            # it away -- fall through to train it. items.py tops up energy with the
            # smallest sufficient Vita (+ charm) before the command executes, and the
            # post-item re-decision then runs the training at the restored energy.
        conserve = self._summer_conserve_command(enabled, turn, vital, best_score, preset, rest, recreation)
        if conserve:
            return conserve
        return best

    def _record_turn_quality(self, turn, best_score):
        """Log this turn's best training score once per turn, for the rolling baseline. Negative
        scores (energy penalties / forbidden-facility sentinels) are skipped so they don't skew it."""
        if best_score is None or best_score < 0 or turn == getattr(self, "_quality_last_turn", -1):
            return
        self._quality_last_turn = turn
        self._score_history.append(float(best_score))
        if len(self._score_history) > 16:
            self._score_history = self._score_history[-16:]

    def _turn_quality_threshold(self, best_score, preset, turn):
        """Turn-quality lookahead -> effective rest threshold.

        The base scorer is greedy, so it would burn a weak turn on mediocre training and then be
        forced to rest on a later strong (rainbow) turn. Instead, compare this turn's best score to
        a rolling baseline of recent turns: on a clearly WEAK board, raise the rest threshold so the
        bot rests now and banks energy for a future strong turn; on a STRONG board, lower it so it
        pushes through (the charm/Vita rescue + failure cap keep that safe). Energy is also banked
        entering the summer camps / finals. Aggressive defaults (tunable via preset)."""
        base = int(preset.get("rest_threshold") or 48)
        # No banking once we're INSIDE the summer camp we banked for -- spend the camp, don't rest it.
        if not preset.get("turn_quality_lookahead", True) or turn in SUMMER_CAMP_TURNS:
            return base
        boost = int(preset.get("turn_quality_rest_boost") or 18)
        if turn in PRE_EVENT_BANK_TURNS:
            base += boost // 2
        hist = self._score_history
        if turn == self._quality_last_turn and hist:
            # _best_command can run twice on a race-candidate turn; this turn's score was already
            # recorded on the first pass, so drop it from the baseline to keep both passes consistent.
            hist = hist[:-1]
        if best_score is None or len(hist) < 4:
            return base
        recent = sorted(hist[-8:])
        baseline = recent[len(recent) // 2]  # median of recent boards
        if baseline <= 0:
            return base
        if best_score < baseline * float(preset.get("turn_quality_weak_ratio") or 0.82):
            return base + boost                      # weak board -> rest eagerly, bank energy
        if best_score > baseline * float(preset.get("turn_quality_strong_ratio") or 1.20):
            return max(30, base - boost)             # strong board -> push, spend energy
        return base

    def _rest_command(self, commands):
        for cmd in commands:
            if cmd.get("command_type") == 7 and cmd.get("command_id") == 701:
                return cmd
        return None

    def _recreation_command(self, commands):
        for cmd in commands:
            if cmd.get("command_type") == 3:
                return cmd
        return None

    def _medic_command(self, commands):
        for cmd in commands:
            if cmd.get("command_type") == 8 and cmd.get("command_id") == 801:
                return cmd
        return None

    def _enabled_training(self, commands, command_id):
        for cmd in commands:
            if cmd.get("command_type") == 1 and cmd.get("command_id") == command_id:
                return cmd
        return None

    def _enabled_training_idx(self, commands, idx):
        for cmd in commands:
            if cmd.get("command_type") == 1 and TRAINING_COMMANDS.get(cmd.get("command_id")) == idx:
                return cmd
        return None

    def _summer_conserve_command(self, enabled, turn, vital, best_score, preset, rest, recreation):
        if turn not in SUMMER_CONSERVE_TURNS:
            return None
        if best_score >= float(preset.get("summer_score_threshold") or 0.34):
            return None
        if vital < SUMMER_CONSERVE_ENERGY:
            if turn in SUMMER_CAMP_TURNS and recreation:
                return recreation
            return rest
        return self._enabled_training_idx(enabled, 4)

    def _has_curable_bad_status(self, chara, preset):
        wanted = self._cure_condition_names(preset)
        if not wanted:
            return False
        for effect_id in chara.get("chara_effect_id_array") or []:
            try:
                effect_id = int(effect_id)
            except (TypeError, ValueError):
                continue
            name = BAD_EFFECT_NAMES.get(effect_id)
            if name and self._condition_key(name) in wanted:
                return True
        return False

    def _cure_condition_names(self, preset):
        result = set()
        names = preset.get("cure_asap_conditions") or []
        if isinstance(names, str):
            names = names.split(",")
        for name in names:
            key = self._condition_key(name)
            if key:
                result.add(key)
        return result

    def _condition_key(self, name):
        text = str(name or "").strip()
        if not text or text.startswith("("):
            return ""
        return "".join(ch.lower() for ch in text if ch.isalnum())

    def _command_reason(self, command, chara=None):
        command_type = command.get("command_type")
        command_id = command.get("command_id")
        if command_id in TRAINING_COMMANDS:
            label = f"training {TRAINING_NAMES[TRAINING_COMMANDS.get(command_id, 0)]} {command_id}"
            if chara is not None:
                rc = self._rainbow_count(command, chara)
                if rc:
                    label += f" [{rc} rainbow]"
            return label
        if command_type == 7 and command_id == 701:
            return f"rest {command_id}"
        if command_type == 3:
            return f"recreation {command_id}"
        if command_type == 8 and command_id == 801:
            return "medic 801"
        return f"command {command_type}:{command_id}"

    def _score_command(self, command, data, chara, preset):
        turn = int(chara.get("turn") or 0)
        weights = self._period_row(preset.get("score_value"), turn, [0.11, 0.10, 0.006, 0.09])
        base = preset.get("base_score") or [0, 0, 0, 0, 0]
        targets = preset.get("expect_attribute") or [9999, 9999, 9999, 9999, 9999]
        # Career foresight: when the preset sets no explicit per-stat soft caps, steer training
        # toward the predicted end-build (apt distance + style) instead of leaving stats uncapped.
        # The min(game_cap, target) logic below still applies, so these never exceed the real caps.
        forecast = getattr(self, "_forecast", None)
        if forecast is not None and forecast.active:
            # Fill only the stats the preset left unset (>=9999) with the predicted target, so a
            # partial focused-build override (e.g. an explicit Stamina cap) keeps foresight on the rest.
            targets = [int(t) if int(t) < 9999 else forecast.stat_targets[i] for i, t in enumerate(targets)]
        idx = TRAINING_COMMANDS.get(command.get("command_id"), 0)
        score = float(base[idx] if idx < len(base) else 0)
        w_lv1 = float(weights[0] if len(weights) > 0 else 0.11)
        w_lv2 = float(weights[1] if len(weights) > 1 else 0.10)
        w_energy = float(weights[2] if len(weights) > 2 else 0.006)
        w_hint = float(weights[3] if len(weights) > 3 else 0.09)
        stat_mult = preset.get("stat_value_multiplier") or [0.01, 0.01, 0.01, 0.01, 0.01, 0.005]
        bonds = self._bond_map(chara)
        partners = command.get("training_partner_array") or []
        hints = set(command.get("tips_event_partner_array") or [])
        pal_count = 0
        hint_count = 0
        rainbow_count = 0
        useful_stat_score = 0.0
        # Rainbow-unlock lookahead: one cheap step of planning past the greedy single-turn
        # score. Training a deck support that sits just under bond 80 pushes it toward the
        # rainbow (friendship-training) threshold, which then fires on EVERY future
        # appearance of that card -- the single biggest stat lever in MANT/URA. Greedy
        # scoring gives the crossing turn no credit (rainbow_count only rewards supports
        # ALREADY >=80), so the bot can spread bond thinly and reach rainbow state late.
        # This accumulates a bounded premium for crossing, strongest when the support is
        # close to 80 (one training flips it) and early (more future appearances to cash in).
        rainbow_unlock_score = 0.0
        rainbow_lookahead = preset.get("rainbow_unlock_lookahead", True)
        unlock_lo = float(preset.get("rainbow_unlock_band_lo") or 40)
        unlock_base = float(preset.get("rainbow_unlock_bonus") or 0.12)
        for partner_id in partners:
            bond = bonds.get(partner_id, 0)
            if partner_id in hints:
                hint_count += 1

            if bond >= 80:
                # Maxed support on this training is delivering a rainbow (friendship
                # training) this turn. There is no more bond to build, so it adds no
                # bond value, but we count it for the explicit rainbow reward below.
                if partner_id in DECK_PARTNERS:
                    rainbow_count += 1
                continue

            time_decay = max(0.0, (72 - turn) / 72.0)
            efficiency_boost = 1.0 + (bond / 80.0) * 0.5 if bond >= 60 else 1.0
            
            weight = time_decay * efficiency_boost

            if partner_id not in DECK_PARTNERS:
                yield_val = self._npc_score(bond, turn, preset)
                score += yield_val * weight
                continue

            if partner_id == 6:
                pal_count += 1
                yield_val = self._pal_score(bond, preset)
                score += yield_val * weight
                continue

            ratio = min(1.0, bond / 80.0)
            yield_val = w_lv1 + (w_lv2 - w_lv1) * ratio
            score += yield_val * weight
            if rainbow_lookahead and unlock_lo <= bond < 80:
                # Proximity ramps 0 (band start) -> ~1 (just under 80): the closer to the
                # threshold, the likelier this single training crosses it. time_decay (set
                # above) front-loads the bonus so we secure rainbows while they still pay off.
                proximity = (bond - unlock_lo) / max(1.0, 80.0 - unlock_lo)
                rainbow_unlock_score += unlock_base * proximity * time_decay
        if hint_count:
            # More skill hints on one training = more skill points / discounts, so scale
            # the hint reward by how many partners are hinting (gently, capped at 4)
            # instead of a flat bonus for "at least one hint".
            hint_scale = float(preset.get("hint_count_scale") or 0.5)
            score += w_hint * (1.0 + hint_scale * (min(hint_count, 4) - 1))
        for item in command.get("params_inc_dec_info_array") or []:
            value = float(item.get("value") or 0)
            if item.get("target_type") == 10:
                energy_score = value * w_energy
                if int(chara.get("vital") or 0) >= 80 and value < 0:
                    energy_score *= 0.9
                score += energy_score
                continue
            target = STAT_TARGETS.get(item.get("target_type"))
            if target is None:
                continue
            if target == 5:
                # Skill points are NOT scored by default -- the bot chases the biggest raw
                # STAT gain instead, and whatever SP accumulates is spent at career end by
                # the leftover-SP skill dump. Opt back in with preset "score_skill_points"
                # (uses stat_value_multiplier[5] * skill_point_weight) if you want training
                # to actively favour SP-rich turns.
                if preset.get("score_skill_points", False) and value > 0:
                    sp_mult = float(stat_mult[5] if len(stat_mult) > 5 else 0.005)
                    sp_score = value * sp_mult * float(preset.get("skill_point_weight") or 1.0)
                    score += sp_score
                    useful_stat_score += max(0.0, sp_score)
                continue

            stat_mult_val = float(stat_mult[target] if target < len(stat_mult) else 0.01)
            stat_gain_score = value * stat_mult_val
            # Effective ceiling = the stat's REAL in-game cap (raised by inheritance), tightened
            # by an optional per-preset soft target for focused builds. Reading the live cap is
            # what activates the attenuation ladder + balance boost below without wrongly
            # throttling a cap-raised uma at a flat 1200.
            soft = float(targets[target] if target < len(targets) else 9999)
            game_cap = float(chara.get(STAT_CAP_KEYS.get(target)) or BASE_STAT_CAP)
            cap = min(game_cap, soft)
            if cap > 0 and target < 5:
                current = self._current_stat(chara, target)
                ratio = current / cap
                if ratio > 1.0:
                    stat_gain_score *= 0.0
                elif ratio > 0.97:
                    stat_gain_score *= 0.35 - ((ratio - 0.97) / 0.03) * 0.25
                elif ratio > 0.94:
                    stat_gain_score *= 0.55 - ((ratio - 0.94) / 0.03) * 0.20
                elif ratio > 0.90:
                    stat_gain_score *= 0.75 - ((ratio - 0.90) / 0.04) * 0.20
                elif ratio > 0.86:
                    stat_gain_score *= 0.85 - ((ratio - 0.86) / 0.04) * 0.10
                elif ratio > 0.82:
                    stat_gain_score *= 0.91 - ((ratio - 0.82) / 0.04) * 0.06
                elif ratio > 0.78:
                    stat_gain_score *= 0.95 - ((ratio - 0.78) / 0.04) * 0.04
                elif ratio > 0.74:
                    stat_gain_score *= 0.98 - ((ratio - 0.74) / 0.04) * 0.03
                elif ratio > 0.70:
                    stat_gain_score *= 1.00 - ((ratio - 0.70) / 0.04) * 0.02
                elif preset.get("stat_balance", True) and cap < 9000:
                    # Under-target boost: nudge the bot to FILL a stat that sits far
                    # below its target instead of piling onto near-capped stats, so the
                    # final build is balanced (not lopsided). The further under target,
                    # the bigger the nudge (capped). Active by default now that targets
                    # default to the 1200 stat cap (cap < 9000); complements the cap-based
                    # down-weighting above. Disable with preset "stat_balance": false.
                    thr = float(preset.get("stat_balance_threshold") or 0.55)
                    if ratio < thr:
                        stat_gain_score *= 1.0 + (thr - ratio) * float(preset.get("stat_balance_boost") or 0.6)
            score += stat_gain_score
            # The rainbow/unlock attenuation below keys off useful_stat_score. It must reflect
            # whether the stat is TRULY near its real in-game cap (genuinely wasted gain), NOT
            # merely de-prioritised below a tighter soft forecast/user target -- otherwise a
            # multi-rainbow turn on an off-build stat (e.g. Stamina for a sprinter) would collapse
            # to zero once that stat crept past its low soft target, throwing away the turn's
            # bond/friendship value. So when a soft target is tighter than the game cap, measure
            # headroom against the GAME cap; otherwise keep the soft-attenuated score.
            if target < 5 and cap < game_cap and game_cap > 0:
                game_headroom = max(0.0, 1.0 - self._current_stat(chara, target) / game_cap)
                useful_stat_score += max(0.0, value * stat_mult_val * game_headroom)
            else:
                useful_stat_score += max(0.0, stat_gain_score)
        # Shared "useful stat" attenuation: how much non-capped stat this turn actually
        # yields, relative to a reference. Both the rainbow reward and the bond-unlock
        # premium are gated by it so the bot never chases bond/rainbow on a facility whose
        # stat is already capped (zero useful gain -> zero bond/rainbow incentive).
        ref = float(preset.get("rainbow_useful_ref") or 0.12)
        atten = 1.0 if ref <= 0 else min(1.0, useful_stat_score / ref)
        if rainbow_count and preset.get("rainbow_explicit", True):
            # Explicit rainbow (friendship-training) reward. The reported stat gain
            # already includes the friendship bonus, but the bond loop gives a maxed
            # support zero value, which can make the bot pass up a multi-rainbow turn
            # to keep building bond elsewhere. Add a tunable per-rainbow bonus.
            # Failure compensation, period extra-weight and deck multipliers below apply too.
            per = float(preset.get("rainbow_bonus") or 0.12)
            stack = float(preset.get("rainbow_stack_bonus") or 0.06)
            score += (per * rainbow_count + stack * max(0, rainbow_count - 1)) * atten
        if rainbow_unlock_score:
            # Bond-crossing premium: cap it (so many in-band supports can't dominate a turn)
            # and gate by the same useful-stat factor, then add it here so the pal multiplier
            # and failure compensation below still apply -- we never force a high-failure or
            # already-capped training just because it would tip a support toward rainbow range.
            cap_premium = float(preset.get("rainbow_unlock_cap") or (unlock_base * 2.0))
            score += min(rainbow_unlock_score, cap_premium) * atten
        if pal_count:
            score *= 1.0 + max(0.0, min(1.0, float(preset.get("pal_card_multiplier") or 0.1)))
        if preset.get("compensate_failure", True):
            score *= max(0.0, 1.0 - (float(command.get("failure_rate") or 0) / 50.0))
        if idx == 4:
            vital = int(chara.get("vital") or 0)
            max_vital = int(chara.get("max_vital") or 100)
            gain = 0
            for item in command.get("params_inc_dec_info_array") or []:
                if item.get("target_type") == 10:
                    gain = float(item.get("value") or 0)
                    break
            if vital >= max_vital or (gain > 0 and vital + gain > max_vital):
                score *= 0.35 if turn > 72 else 0.75
            elif vital < 85:
                # Wit also restores energy, so prefer it MORE the lower energy gets --
                # recovering via Wit (which still trains + gives skills/SP) beats wasting
                # a whole rest turn. Scales from ~1.0 near full to a tunable cap when low.
                low = (85 - vital) / 85.0
                score *= 1.0 + low * float(preset.get("wit_energy_boost") or 0.25)
        extra = self._extra_weight(idx, turn, preset)
        if extra == -1:
            return -999.0
        score *= max(0.0, min(2.0, 1.0 + extra))

        if turn < 60:
            deck_mults = preset.get("_deck_multipliers")
            if deck_mults and len(deck_mults) > idx:
                score *= float(deck_mults[idx])

        return score

    def _current_stat(self, chara, target):
        keys = ["speed", "stamina", "power", "guts", "wiz", "skill_point"]
        return float(chara.get(keys[target], 0) or 0)

    def _team_command(self, data, command_id):
        team_data = data.get("team_data_set") or {}
        for cmd in team_data.get("command_info_array") or []:
            if cmd.get("command_id") == command_id:
                return cmd
        return None

    def _bond_map(self, chara):
        result = {}
        for row in chara.get("evaluation_info_array") or []:
            result[row.get("target_id", 0)] = row.get("evaluation", 0)
        return result

    def _bondable_count(self, command, chara):
        """How many deck support partners on this training still need bonding.

        A partner already at max bond (>= 80) contributes a rainbow but no longer
        builds friendship, so it does not count toward the Junior bond-rush. The
        friend/pal slot (6) counts too since it also unlocks rainbow training.
        """
        bonds = self._bond_map(chara)
        count = 0
        for partner_id in command.get("training_partner_array") or []:
            if partner_id in DECK_PARTNERS and int(bonds.get(partner_id, 0) or 0) < 80:
                count += 1
        return count

    def _rainbow_count(self, command, chara):
        """How many deck supports on this training are at max bond (>=80) = rainbows.

        A maxed support present on a training delivers a friendship-training
        ("rainbow") bonus; stacking several on one training is the biggest stat turn
        in the game. NPCs (not in DECK_PARTNERS) don't trigger friendship training.
        """
        bonds = self._bond_map(chara)
        count = 0
        for partner_id in command.get("training_partner_array") or []:
            if partner_id in DECK_PARTNERS and int(bonds.get(partner_id, 0) or 0) >= 80:
                count += 1
        return count

    def _owned_item_count(self, data, item_id):
        total = 0
        for row in (data.get("free_data_set") or {}).get("user_item_info_array") or []:
            if int(row.get("item_id") or 0) == int(item_id):
                total += int(row.get("num") or row.get("current_num") or row.get("item_num") or 0)
        return total

    def _rescue_energy_value(self, data, vital, rest_threshold, margin):
        """Restore value of the SMALLEST owned energy item that would lift vital
        comfortably above the rest threshold, or None if none owned can do it. Used
        to decide whether a low-energy turn can be rescued into a training."""
        target = rest_threshold + margin
        owned = {}
        for row in (data.get("free_data_set") or {}).get("user_item_info_array") or []:
            iid = int(row.get("item_id") or 0)
            if iid in ENERGY_ITEM_VALUES:
                owned[iid] = owned.get(iid, 0) + int(row.get("num") or row.get("current_num") or row.get("item_num") or 0)
        best = None
        for iid, qty in owned.items():
            if qty > 0 and vital + ENERGY_ITEM_VALUES[iid] > target:
                if best is None or ENERGY_ITEM_VALUES[iid] < ENERGY_ITEM_VALUES[best]:
                    best = iid
        return ENERGY_ITEM_VALUES[best] if best is not None else None

    def _can_rescue_training(self, data, chara, preset, best, best_score, vital, failure, rest_threshold):
        """Spend a charm / energy item to RUN a strong training instead of resting it
        away for low energy or high failure? Only for a genuinely good turn (a rainbow
        or a high cap-aware score), only when energy isn't critically low, and only
        when we actually own the mitigation that can clear the blocker: an energy item
        big enough to beat the vital floor, or a charm/energy when only failure is high.
        Mirrors items.py _rescue_energy_target so the post-item re-decision agrees."""
        if not preset.get("rescue_good_training", True):
            return False
        if best is None or int(best.get("command_type") or 0) != 1:
            return False
        if best_score is None or best_score <= 0:
            return False
        if vital < int(preset.get("rescue_min_vital") or 25):
            return False
        rainbow = self._rainbow_count(best, chara)
        strong = best_score >= float(preset.get("rescue_score_threshold") or 0.55)
        if rainbow < 1 and not strong:
            return False
        margin = int(preset.get("rescue_vital_margin") or 12)
        energy_val = self._rescue_energy_value(data, vital, rest_threshold, margin)
        has_charm = self._owned_item_count(data, GOOD_LUCK_CHARM_ID) > 0
        hard_cap = int(preset.get("failure_hard_cap") or 50)
        if failure >= hard_cap:
            # Absolute failure ceiling: above the cap only a Good-Luck Charm (which forces
            # a verified 0%) may rescue the turn -- an energy bump does NOT guarantee the
            # failure drops below the cap, so we never gamble a high-intensity facility on
            # it. With no charm we rest instead. (A pro run was seen training at 99%.)
            return has_charm
        if vital <= rest_threshold:
            # only an energy item can lift vital back over the rest threshold
            return energy_val is not None
        if failure >= 35:
            # vital is fine, just the (possibly stale) failure is high -> charm/energy fixes it
            return has_charm or energy_val is not None
        return False

    def _command_stat_gain(self, command):
        """Raw stat points a training yields this turn (Speed/Stamina/Power/Guts/Wit).

        This is the "jumlah training" the player thinks in: a 2-rainbow turn lands
        around 30+. Skill points are not counted; the stat cap is not considered.
        """
        total = 0
        for item in command.get("params_inc_dec_info_array") or []:
            if item.get("target_type") in (1, 2, 3, 4, 5):
                total += int(item.get("value") or 0)
        if total == 0:
            for field in ["speed", "stamina", "power", "guts", "wiz"]:
                total += int(command.get(field) or 0)
        return total

    def _is_g1_program(self, program_id):
        """Is this race a G1? (race_instance_id starting with '1' is the codebase's
        G1 convention, same as the item/cleat logic.)"""
        if not self.race_planner or not program_id:
            return False
        info = (self.race_planner.program or {}).get(int(program_id or 0)) or {}
        return str(info.get("race_instance_id") or "").startswith("1")

    def _train_outvalues_race(self, data, chara, preset, program_id=0):
        """Should a scheduled race be skipped in favor of training this turn?

        Never for a G1 race -- those are too valuable to pass up, so the bot always
        runs a scheduled G1 regardless of how good the training is. Otherwise True
        only when (a) some enabled training yields >= the configured raw stat
        threshold (default 30 = ~2 rainbow), and (b) the bot would actually train
        (not rest/recreate for low energy/mood). Applies to wanted and fan races.
        """
        if self._is_g1_program(program_id):
            return False
        threshold = preset.get("race_skip_train_stat", RACE_SKIP_TRAIN_STAT)
        if not threshold:
            return False
        commands = (data.get("home_info") or {}).get("command_info_array") or []
        training = [
            cmd for cmd in commands
            if cmd.get("is_enable", 1) and cmd.get("command_type") == 1 and cmd.get("command_id") in TRAINING_COMMANDS
        ]
        if not training:
            return False
        best_stat = max(self._command_stat_gain(cmd) for cmd in training)
        if best_stat < float(threshold):
            return False
        command = self._best_command(data, chara, preset)
        return bool(command) and int(command.get("command_type") or 0) == 1

    def _npc_score(self, bond, turn, preset):
        if bond >= 80:
            return 0.0
        row = self._period_row(preset.get("npc_score_value"), turn, [0.05, 0.05, 0.05])
        v1 = float(row[0] if len(row) > 0 else 0.05)
        v2 = float(row[1] if len(row) > 1 else v1)
        ratio = min(1.0, bond / 80.0)
        return v1 + (v2 - v1) * ratio

    def _pal_score(self, bond, preset):
        if bond >= 80:
            return 0.0
        scores = preset.get("pal_friendship_score") or [0.08, 0.057, 0.018]
        v1 = float(scores[0] if len(scores) > 0 else 0.08)
        v2 = float(scores[1] if len(scores) > 1 else v1)
        ratio = min(1.0, bond / 80.0)
        return v1 + (v2 - v1) * ratio

    def _period_index(self, turn):
        if turn <= 24:
            return 0
        if turn <= 48:
            return 1
        if turn <= 60:
            return 2
        if turn <= 72:
            return 3
        return 4

    def _period_row(self, rows, turn, fallback):
        if not isinstance(rows, list) or not rows:
            return fallback
        idx = min(self._period_index(turn), len(rows) - 1)
        row = rows[idx]
        return row if isinstance(row, list) else fallback

    def _extra_weight(self, idx, turn, preset):
        rows = preset.get("extra_weight") or [[0, 0, 0, 0, 0]] * 4
        if turn <= 24:
            row_idx = 0
        elif turn <= 48:
            row_idx = 1
        elif turn in SUMMER_CAMP_TURNS and len(rows) >= 4:
            row_idx = 3
        else:
            row_idx = 2
        if row_idx >= len(rows) or not isinstance(rows[row_idx], list) or idx >= len(rows[row_idx]):
            return 0.0
        return float(rows[row_idx][idx] or 0)

    def _mood_threshold(self, turn, preset):
        if turn <= 36:
            return int(preset.get("motivation_threshold_year1") or 3)
        if turn <= 60:
            return int(preset.get("motivation_threshold_year2") or 4)
        return int(preset.get("motivation_threshold_year3") or 4)

    def _should_recreate(self, recreation, preset, turn, motivation, vital, best_score):
        if not recreation:
            return False
        if turn in SUMMER_CAMP_TURNS:
            return False
        # Opt-in: proactively top mood up to GREAT (motivation 5) on weak, energy-spare
        # training turns -- a strong-run habit (the GREAT multiplier on the next good turn
        # outvalues a mediocre training now). Default off; never fires on a rainbow/strong
        # turn (gated by best_score) or when energy is near full.
        if preset.get("mood_target_recreate") and motivation < 5 and vital < 90 \
                and best_score <= float(preset.get("mood_recreate_max_score") or 0.30):
            return True
        if motivation < self._mood_threshold(turn, preset) and vital < 90 and best_score <= 0.3:
            return True
        if not preset.get("prioritize_recreation"):
            return False
        thresholds = preset.get("pal_thresholds") or []
        if not thresholds:
            return False
        stage = int(preset.get("_pal_event_stage") or 0)
        if stage >= len(thresholds):
            stage = 0
        row = thresholds[stage]
        if not isinstance(row, list) or len(row) < 2:
            return False
        mood_ok = motivation <= int(row[0])
        energy_ok = vital <= int(row[1])
        score_ok = True
        if len(row) > 2:
            score_ok = best_score <= float(row[2])
        return mood_ok and energy_ok and score_ok

    def choose_from_event(self, event, current_turn):
        if self.event_manager:
            return self.event_manager.choose(event)
        return 1
