import math
import random
import time
import hashlib
import os

_BASE_DELAYS = {
    'load_index': (1.16, 14.69, 5.26),
    'load_career': (0.62, 7.64, 2.56),
    'pre_single_mode': (1.80, 25.95, 2.03),
    'start_career': (1.58, 6.23, 1.98),
    'start_session': (0.62, 4.55, 1.06),
    'pre_signup': (0.62, 4.55, 1.06),
    'signup': (0.62, 4.55, 1.06),
    'check_event': (1.11, 3.90, 1.88),
    'continue': (0.96, 4.82, 3.05),
    'exec_command': (2.86, 17.68, 4.82),
    'finish_career': (3.05, 15.49, 3.54),
    'gain_skills': (7.02, 99.37, 54.62),
    'read_info': (1.16, 14.69, 5.26),
    'recovery_trainer_point': (0.62, 4.55, 1.06),
    'multi_item_exchange': (4.20, 13.79, 8.29),
    'multi_item_use': (2.99, 9.87, 5.67),
    'minigame_end': (1.11, 3.90, 1.88),
    'race_end': (1.85, 3.90, 2.01),
    'race_entry': (0.73, 4.94, 0.78),
    'change_running_style': (0.73, 4.94, 0.78),
    'reserve_race': (2.78, 9.26, 4.90),
    'race_out': (2.20, 9.91, 3.79),
    'race_start': (1.93, 10.36, 3.46),
}

import threading

_dna_path = os.path.join(os.path.dirname(__file__), '.timing_dna')
if not os.path.exists(_dna_path):
    with open(_dna_path, 'w') as f:
        f.write(str(random.randint(1000000, 9999999)))

with open(_dna_path, 'r') as f:
    _dna_seed = int(f.read().strip())

# These stay module-level globals on purpose: the Web UI toggles them at runtime
# (see set_turn_delay/get_turn_delay in main.py) and they apply to every account.
# Per-turn pause (between turns). Raised well above the realistic 2.5-5s so a
# full career stretches to ~45-50 min (more human, less bot-like). Adjustable
# from the Web UI; these are the startup defaults.
TURN_DELAY_MIN = 12.0
TURN_DELAY_MAX = 24.0
TURN_DELAY_RESTORE_MIN = 12.0
TURN_DELAY_RESTORE_MAX = 24.0
GLOBAL_DELAYS_DISABLED = False

# Per-action ("button press") delay scale. 1.0 = realistic human pacing,
# >1 = slower, <1 = faster (0.5 = 2x faster). Set to 1.2 so per-action timing is
# slightly above realistic; together with the longer turn delay above this puts
# a full career around 45-50 min. Keeps the human-like variation/jitter. Only
# affects simulate_delay, NOT the per-turn delay.
ACTION_DELAY_SCALE = 1.2


class TimingDNA:
    """A self-contained, thread-safe "timing personality".

    Each account gets its own instance (seeded from its viewer_id) so two
    accounts never share an identical timing fingerprint, and two runner
    threads never touch the same RNG state at the same time.
    """

    _registry = {}
    _registry_lock = threading.Lock()

    def __init__(self, seed):
        self.seed = int(seed)
        self.lock = threading.RLock()
        self.rng = random.Random(self.seed)
        r = self.rng
        # Persona is derived in this exact draw order so the default instance
        # reproduces the historical single-account timing stream byte-for-byte.
        self.sigma = r.uniform(0.45, 0.75)
        self.speed_shift = r.uniform(0.92, 1.08)
        self.distraction_chance = r.uniform(0.015, 0.065)
        self.distraction_min = r.uniform(1.5, 3.5)
        self.distraction_max = r.uniform(7.0, 14.0)
        self.endpoint_shifts = {ep: r.uniform(0.85, 1.15) for ep in _BASE_DELAYS}

    @classmethod
    def for_account(cls, viewer_id):
        """Return the stable, distinct personality for a given account.

        The seed mixes the per-install seed with the viewer_id, so the same
        account always gets the same ritme while different accounts diverge.
        """
        key = int(viewer_id or 0)
        with cls._registry_lock:
            dna = cls._registry.get(key)
            if dna is None:
                mixed = hashlib.sha256(f"{_dna_seed}:{key}".encode()).hexdigest()
                dna = cls(int(mixed[:12], 16))
                cls._registry[key] = dna
            return dna

    # ---- thread-safe RNG primitives ----
    def uniform(self, a, b):
        with self.lock:
            return self.rng.uniform(a, b)

    def gauss(self, mean, stddev):
        with self.lock:
            return self.rng.gauss(mean, stddev)

    def randint(self, a, b):
        with self.lock:
            return self.rng.randint(a, b)

    def _lognorm(self, mu, sigma):
        with self.lock:
            return self.rng.lognormvariate(mu, sigma)

    def _chance(self):
        with self.lock:
            return self.rng.random()

    # ---- sleeps ----
    def sleep(self, min_val, max_val, mean=None, stddev=None):
        if GLOBAL_DELAYS_DISABLED:
            return 0.0
        if mean is not None and stddev is not None:
            dt = max(min_val, min(max_val, self.gauss(mean, stddev)))
        else:
            dt = self.uniform(min_val, max_val)
        time.sleep(dt)
        return dt

    def jittered_sleep(self, seconds, spread=0.3):
        """Sleep around `seconds` with +/- `spread` random jitter so two retries
        never wait for an identical duration (an obvious bot fingerprint)."""
        if GLOBAL_DELAYS_DISABLED:
            return 0.0
        seconds = max(0.0, float(seconds))
        spread = min(0.95, max(0.0, float(spread)))
        dt = max(0.0, self.uniform(seconds * (1.0 - spread), seconds * (1.0 + spread)))
        time.sleep(dt)
        return dt

    def backoff_sleep(self, attempt, base=1.0, cap=15.0, factor=2.0):
        """Exponential backoff with "equal jitter": grows with `attempt` up to
        `cap`, always at least half the exponential target, never identical."""
        if GLOBAL_DELAYS_DISABLED:
            return 0.0
        attempt = max(0, int(attempt))
        base = max(0.0, float(base))
        cap = max(base, float(cap))
        target = min(cap, base * (factor ** attempt))
        half = target / 2.0
        dt = min(cap, max(0.0, half + self.uniform(0.0, half)))
        time.sleep(dt)
        return dt

    def simulate_delay(self, endpoint, client=None):
        if GLOBAL_DELAYS_DISABLED:
            print(f"Endpoint: {endpoint} | Delay: 0.000s", flush=True)
            return 0.0

        if endpoint not in _BASE_DELAYS:
            target_delay = 0.3 * self.speed_shift
            mu = math.log(target_delay) - (self.sigma ** 2) / 2.0
            dt = self._lognorm(mu, self.sigma)
            dt = max(0.08, min(1.2, dt))
        else:
            real_min, real_max, real_avg = _BASE_DELAYS[endpoint]
            ep_shift = self.endpoint_shifts[endpoint]
            target_delay = real_avg * self.speed_shift * ep_shift
            shifted_min = real_min * self.speed_shift * ep_shift
            shifted_max = real_max * self.speed_shift * ep_shift
            mu = math.log(target_delay) - (self.sigma ** 2) / 2.0
            dt = self._lognorm(mu, self.sigma)
            dt = max(shifted_min, min(shifted_max, dt))

        if self._chance() < self.distraction_chance:
            dt += self.uniform(self.distraction_min, self.distraction_max)

        dt *= ACTION_DELAY_SCALE

        print(f"Endpoint: {endpoint} | Delay: {dt:.3f}s", flush=True)

        if client is not None and hasattr(client, '_last_raw_call_ts'):
            elapsed = time.time() - client._last_raw_call_ts
            actual_sleep = dt - elapsed
            if actual_sleep > 0:
                time.sleep(actual_sleep)
        else:
            time.sleep(dt)
        return dt

    def simulate_turn_delay(self):
        if GLOBAL_DELAYS_DISABLED:
            print(f"Endpoint: turn_delay | Delay: 0.000s", flush=True)
            return 0.0
        range_span = TURN_DELAY_MAX - TURN_DELAY_MIN
        target_mean = (((TURN_DELAY_MIN + TURN_DELAY_MAX) / 2.0) + (self.uniform(-0.08, 0.08) * range_span)) * self.speed_shift
        sigma = 0.75 * self.sigma
        mu = math.log(max(0.1, target_mean)) - (sigma ** 2) / 2.0
        dt = self._lognorm(mu, sigma)
        dt = min(TURN_DELAY_MAX * 5.0, max(TURN_DELAY_MIN * 0.5, dt))

        print(f"Endpoint: turn_delay | Delay: {dt:.3f}s", flush=True)
        time.sleep(dt)
        return dt


# The default personality (seeded from .timing_dna) preserves the historical
# single-account behavior. All bare module-level helpers route here unless a
# per-account DNA is bound to the current thread via use_dna().
_default_dna = TimingDNA(_dna_seed)

_active = threading.local()


def use_dna(dna):
    """Bind `dna` as the active personality for the current thread.

    Each account's runner runs in its own thread, so binding once makes every
    subsequent bare delay call in that thread use the right account's timing.
    """
    _active.dna = dna


def current_dna():
    return getattr(_active, "dna", None) or _default_dna


def simulate_delay(endpoint, client=None):
    return current_dna().simulate_delay(endpoint, client)


def simulate_turn_delay():
    return current_dna().simulate_turn_delay()


def dna_randint(min_val, max_val):
    return current_dna().randint(min_val, max_val)


def dna_sleep(min_val, max_val, mean=None, stddev=None):
    return current_dna().sleep(min_val, max_val, mean, stddev)


def dna_uniform(min_val, max_val):
    return current_dna().uniform(min_val, max_val)


def dna_gauss(mean, stddev):
    return current_dna().gauss(mean, stddev)


def jittered_sleep(seconds, spread=0.3):
    return current_dna().jittered_sleep(seconds, spread)


def backoff_sleep(attempt, base=1.0, cap=15.0, factor=2.0):
    return current_dna().backoff_sleep(attempt, base=base, cap=cap, factor=factor)


class GateKeeper:
    def __init__(self, client, dna=None):
        super().__setattr__('_client', client)
        raw_call = getattr(client, '_gatekeeper_raw_call', None)
        if raw_call is None:
            raw_call = client.call
            setattr(client, '_gatekeeper_raw_call', raw_call)
        super().__setattr__('_raw_call', raw_call)
        if dna is None:
            viewer_id = getattr(client, 'viewer_id', 0)
            dna = TimingDNA.for_account(viewer_id) if viewer_id else _default_dna
        super().__setattr__('_dna', dna)
        use_dna(dna)
        client.call = self._paced_call

    def wait_turn_delay(self):
        use_dna(self._dna)
        self._dna.simulate_turn_delay()

    def wait_complex_delay(self):
        pass

    def __setattr__(self, name, value):
        if name in ('_client', '_raw_call', '_dna'):
            super().__setattr__(name, value)
        else:
            setattr(self._client, name, value)

    def _pacing_name(self, ep):
        path_map = {
            'load/index': 'load_index',
            'read_info/index': 'read_info',
            'pre_single_mode/index': 'pre_single_mode',
            'tool/start_session': 'start_session',
            'tool/pre_signup': 'pre_signup',
            'tool/signup': 'signup',
            'user/recovery_trainer_point': 'recovery_trainer_point',
            'single_mode_free/start': 'start_career',
            'single_mode_free/check_event': 'check_event',
            'single_mode_free/exec_command': 'exec_command',
            'single_mode_free/read_info': 'load_index',
            'single_mode_free/pre': 'pre_single_mode',
            'single_mode_free/race_continue': 'continue',
            'single_mode_free/continue': 'continue',
            'single_mode_free/gain_skills': 'gain_skills',
            'single_mode_free/multi_item_exchange': 'multi_item_exchange',
            'single_mode_free/multi_item_use': 'multi_item_use',
            'single_mode_free/minigame_end': 'minigame_end',
            'single_mode_free/race_end': 'race_end',
            'single_mode_free/race_entry': 'race_entry',
            'single_mode_free/change_running_style': 'change_running_style',
            'single_mode_free/reserve_race': 'reserve_race',
            'single_mode_free/race_out': 'race_out',
            'single_mode_free/race_start': 'race_start',
            'single_mode_free/load': 'load_career',
            'single_mode_free/finish': 'finish_career'
        }
        return path_map.get(ep, ep.split('/')[-1])

    def _paced_call(self, ep, *args, **kwargs):
        use_dna(self._dna)
        self._dna.simulate_delay(self._pacing_name(ep), self._client)
        return self._raw_call(ep, *args, **kwargs)

    def __getattr__(self, name):
        attr = getattr(self._client, name)
        return attr
