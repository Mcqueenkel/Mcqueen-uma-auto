"""Discord webhook notifications for finished careers.

The webhook URL is stored in uma_runtime/discord.json (gitignored) so it never
reaches the repo. Sending uses only the standard library (urllib), so no extra
dependency is needed.
"""

import json
import urllib.request
from pathlib import Path


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
    sparks = summary.get("sparks") or []
    if sparks:
        spark_text = _format_sparks(sparks)
        if spark_text:
            fields.append({"name": "✨ Sparks (inheritance factors)", "value": spark_text[:1024], "inline": False})
    return {"title": f"{title} — {status}", "description": description, "color": color, "fields": fields}


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
    payload = {"embeds": [_build_embed(summary)]}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
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
