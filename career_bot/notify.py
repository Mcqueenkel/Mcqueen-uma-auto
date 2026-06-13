"""Discord webhook notifications for finished careers.

The webhook URL is stored in uma_runtime/discord.json (gitignored) so it never
reaches the repo. Sending uses only the standard library (urllib), so no extra
dependency is needed.
"""

import hashlib
import json
import os
import re
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Daily fan tracking rolls over with the GAME's daily reset, not a local timezone. That reset
# is a fixed instant -- 15:00 UTC (= midnight in the game's JST server day) -- so the fan-day is
# derived from the game's server clock (or UTC) shifted by this hour. No locale assumptions.
GAME_DAY_RESET_UTC_HOUR = 15


def _discord_path(base_dir):
    return Path(base_dir) / "uma_runtime" / "discord.json"


def _read_config(base_dir):
    path = _discord_path(base_dir)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _write_config(base_dir, cfg):
    path = _discord_path(base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def get_webhook_url(base_dir):
    return str(_read_config(base_dir).get("webhook_url") or "").strip()


def set_webhook_url(base_dir, url):
    cfg = _read_config(base_dir)
    cfg["webhook_url"] = str(url or "").strip()
    _write_config(base_dir, cfg)
    return True


def get_account_name(base_dir):
    return str(_read_config(base_dir).get("account_name") or "").strip()


def set_account_name(base_dir, name):
    cfg = _read_config(base_dir)
    cfg["account_name"] = str(name or "").strip()
    _write_config(base_dir, cfg)
    return True


def uma_name(base_dir, card_id):
    if not card_id:
        return None
    try:
        path = Path(base_dir) / "data" / "chara_list.json"
        names = json.loads(path.read_text(encoding="utf-8"))
        return names.get(str(card_id))
    except Exception:
        return None


_SPARK_CAT_ORDER = ["stat", "aptitude", "unique", "skill", "race", "scenario", "other"]
_SPARK_CAT_LABEL = {
    "stat": "Stat", "aptitude": "Aptitude", "unique": "Unique",
    "skill": "Skill", "race": "Race", "scenario": "Scenario", "other": "Other",
}


def resolve_sparks(base_dir, factor_ids):
    """Turn factor ids (inheritance sparks) into {name, stars, category} via
    data/factor_map.json. Unknown ids are skipped."""
    if not factor_ids:
        return []
    try:
        fm = json.loads((Path(base_dir) / "data" / "factor_map.json").read_text(encoding="utf-8"))
    except Exception:
        return []
    out = []
    for fid in factor_ids:
        e = fm.get(str(fid))
        if e and e.get("name"):
            out.append({
                "name": e["name"],
                "stars": int(e.get("stars") or 0),
                "category": e.get("category") or "other",
            })
    return out


def _format_sparks(sparks):
    by_cat = {}
    for s in sparks:
        stars = max(1, min(3, int(s.get("stars") or 1)))
        by_cat.setdefault(s.get("category") or "other", []).append(f"{s['name']} {'★' * stars}")
    lines = []
    for cat in _SPARK_CAT_ORDER:
        if by_cat.get(cat):
            lines.append(f"**{_SPARK_CAT_LABEL.get(cat, cat)}:** " + " · ".join(by_cat[cat]))
    return "\n".join(lines)


# Aptitude grade (1..8) -> letter, used by the forecast panel's aptitude line.
_GRADE_LETTERS = {8: "S", 7: "A", 6: "B", 5: "C", 4: "D", 3: "E", 2: "F", 1: "G"}

# Final career evaluation rank -> letter (the game's trained-chara rank scale,
# same mapping the dashboard's parents grid uses).
_RANK_LETTERS = {
    1: "G", 2: "G+", 3: "F", 4: "F+", 5: "E", 6: "E+", 7: "D", 8: "D+",
    9: "C", 10: "C+", 11: "B", 12: "B+", 13: "A", 14: "A+", 15: "S", 16: "S+",
    17: "SS", 18: "SS+", 19: "UG", 20: "UF", 21: "UE", 22: "UD",
}


def rank_letter(rank):
    try:
        return _RANK_LETTERS.get(int(rank), "")
    except (TypeError, ValueError):
        return ""


def fan_day_key(server_ts=None):
    """The 'game-day' a moment belongs to = the DATE of the most recent in-game daily reset
    (15:00 UTC). Prefer the GAME's server time (Unix UTC) so the tally rolls over exactly with
    the game's new day regardless of the machine clock; fall back to UTC now. Shifting back the
    reset hour folds the day so reset-time today .. reset-time tomorrow share one key. Auto-reset
    is then just 'the stored key no longer matches the current one' -- no timer needed."""
    if server_ts:
        try:
            t = datetime.fromtimestamp(int(server_ts), tz=timezone.utc)
        except (TypeError, ValueError, OSError, OverflowError):
            t = datetime.now(timezone.utc)
    else:
        t = datetime.now(timezone.utc)
    return (t - timedelta(hours=GAME_DAY_RESET_UTC_HOUR)).date().isoformat()


def _fan_dir(base_dir):
    return Path(base_dir) / "uma_runtime" / "fan_totals"


def _account_slug(account):
    # Hash-suffixed so DISTINCT account names never collide into one file -- in-game names are
    # often non-ASCII (Japanese), which would otherwise all sanitize to the same slug and merge
    # two accounts' fan totals. The display label comes from the stored `account` field, not this.
    raw = str(account or "").strip()
    if not raw:
        return "default"
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", raw).strip("_") or "acct"
    return f"{safe}-{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:8]}"


def _read_account_fans(path, day):
    """Read one account's daily fan file, returning 0 when its fan-day has rolled over."""
    try:
        d = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        d = {}
    if not isinstance(d, dict) or d.get("day") != day:
        return 0
    try:
        return int(d.get("fans") or 0)
    except (TypeError, ValueError):
        return 0


def record_account_fans(base_dir, account, fans, server_ts=None):
    """Add a finished career's fans to this account's running daily total (auto-resets on the
    game's daily reset, using server_ts when given). Per-account file so parallel account-
    instances never clobber each other. Returns the cross-account daily summary for the webhook."""
    fans = max(0, int(fans or 0))
    day = fan_day_key(server_ts)
    slug = _account_slug(account)
    path = _fan_dir(base_dir) / f"{slug}.json"
    try:
        total = _read_account_fans(path, day) + fans
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(f".json.{os.getpid()}.tmp")
        tmp.write_text(json.dumps({"day": day, "fans": total,
                                   "account": str(account or "").strip(),
                                   "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")},
                                  ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, path)
    except Exception as exc:
        print(f"record_account_fans failed: {exc}", flush=True)
    return daily_fan_summary(base_dir, server_ts)


def daily_fan_summary(base_dir, server_ts=None):
    """Current daily fan totals across all accounts (game-day reset applied on read using
    server_ts when given). Returns {day, accounts: [{account, fans}], total}."""
    day = fan_day_key(server_ts)
    accounts = []
    fan_dir = _fan_dir(base_dir)
    try:
        files = sorted(fan_dir.glob("*.json")) if fan_dir.exists() else []
    except Exception:
        files = []
    for path in files:
        if path.name.endswith(".tmp") or ".json." in path.name:
            continue
        fans = _read_account_fans(path, day)
        if fans <= 0:
            continue
        label = path.stem
        try:
            stored = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(stored, dict) and stored.get("account"):
                label = stored["account"]
        except Exception:
            pass
        accounts.append({"account": label, "fans": fans})
    accounts.sort(key=lambda a: a["fans"], reverse=True)
    return {"day": day, "accounts": accounts, "total": sum(a["fans"] for a in accounts)}


def _history_path(base_dir):
    return Path(base_dir) / "uma_runtime" / "career_history.json"


def record_career_history(base_dir, summary):
    """Append a finished career to the all-time history and return its TOTAL RANKING:
    {place, total, top: [{uma_name, rank, rank_score, when, current}]}.

    Only careers that produced a final evaluation (rank_score > 0, i.e. actually
    finished) are ranked; stopped/errored runs are not recorded. The history lives in
    uma_runtime/ (gitignored) and works with or without a webhook configured."""
    summary = dict(summary or {})
    score = int(summary.get("rank_score") or 0)
    if str(summary.get("status")) != "finished" or score <= 0:
        return None
    path = _history_path(base_dir)
    history = []
    if path.exists():
        try:
            history = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(history, list):
                raise ValueError("history is not a list")
        except Exception as exc:
            # Never silently wipe the all-time record: preserve the unreadable file
            # and start a fresh history beside it.
            history = []
            try:
                import os
                corrupt = path.with_name(f"career_history.corrupt-{time.strftime('%Y%m%d_%H%M%S')}.json")
                os.replace(path, corrupt)
                print(f"career history unreadable ({exc}); preserved as {corrupt.name}", flush=True)
            except Exception:
                pass
    entry = {
        "when": time.strftime("%Y-%m-%d %H:%M"),
        "uma_name": summary.get("uma_name") or uma_name(base_dir, summary.get("card_id")) or "Unknown",
        "card_id": str(summary.get("card_id") or ""),
        "rank": int(summary.get("rank") or 0),
        "rank_score": score,
        "fans": int(summary.get("fans") or 0),
        "preset": summary.get("preset") or "",
        "account": summary.get("account") or "",
    }
    history.append(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    import os
    # pid-suffixed tmp so two bot instances sharing uma_runtime can't collide mid-write.
    tmp = path.with_suffix(f".json.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(history, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)

    ranked = sorted(history, key=lambda e: int(e.get("rank_score") or 0), reverse=True)
    # Standard competition ranking: a tie with the all-time best is shared #1.
    place = 1 + sum(1 for e in history if int(e.get("rank_score") or 0) > score)
    top = []
    for i, e in enumerate(ranked[:5]):
        top.append({
            "pos": i + 1,
            "uma_name": e.get("uma_name") or "Unknown",
            "rank": int(e.get("rank") or 0),
            "rank_score": int(e.get("rank_score") or 0),
            "when": e.get("when") or "",
            "current": e is entry,
        })
    return {"place": place, "total": len(ranked), "top": top}
_FORECAST_STATS = [("Speed", "speed"), ("Stamina", "stamina"), ("Power", "power"),
                   ("Guts", "guts"), ("Wit", "wit")]


def _apt_str(forecast):
    """C+ apt distances as 'long A, middle B' (anything below C is dropped)."""
    out = []
    for entry in forecast.get("apt_distances") or []:
        try:
            cat, grade = entry[0], int(entry[1])
        except Exception:
            continue
        if grade >= 5:
            out.append(f"{cat} {_GRADE_LETTERS.get(grade, '?')}")
    return ", ".join(out)


def _targets_str(forecast):
    t = forecast.get("stat_targets")
    if not isinstance(t, dict):
        t = {}
    return " · ".join(f"{name[:3].upper()} {int(t.get(name, 0) or 0)}" for name, _ in _FORECAST_STATS)


def _build_embed(summary):
    status = str(summary.get("status") or "?")
    color = {"finished": 0x2ECC71, "stopped": 0xF1C40F, "error": 0xE74C3C}.get(status, 0x95A5A6)
    title = {
        "finished": "🏁 Career Finished",
        "stopped": "⏹️ Career Stopped",
        "error": "⚠️ Career Error",
    }.get(status, "Career")
    stats = summary.get("stats") or {}
    fans = int(summary.get("fans") or stats.get("fans") or 0)

    description = ""
    if summary.get("account"):
        description += f"👤 Account **{summary['account']}** · "
    description += f"**{summary.get('uma_name') or 'Unknown'}**"
    if summary.get("preset"):
        description += f" · `{summary['preset']}`"
    loop_target = int(summary.get("loop_target") or 0)
    if loop_target != 1:
        description += f" · 🔁 Run {int(summary.get('loop_index') or 1)}/{'∞' if loop_target == 0 else loop_target}"

    fields = [
        {"name": "Status", "value": status, "inline": True},
        {"name": "Turn", "value": str(summary.get("final_turn") or 0), "inline": True},
        {"name": "Duration", "value": str(summary.get("duration") or "?"), "inline": True},
    ]
    # Final evaluation grade (from the finish response's trained-chara entry).
    letter = rank_letter(summary.get("rank"))
    score = int(summary.get("rank_score") or 0)
    if letter or score:
        fields.append({"name": "Grade",
                       "value": f"**{letter or '?'}** ({score:,} pts)" if score else f"**{letter}**",
                       "inline": True})
    fields += [
        {"name": "Total Fans", "value": f"{fans:,}", "inline": True},
        {"name": "Skill Point", "value": str(stats.get("skill_point", 0)), "inline": True},
        {"name": "Skills bought", "value": str(summary.get("skills_bought", 0)), "inline": True},
        {
            "name": "Stat",
            "value": "SPD {} · STA {} · PWR {} · GUT {} · WIT {}".format(
                stats.get("speed", 0), stats.get("stamina", 0), stats.get("power", 0),
                stats.get("guts", 0), stats.get("wit", 0),
            ),
            "inline": False,
        },
        {"name": "Race", "value": str(summary.get("races", 0)), "inline": True},
    ]
    forecast = summary.get("forecast")
    if forecast and forecast.get("active"):
        # How the final build matched what the bot predicted this career should aim for.
        targets = forecast.get("stat_targets") or {}
        parts = []
        for name, key in _FORECAST_STATS:
            ach = int(stats.get(key, 0))
            tgt = int(targets.get(name, 0))
            mark = " ✓" if tgt and ach >= tgt * 0.95 else ""
            parts.append(f"{name[:3].upper()} {ach}/{tgt}{mark}")
        apt = _apt_str(forecast)
        head = f"**{forecast.get('archetype') or '?'}**" + (f" (apt: {apt})" if apt else "")
        fields.append({"name": "🔮 Predicted Direction (achieved / target)",
                       "value": (head + "\n" + " · ".join(parts))[:1024], "inline": False})

    ranking = summary.get("ranking")
    if ranking and ranking.get("top"):
        # All-time standing across every finished career (uma_runtime/career_history.json).
        lines = []
        for e in ranking["top"]:
            mark = " **← this run**" if e.get("current") else ""
            letter_e = rank_letter(e.get("rank"))
            lines.append(f"{e.get('pos')}. {e.get('uma_name')} — {letter_e or '?'} ({int(e.get('rank_score') or 0):,}){mark}")
        head = f"**#{ranking.get('place')} of {ranking.get('total')}** all-time"
        fields.append({"name": "🏆 Total Ranking",
                       "value": (head + "\n" + "\n".join(lines))[:1024], "inline": False})

    fan_summary = summary.get("fan_summary")
    if fan_summary and fan_summary.get("accounts"):
        # Fans earned per account this game-day; resets with the in-game daily reset.
        lines = [f"**{a['account'] or 'default'}**: {int(a['fans']):,}" for a in fan_summary["accounts"]]
        head = ""
        if len(fan_summary["accounts"]) > 1:
            head = f"Total **{int(fan_summary.get('total') or 0):,}** · "
        fields.append({"name": "📅 Daily Fans (resets at the daily game reset)",
                       "value": (head + " · ".join(lines))[:1024], "inline": False})

    sparks = summary.get("sparks") or []
    if sparks:
        spark_text = _format_sparks(sparks)
        if spark_text:
            fields.append({"name": "✨ Sparks (inheritance factors)", "value": spark_text[:1024], "inline": False})
    return {"title": f"{title} — {status}", "description": description, "color": color, "fields": fields}


def _build_forecast_embed(forecast, meta):
    """A standalone 'predicted career direction' panel, sent when a career starts."""
    meta = meta or {}
    desc = ""
    if meta.get("account"):
        desc += f"👤 Account **{meta['account']}** · "
    desc += f"**{meta.get('uma_name') or 'Unknown'}**"
    if meta.get("preset"):
        desc += f" · `{meta['preset']}`"
    apt = _apt_str(forecast) or "no strong aptitude"
    fields = [
        {"name": "Direction", "value": forecast.get("archetype") or "?", "inline": True},
        {"name": "Aptitude", "value": apt, "inline": True},
        {"name": "🎯 Build Target", "value": _targets_str(forecast) or "—", "inline": False},
    ]
    return {"title": "🔮 Career Forecast", "description": desc, "color": 0x5865F2, "fields": fields}


def _post(url, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json", "User-Agent": "umamusume-sweepy/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            code = getattr(resp, "status", None) or resp.getcode()
            return 200 <= int(code) < 300
    except Exception as exc:
        print(f"Discord webhook failed: {exc}", flush=True)
        return False


def get_notify_forecast(base_dir):
    return bool(_read_config(base_dir).get("notify_forecast", True))


def set_notify_forecast(base_dir, enabled):
    cfg = _read_config(base_dir)
    cfg["notify_forecast"] = bool(enabled)
    _write_config(base_dir, cfg)
    return True


def send_forecast(base_dir, forecast, meta=None):
    """POST the predicted-direction panel to Discord when a career starts. Gated by the webhook
    URL + the notify_forecast flag (default on). Failures are swallowed so they never crash a run."""
    url = get_webhook_url(base_dir)
    forecast = dict(forecast or {})
    if not url or not forecast.get("active", False):
        return False
    if not _read_config(base_dir).get("notify_forecast", True):
        return False
    meta = dict(meta or {})
    label = get_account_name(base_dir)
    if label:
        meta["account"] = label  # UI-set display name overrides the env/--account label (matches summary)
    return _post(url, {"embeds": [_build_forecast_embed(forecast, meta)]})


def send_career_summary(base_dir, summary):
    """POST a career-summary embed to the configured Discord webhook.

    Returns True on success, False if no webhook is configured or the request
    fails (failures are swallowed so they never crash a finished career)."""
    url = get_webhook_url(base_dir)
    if not url:
        return False
    summary = dict(summary or {})
    label = get_account_name(base_dir)
    if label:
        summary["account"] = label  # UI-set display name overrides the --account label
    if not summary.get("uma_name") and summary.get("card_id"):
        summary["uma_name"] = uma_name(base_dir, summary.get("card_id"))
    if "sparks" not in summary:
        summary["sparks"] = resolve_sparks(base_dir, summary.get("factor_ids") or [])
    return _post(url, {"embeds": [_build_embed(summary)]})
