import time
import random
import struct
import cv2
import numpy as np
import threading
import subprocess
import shlex
from typing import Optional
from bot.conn.adb_client import AdbClient
from bot.conn.ctrl import AndroidController
from bot.base.point import ClickPoint, ClickPointType
from bot.recog.image_matcher import image_match
from config import CONFIG

class ADBTimeoutError(Exception):
    pass

class AdbController(AndroidController):
    def __init__(self, device_name: str):
        self.client = AdbClient(device_name)
        self.lock = threading.Lock()
        self.input_lock = threading.Lock()
        self.last_img = None
        self.last_ts = 0.0
        self.max_age = 0.120
        self.last_click = 0.0
        self.trigger_decision_reset = False
        
        self.recent_click_buckets = []
        self.fallback_block_until = 0.0
        self.repetitive_click_name = None
        self.repetitive_click_count = 0
        self.repetitive_other_clicks = 0
        self.last_click_time = 0.0
        self.last_recovery_time = 0
        self.recovery_grace_until = 0.0

    def init_env(self) -> None:
        for attempt in range(3):
            try:
                res = self.client.run_cmd(["shell", "echo", "ok"])
                if res.returncode != 0: raise Exception(f"ADB failed: {res.stderr}")
                return
            except Exception:
                if attempt < 2:
                    time.sleep(0.1)
                else:
                    raise

    def get_screen(self, to_gray=False, force=False):
        for attempt in range(3):
            img = None
            with self.lock:
                now = time.time()
                if not force and self.last_img is not None and (now - self.last_ts) < self.max_age:
                    img = self.last_img
                else:
                    img = self.capture()
                    if img is not None:
                        self.last_img = img
                        self.last_ts = time.time()
            if img is not None:
                return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if to_gray else img
            if attempt < 2:
                time.sleep(0.1)
        return None

    def capture(self) -> Optional[np.ndarray]:
        for _ in range(3):
            raw = self.client.capture_screen_raw()
            if not raw or len(raw) < 16:
                time.sleep(0.1)
                continue
            try:
                w, h, fmt = struct.unpack('<III', raw[:12])
                pixel_size = w * h * 4
                header_size = 16 if len(raw) >= 16 + pixel_size else 12
                if len(raw) < header_size + pixel_size:
                    time.sleep(0.1)
                    continue
                img = np.frombuffer(raw[header_size:header_size + pixel_size], dtype=np.uint8).reshape((h, w, 4))
                return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR if fmt == 5 else cv2.COLOR_RGBA2BGR)
            except Exception: time.sleep(0.1)
        return None

    def in_fallback_block(self, name):
        if isinstance(name, str) and name == "Default fallback click":
            if time.time() < self.fallback_block_until:
                return True
        return False

    def update_click_buckets(self, x, y):
        bucket = (int(x/25), int(y/25))
        if bucket not in self.recent_click_buckets:
            self.recent_click_buckets.append(bucket)
            if len(self.recent_click_buckets) > 2:
                self.recent_click_buckets.pop(0)
            self.fallback_block_until = time.time() + 2.0

    def build_click_key(self, x, y, name):
        if isinstance(name, str) and name.strip() != "":
            return name.strip()
        return f"{int(x/50)}:{int(y/50)}"

    def update_repetitive_click(self, click_key):
        try:
            from bot.base.runtime_state import update_repetitive, get_repetitive_threshold
            repetitive_threshold = int(get_repetitive_threshold())
        except Exception:
            repetitive_threshold = 11
            update_repetitive = None

        if isinstance(click_key, str):
            click_key = click_key.strip()

        if self.repetitive_click_name is None:
            self.repetitive_click_name = click_key
            self.repetitive_click_count = 1
            self.repetitive_other_clicks = 0
            if update_repetitive: update_repetitive(1, 0)
            return False

        current_name = self.repetitive_click_name.strip() if isinstance(self.repetitive_click_name, str) else self.repetitive_click_name
        is_same_key = (click_key == current_name) or (
            isinstance(click_key, str) and isinstance(current_name, str) and
            click_key.lower() == current_name.lower()
        )

        if is_same_key:
            self.repetitive_click_count += 1
        else:
            self.repetitive_other_clicks += 1
            if self.repetitive_other_clicks >= 2:
                self.repetitive_click_name = click_key
                self.repetitive_click_count = 1
                self.repetitive_other_clicks = 0
        
        if update_repetitive: update_repetitive(self.repetitive_click_count, self.repetitive_other_clicks)

        if time.time() < self.recovery_grace_until:
            self.repetitive_click_name = None
            self.repetitive_click_count = 0
            self.repetitive_other_clicks = 0
            return False

        if self.repetitive_click_name == click_key and self.repetitive_click_count >= repetitive_threshold:     
            try:
                self.recover_home_and_reopen()
            finally:
                self.repetitive_click_name = None
                self.repetitive_click_count = 0
                self.repetitive_other_clicks = 0
                if update_repetitive: update_repetitive(0, 0)
            return True
        return False

    def safety_dont_click(self, x, y):
        if 263 <= x <= 458 and 559 <= y <= 808:
            from module.umamusume.asset.template import REF_DONT_CLICK
            screen_gray = self.get_screen(to_gray=True, force=True)
            match = image_match(screen_gray, REF_DONT_CLICK)
            if getattr(match, "find_match", False):
                return True
        return False

    def wait_click_interval(self):
        elapsed = time.time() - self.last_click_time
        min_interval = random.uniform(0.06, 0.09)
        wait_needed = max(0.0, min_interval - elapsed)
        if wait_needed > 0: time.sleep(wait_needed)

    def recover_home_and_reopen(self):
        if time.time() - self.last_recovery_time < 10: return
        self.last_recovery_time = time.time()
        self.recovery_grace_until = time.time() + 60
        for _ in range(3):
            self.execute_adb_shell("input keyevent 4", True)
            time.sleep(0.4)
        self.execute_adb_shell("input keyevent 3", True)
        time.sleep(0.8)
        self.execute_adb_shell("monkey -p com.cygames.umamusume -c android.intent.category.LAUNCHER 1", True)
        time.sleep(1.2)
        self.trigger_decision_reset = True

    def back(self):
        with self.input_lock:
            self.execute_adb_shell("input keyevent 4", True)
            time.sleep(CONFIG.bot.auto.adb.delay)

    def click(self, x, y, name="", random_offset=True, hold_duration=0):
        with self.input_lock:
            from bot.base.runtime_state import get_state
            if get_state().get("input_blocked"): return
            
            if self.safety_dont_click(x, y): return
            
            if self.in_fallback_block(name): return
            self.update_click_buckets(x, y)
            
            click_key = self.build_click_key(x, y, name)
            if self.update_repetitive_click(click_key): return

            if random_offset:
                x += int(max(-8, min(8, random.gauss(0, 3))))
                y += int(max(-8, min(8, random.gauss(0, 3))))
            
            x, y = max(30, min(690, x)), max(66, min(1240, y))
            if hold_duration > 0 and y < 66: hold_duration = 0
            
            self.wait_click_interval()
            
            if hold_duration == 0:
                self.execute_adb_shell(f"input tap {x} {y}", True)
            else:
                duration = int(max(50, min(180, random.gauss(90, 30)))) + hold_duration
                dx, dy = x + random.randint(-3, 3), y + random.randint(-3, 3)
                if y < 120: dy = y
                self.execute_adb_shell(f"input swipe {x} {y} {dx} {dy} {duration}", True)
            
            self.last_click_time = time.time()
            time.sleep(CONFIG.bot.auto.adb.delay)

    def swipe(self, x1, y1, x2, y2, duration=0.2, name=""):
        with self.input_lock:
            from bot.base.runtime_state import get_state
            if get_state().get("input_blocked"): return
            
            x1 += int(max(-10, min(10, random.gauss(0, 4))))
            y1 += int(max(-10, min(10, random.gauss(0, 4))))
            x2 += int(max(-10, min(10, random.gauss(0, 4))))
            y2 += int(max(-10, min(10, random.gauss(0, 4))))
            
            if y1 < 120:
                self.click(x1, y1, name=name, random_offset=False, hold_duration=0)
                return

            x1, y1 = max(30, min(690, x1)), max(66, min(1240, y1))
            x2, y2 = max(30, min(690, x2)), max(66, min(1240, y2))
            
            d = int(duration * 1000 * random.uniform(0.94, 1.06))
            self.execute_adb_shell(f"input swipe {x1} {y1} {x2} {y2} {d}", True)
            time.sleep(CONFIG.bot.auto.adb.delay)

    def start_app(self, package, activity=None):
        cmd = f"am start -n {package}/{activity}" if activity else f"monkey -p {package} -c android.intent.category.LAUNCHER 1"
        self.execute_adb_shell(cmd, True)

    def destroy(self):
        self.last_img = None

    def click_by_point(self, point: ClickPoint, random_offset=True, hold_duration=0):
        if point.target_type == ClickPointType.CLICK_POINT_TYPE_COORDINATE:
            self.click(point.coordinate.x, point.coordinate.y, name=point.desc, random_offset=random_offset, hold_duration=hold_duration)
        elif point.target_type == ClickPointType.CLICK_POINT_TYPE_TEMPLATE:
            gray = self.get_screen(to_gray=True)
            res = image_match(gray, point.template)
            if res.find_match:
                self.click(res.center_point[0], res.center_point[1], name=point.desc, random_offset=random_offset, hold_duration=hold_duration)

    def execute_adb_shell(self, cmd: str, sync: bool = True):
        if cmd.startswith("shell "): cmd = cmd[6:]
        if sync:
            return self.client.shell(cmd, sync=True)
        else:
            adb_cmd = [self.client.adb_path, "-s", self.client.device_name, "shell"] + shlex.split(cmd)
            return subprocess.Popen(adb_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def reinit_connection(self):
        with self.client.plock:
            if self.client.psock:
                try: self.client.psock.close()
                except: pass
                self.client.psock = None
        try:
            self.client.kill_server()
            time.sleep(1)
            self.client.start_server()
            time.sleep(2)
            self.client.connect()
            self.init_env()
        except Exception: pass
        self.last_img = None
        self.client.prefill_pool()

    def swipe_and_hold(self, x1, y1, x2, y2, swipe_duration, hold_duration, name=""):
        with self.input_lock:
            from bot.base.runtime_state import get_state
            if get_state().get("input_blocked"): return
            
            x1 += int(max(-10, min(10, random.gauss(0, 4))))
            y1 += int(max(-10, min(10, random.gauss(0, 4))))
            x2 += int(max(-10, min(10, random.gauss(0, 4))))
            y2 += int(max(-10, min(10, random.gauss(0, 4))))
            
            if y1 < 120:
                self.click(x1, y1, name=name, random_offset=False, hold_duration=0)
                return
                
            x1, y1 = max(30, min(690, x1)), max(66, min(1240, y1))
            x2, y2 = max(30, min(690, x2)), max(66, min(1240, y2))
            
            sw_d = int(swipe_duration * random.uniform(0.94, 1.06))
            ho_d = int(hold_duration * random.uniform(0.94, 1.06))
            rev_y = y2 - 28 if y2 > y1 else y2 + 28
            rev_y = max(66, min(1240, rev_y))
            
            self.execute_adb_shell(f"input swipe {x1} {y1} {x2} {y2} {sw_d}", True)
            time.sleep(0.05)
            self.execute_adb_shell(f"input swipe {x2} {y2} {x2} {rev_y} {ho_d}", True)
            time.sleep(CONFIG.bot.auto.adb.delay)

    def swipe_async(self, x1, y1, x2, y2, duration_ms, name=""):
        x1, y1 = max(30, min(690, x1)), max(66, min(1240, y1))
        x2, y2 = max(30, min(690, x2)), max(66, min(1240, y2))
        def _run():
            with self.input_lock:
                self.execute_adb_shell(f"input swipe {x1} {y1} {x2} {y2} {duration_ms}", True)
        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return t
