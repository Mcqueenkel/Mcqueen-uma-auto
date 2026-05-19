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

_dna_path = os.path.join(os.path.dirname(__file__), '.timing_dna')
if not os.path.exists(_dna_path):
    with open(_dna_path, 'w') as f:
        f.write(str(random.randint(1000000, 9999999)))

with open(_dna_path, 'r') as f:
    _dna_seed = int(f.read().strip())

_dna_rng = random.Random(_dna_seed)
_USER_SIGMA = _dna_rng.uniform(0.45, 0.75)
_USER_SPEED_SHIFT = _dna_rng.uniform(0.92, 1.08)

_USER_DISTRACTION_CHANCE = _dna_rng.uniform(0.015, 0.065)
_USER_DISTRACTION_MIN = _dna_rng.uniform(1.5, 3.5)
_USER_DISTRACTION_MAX = _dna_rng.uniform(7.0, 14.0)

TURN_DELAY_MIN = 2.5
TURN_DELAY_MAX = 5.0
TURN_DELAY_RESTORE_MIN = 2.5
TURN_DELAY_RESTORE_MAX = 5.0
GLOBAL_DELAYS_DISABLED = False

_ENDPOINT_SHIFTS = {}
for ep in _BASE_DELAYS:
    _ENDPOINT_SHIFTS[ep] = _dna_rng.uniform(0.85, 1.15)


def simulate_delay(endpoint, client=None):
    if GLOBAL_DELAYS_DISABLED:
        print(f"Endpoint: {endpoint} | Delay: 0.000s", flush=True)
        return 0.0

    if endpoint not in _BASE_DELAYS:
        target_delay = 0.3 * _USER_SPEED_SHIFT
        mu = math.log(target_delay) - (_USER_SIGMA**2) / 2.0
        dt = _dna_rng.lognormvariate(mu, _USER_SIGMA)
        dt = max(0.08, min(1.2, dt))
    else:
        real_min, real_max, real_avg = _BASE_DELAYS[endpoint]
        ep_shift = _ENDPOINT_SHIFTS[endpoint]
        target_delay = real_avg * _USER_SPEED_SHIFT * ep_shift
        shifted_min = real_min * _USER_SPEED_SHIFT * ep_shift
        shifted_max = real_max * _USER_SPEED_SHIFT * ep_shift
        mu = math.log(target_delay) - (_USER_SIGMA**2) / 2.0
        dt = _dna_rng.lognormvariate(mu, _USER_SIGMA)
        dt = max(shifted_min, min(shifted_max, dt))

    if _dna_rng.random() < _USER_DISTRACTION_CHANCE:
        dt += _dna_rng.uniform(_USER_DISTRACTION_MIN, _USER_DISTRACTION_MAX)

    print(f"Endpoint: {endpoint} | Delay: {dt:.3f}s", flush=True)

    if client and hasattr(client, '_last_raw_call_ts'):
        elapsed = time.time() - client._last_raw_call_ts
        actual_sleep = dt - elapsed
        if actual_sleep > 0:
            time.sleep(actual_sleep)
    else:
        time.sleep(dt)
    return dt


def simulate_turn_delay():
    if GLOBAL_DELAYS_DISABLED:
        print(f"Endpoint: turn_delay | Delay: 0.000s", flush=True)
        return 0.0
    range_span = TURN_DELAY_MAX - TURN_DELAY_MIN
    target_mean = (((TURN_DELAY_MIN + TURN_DELAY_MAX) / 2.0) + (_dna_rng.uniform(-0.08, 0.08) * range_span)) * _USER_SPEED_SHIFT
    sigma = 0.75 * _USER_SIGMA
    mu = math.log(max(0.1, target_mean)) - (sigma**2) / 2.0
    dt = _dna_rng.lognormvariate(mu, sigma)
    dt = min(TURN_DELAY_MAX * 5.0, max(TURN_DELAY_MIN * 0.5, dt))
    
    print(f"Endpoint: turn_delay | Delay: {dt:.3f}s", flush=True)
    time.sleep(dt)

def dna_randint(min_val, max_val):
    return _dna_rng.randint(min_val, max_val)

def dna_sleep(min_val, max_val, mean=None, stddev=None):
    if GLOBAL_DELAYS_DISABLED:
        return 0.0
    if mean is not None and stddev is not None:
        dt = max(min_val, min(max_val, _dna_rng.gauss(mean, stddev)))
    else:
        dt = _dna_rng.uniform(min_val, max_val)
    time.sleep(dt)
    return dt

def dna_uniform(min_val, max_val):
    return _dna_rng.uniform(min_val, max_val)

def dna_gauss(mean, stddev):
    return _dna_rng.gauss(mean, stddev)


class GateKeeper:
    def __init__(self, client):
        super().__setattr__('_client', client)
        raw_call = getattr(client, '_gatekeeper_raw_call', None)
        if raw_call is None:
            raw_call = client.call
            setattr(client, '_gatekeeper_raw_call', raw_call)
        super().__setattr__('_raw_call', raw_call)
        client.call = self._paced_call

    def wait_turn_delay(self):
        simulate_turn_delay()

    def wait_complex_delay(self):
        pass

    def __setattr__(self, name, value):
        if name in ('_client', '_raw_call'):
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
        simulate_delay(self._pacing_name(ep), self._client)
        return self._raw_call(ep, *args, **kwargs)

    def __getattr__(self, name):
        attr = getattr(self._client, name)
        return attr
