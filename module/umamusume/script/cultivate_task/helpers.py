import cv2
import time
import os

import bot.base.log as logger
from bot.recog.image_matcher import image_match
from module.umamusume.context import UmamusumeContext
from module.umamusume.constants.game_constants import is_summer_camp_period

log = logger.get_logger(__name__)

TRAINING_REPLACEMENT_DATES_ORDER = (7, 5, 1, 4, 3)
TRAINING_REPLACEMENT_DATES = set(TRAINING_REPLACEMENT_DATES_ORDER)
REST_REPLACEMENT_DATES = {2, 6, 7}
RECREATION_REPLACEMENT_DATES = {3}

ts_cancel_tpl = None

def get_ts_cancel_template():
    global ts_cancel_tpl
    if ts_cancel_tpl is None:
        base = os.path.dirname(__file__)
        for _ in range(4):
            base = os.path.dirname(base)
        path = os.path.join(base, "resource", "umamusume", "ui", "cancel.png")
        ts_cancel_tpl = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    return ts_cancel_tpl

TS_CLICK = (331, 427)
TS_RECREATION_CANCEL = (314, 901, 405, 931)
TS_MENU_CANCEL = (291, 1154, 418, 1204)
TS_DATE_X = 604
TS_DATE_Y = [149, 298, 443, 592, 731, 876, 1015]
TS_DATE_CLICK_Y = [180, 330, 475, 625, 765, 910, 1050]
TS_DATE_CLICK_X = 400

def ts_match_cancel(screen, x1, y1, x2, y2):
    tpl = get_ts_cancel_template()
    if tpl is None:
        return False
    roi = screen[y1:y2, x1:x2]
    if roi.size == 0 or roi.shape[0] < tpl.shape[0] or roi.shape[1] < tpl.shape[1]:
        return False
    roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    res = cv2.matchTemplate(roi_gray, tpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(res)
    return max_val >= 0.8

def ts_wait_cancel(ctx, x1, y1, x2, y2, timeout=1.6, interval=0.17):
    start = time.time()
    while time.time() - start < timeout:
        screen = ctx.ctrl.get_screen()
        if screen is not None and ts_match_cancel(screen, x1, y1, x2, y2):
            return True
        time.sleep(interval)
    return False

def ts_wait_cancel_gone(ctx, x1, y1, x2, y2, timeout=1.6, interval=0.17):
    start = time.time()
    while time.time() - start < timeout:
        screen = ctx.ctrl.get_screen()
        if screen is None or not ts_match_cancel(screen, x1, y1, x2, y2):
            return True
        time.sleep(interval)
    return False

def is_menu(ctx: UmamusumeContext):
    from module.umamusume.asset.template import UI_HOME_HINT
    img = ctx.ctrl.get_screen()
    if img is None:
        return False
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    result = image_match(img_gray, UI_HOME_HINT)
    return result.find_match


def should_use_pal_outing_simple(ctx: UmamusumeContext):
    if not getattr(ctx.cultivate_detail, 'prioritize_recreation', False):
        return False
    if ctx.cultivate_detail.pal_event_stage <= 0:
        return False

    ti = ctx.cultivate_detail.turn_info
    if ti is None:
        return False
    cached = getattr(ti, 'pal_outing_cached', None)
    cached_date = getattr(ti, 'pal_outing_cached_date', -1)
    if cached is not None and cached_date == ti.date:
        return cached

    img = ctx.current_screen
    if img is None:
        return False

    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    from module.umamusume.asset.template import UI_RECREATION_FRIEND_NOTIFICATION
    result = image_match(img_gray, UI_RECREATION_FRIEND_NOTIFICATION)
    if not result.find_match:
        ti.pal_outing_cached = False
        ti.pal_outing_cached_date = ti.date
        return False

    pal_thresholds = ctx.cultivate_detail.pal_thresholds
    if not pal_thresholds:
        ti.pal_outing_cached = False
        ti.pal_outing_cached_date = ti.date
        return False

    stage = ctx.cultivate_detail.pal_event_stage
    if stage > len(pal_thresholds):
        ti.pal_outing_cached = False
        ti.pal_outing_cached_date = ti.date
        return False

    thresholds = pal_thresholds[stage - 1]
    mood_threshold = thresholds[0]
    energy_threshold = thresholds[1]
    score_threshold = thresholds[2] if len(thresholds) > 2 else 0

    from bot.conn.fetch import fetch_state
    state = fetch_state(img)
    current_energy = state.get("energy", 0)
    current_mood_raw = state.get("mood")
    current_mood = current_mood_raw if current_mood_raw is not None else 4

    mood_below = current_mood <= mood_threshold
    energy_below = current_energy <= energy_threshold

    log.info(f"PAL outing check - Stage {stage}:")
    log.info(f"Mood: {current_mood} vs {mood_threshold} - {'<=' if mood_below else '>'}")
    log.info(f"Energy: {current_energy} vs {energy_threshold} - {'<=' if energy_below else '>'}")

    should_outing = mood_below and energy_below
    if should_outing:
        log.info("Both conditions met - using pal outing instead of rest")
    else:
        log.info("Conditions not met - using rest")

    ti.pal_outing_cached = should_outing
    ti.pal_outing_cached_date = ti.date
    return should_outing


def should_use_pal_outing(ctx: UmamusumeContext, score_below: bool = False):
    prioritize = getattr(ctx.cultivate_detail, 'prioritize_recreation', False)
    stage = ctx.cultivate_detail.pal_event_stage
    if not prioritize:
        return False
    if stage <= 0:
        return False

    ti = ctx.cultivate_detail.turn_info
    if ti is None:
        return False
    cached = getattr(ti, 'pal_outing_cached', None)
    cached_date = getattr(ti, 'pal_outing_cached_date', -1)
    if cached is not None and cached_date == ti.date:
        return cached

    img = ctx.current_screen
    if img is None:
        return False

    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    from module.umamusume.asset.template import UI_RECREATION_FRIEND_NOTIFICATION
    result = image_match(img_gray, UI_RECREATION_FRIEND_NOTIFICATION)
    if not result.find_match:
        ti.pal_outing_cached = False
        ti.pal_outing_cached_date = ti.date
        return False

    pal_thresholds = ctx.cultivate_detail.pal_thresholds
    if not pal_thresholds:
        ti.pal_outing_cached = False
        ti.pal_outing_cached_date = ti.date
        return False

    stage = ctx.cultivate_detail.pal_event_stage
    if stage > len(pal_thresholds):
        ti.pal_outing_cached = False
        ti.pal_outing_cached_date = ti.date
        return False

    thresholds = pal_thresholds[stage - 1]
    mood_threshold = thresholds[0]
    energy_threshold = thresholds[1]
    score_threshold = thresholds[2] if len(thresholds) > 2 else 0

    from bot.conn.fetch import fetch_state
    state = fetch_state(img)
    current_energy = state.get("energy", 0)
    current_mood_raw = state.get("mood")
    current_mood = current_mood_raw if current_mood_raw is not None else 4

    mood_below = current_mood <= mood_threshold
    energy_below = current_energy <= energy_threshold
    score_below_val = score_threshold > 0 and score_below

    conditions_met = sum([mood_below, energy_below, score_below_val])
    should_outing = conditions_met >= 2

    ti.pal_outing_cached = should_outing
    ti.pal_outing_cached_date = ti.date
    return should_outing


def detect_pal_stage(ctx: UmamusumeContext, img):
    pal_name = ctx.cultivate_detail.pal_name
    pal_thresholds = ctx.cultivate_detail.pal_thresholds

    if not pal_name or not pal_thresholds:
        return 0

    pal_data = pal_thresholds
    num_stages = len(pal_data)

    coords_to_check = []
    if num_stages == 3:
        coords_to_check = [(554, 474), (605, 474)]
    elif num_stages == 4:
        coords_to_check = [(503, 474), (554, 474), (605, 474)]
    elif num_stages == 5:
        coords_to_check = [(452, 474), (503, 474), (554, 474), (605, 474)]

    matching_pixels = 0
    for x, y in coords_to_check:
        pixel_color = img[y, x]
        b, g, r = pixel_color[0], pixel_color[1], pixel_color[2]
        is_match = abs(b - 223) <= 5 and abs(g - 227) <= 5 and abs(r - 231) <= 5
        if is_match:
            matching_pixels += 1

    calculated_stage = len(coords_to_check) - matching_pixels + 1
    return calculated_stage


def detect_group_card_dates(ctx: UmamusumeContext):
    from module.umamusume.asset.point import CULTIVATE_TRIP_MANT, ESCAPE
    ctx.ctrl.click_by_point(CULTIVATE_TRIP_MANT)
    if not ts_wait_cancel(ctx, *TS_RECREATION_CANCEL, timeout=3.2):
        ctx.ctrl.click_by_point(ESCAPE)
        if not ts_wait_cancel(ctx, *TS_RECREATION_CANCEL, timeout=2.0):
            ctx.cultivate_detail.group_card_available_dates = []
            return []
    ctx.ctrl.click(*TS_CLICK)
    if not ts_wait_cancel(ctx, *TS_MENU_CANCEL, timeout=3.2):
        ctx.ctrl.click_by_point(ESCAPE)
        ts_wait_cancel(ctx, *TS_RECREATION_CANCEL, timeout=2.0)
        ctx.ctrl.click_by_point(ESCAPE)
        ts_wait_cancel_gone(ctx, *TS_RECREATION_CANCEL, timeout=2.0)
        ctx.cultivate_detail.group_card_available_dates = []
        return []
    screen = ctx.ctrl.get_screen()
    available = []
    if screen is not None:
        h, w, _ = screen.shape
        for i, y in enumerate(TS_DATE_Y):
            if y < h and TS_DATE_X < w:
                r, g, b = screen[y, TS_DATE_X][:3]
                is_white = abs(int(r) - 255) <= 5 and abs(int(g) - 255) <= 5 and abs(int(b) - 255) <= 5
                if is_white:
                    available.append(i + 1)
    ctx.cultivate_detail.group_card_available_dates = available
    import random
    for attempt in range(10):
        if is_menu(ctx):
            break
        x = random.randint(500, 600)
        y = random.randint(15, 22)
        ctx.ctrl.click(x, y)
        time.sleep(0.3)
    return available


def should_use_group_card_recreation(ctx: UmamusumeContext) -> bool:
    enabled = getattr(ctx.cultivate_detail, 'group_card_enabled', False)
    available = getattr(ctx.cultivate_detail, 'group_card_available_dates', [])
    last_used = getattr(ctx.cultivate_detail, 'group_card_last_date', -1)
    current_date = ctx.cultivate_detail.turn_info.date
    if not enabled:
        return False
    if not available:
        return False
    if current_date - last_used <= 1:
        return False
    all_dates = REST_REPLACEMENT_DATES | TRAINING_REPLACEMENT_DATES | RECREATION_REPLACEMENT_DATES
    return any(d in all_dates for d in available)


def get_group_card_recreation_date(ctx: UmamusumeContext) -> int:
    """Return the best date slot to use for group card recreation.
    Priority: training replacement > rest replacement > recreation replacement."""
    available = getattr(ctx.cultivate_detail, 'group_card_available_dates', [])
    if not available:
        return 0
    all_priority = list(TRAINING_REPLACEMENT_DATES_ORDER) + \
                  [d for d in REST_REPLACEMENT_DATES if d not in TRAINING_REPLACEMENT_DATES_ORDER] + \
                  [d for d in RECREATION_REPLACEMENT_DATES if d not in TRAINING_REPLACEMENT_DATES_ORDER]
    for date in all_priority:
        if date in available:
            return date
    return 0


def execute_group_card_recreation(ctx: UmamusumeContext, trip_click_point=None) -> bool:
    """Execute a group card recreation action.
    This navigates the team recreation UI, which is DIFFERENT from friend outing UI."""
    date_slot = get_group_card_recreation_date(ctx)
    if date_slot == 0:
        return False

    from module.umamusume.asset.point import CULTIVATE_OPERATION_COMMON_CONFIRM, ESCAPE

    if trip_click_point:
        ctx.ctrl.click_by_point(trip_click_point)
    else:
        from module.umamusume.asset.point import CULTIVATE_TRIP_MANT
        ctx.ctrl.click_by_point(CULTIVATE_TRIP_MANT)
    time.sleep(0.3)

    if not ts_wait_cancel(ctx, *TS_RECREATION_CANCEL, timeout=2.0):
        ctx.ctrl.click_by_point(ESCAPE)
        if not ts_wait_cancel(ctx, *TS_RECREATION_CANCEL, timeout=1.5):
            return False

    ctx.ctrl.click_by_point(CULTIVATE_OPERATION_COMMON_CONFIRM)
    time.sleep(0.3)

    ctx.ctrl.click(*TS_CLICK)
    time.sleep(0.3)

    if not ts_wait_cancel(ctx, *TS_MENU_CANCEL, timeout=2.0):
        ctx.ctrl.click_by_point(ESCAPE)
        ts_wait_cancel(ctx, *TS_RECREATION_CANCEL, timeout=1.5)
        ctx.ctrl.click_by_point(ESCAPE)
        ts_wait_cancel_gone(ctx, *TS_RECREATION_CANCEL, timeout=1.5)
        return False

    click_y = TS_DATE_CLICK_Y[date_slot - 1]
    ctx.ctrl.click(TS_DATE_CLICK_X, click_y)
    time.sleep(0.3)

    import random
    for _ in range(10):
        if is_menu(ctx):
            break
        x = random.randint(500, 600)
        y = random.randint(15, 22)
        ctx.ctrl.click(x, y)
        time.sleep(0.2)

    ctx.cultivate_detail.group_card_last_date = ctx.cultivate_detail.turn_info.date
    ctx.cultivate_detail.group_card_available_dates = []
    return True
