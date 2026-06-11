# Mcqueen Uma Auto

A web-controlled automation bot for the **MANT / Trackblazer ("Make a New Track")** career scenario in *Umamusume: Pretty Derby*. It plays a full career end-to-end through the in-game API and is driven from a small local web dashboard.

Built on the **Sweepy** decision engine, then heavily extended with a smarter training brain, deck-aware shopping, account-safety guards, and an easier login flow.

> [!WARNING]
> Automating gameplay may violate the game's Terms of Service and can get your account flagged or restricted. This project is for **personal & educational use** — use it at your own risk. Run gently and don't hammer the servers.

---

## ✨ Features

- 🤖 **Full-career autoplay** — Junior → Classic → Senior → Twinkle Star Climax, all via the game API.
- 🧠 **Smart training engine**
  - Explicit **rainbow / friendship-training** scoring (prioritizes maxed-bond support trainings).
  - **Stat-balancing** toward your per-stat targets so the build isn't lopsided.
  - **Hint prioritization** scaled by how many partners are hinting.
  - **Wit-as-rest** energy efficiency — recover via Wit (which still trains + gives SP) instead of wasting a rest turn.
  - **Skill-Point (SP) awareness** — values SP gains so it collects points toward better skills.
  - **Energy-rescue** — spend Vita / Good-Luck Charm to run a great training instead of resting.
- 🛒 **Deck-aware shop** — buys & uses shop items every turn; stat-specific items (**Ankle Weights / Training Applications**) are prioritized to match your support-card deck; **Cleat ("Golden") Hammers** are reserved for the climax races.
- 🛡️ **Auto-backoff circuit breaker** — if the server rejects too many calls in a short window (throttling), the bot **stops itself** instead of hammering, to protect your account.
- ▶️ **RUN** with a confirmation popup showing how many careers will run · ⏸️ **PAUSE / RESUME** mid-career · ⚡ **NO CD** mode.
- 🔁 **Multi-run loop** — run N careers back-to-back.
- 🔑 **Captured-ticket login** — logs in with the Steam session ticket captured from the running game. No manual Steam credentials, and it avoids the `1055` account-mismatch error.
- 🔄 **RE-CAPTURE** — switch to a different Uma account without restarting the server.
- 👥 **Multi-account** — run several accounts at once, each as its own process on its own port.
- 🔔 **Discord notifications** — webhook embed when a career finishes (account, duration, skills bought, sparks).

---

## 📦 Requirements

- **Windows** with *Umamusume: Pretty Derby* (Steam) installed, updated, and logged into the account you want to bot.
- **Python 3.10+**
- **Node.js** (used to generate the Steam session ticket)

See [`DEPENDENCIES.md`](DEPENDENCIES.md) for the full list.

---

## 🚀 Installation

> [!IMPORTANT]
> Install Node first, run `npm i`, then install the Python requirements.

```bash
# 1) Node.js (Steam ticket helper)
winget install -e --id OpenJS.NodeJS
npm i

# 2) Python dependencies
pip install -r requirements.txt
```

---

## ▶️ Usage

```bash
python main.py 1616 --account A
```

Every start captures auth **fresh**: the game launches via Steam, the login is
captured at the menu, the game closes, and the bot serves. Auth lives only in
memory for that process — nothing is saved to disk. (Saved auth was removed: the
short-lived Steam ticket can't be persisted anyway, so "saved" logins only
produced confusing `No Steam ticket available` dead-ends.)

Then open the dashboard at **http://127.0.0.1:1616**.

- `PORT` defaults to `1616` (or the `SWEEPY_PORT` env var).
- `--account NAME` is a display label (Discord notifications / multi-instance bookkeeping).

### Multiple accounts at once

Each account runs as its own process on its own port:

```bash
python main.py 1616 --account A
python main.py 1617 --account B
```

---

## 🖥️ Dashboard

- **RUN** (green) — starts a career; a popup confirms how many careers will run.
- **PAUSE / RESUME** — hold the bot mid-career without dropping the session.
- **NO CD** — removes action cooldowns.
- **RE-CAPTURE** — swap to another Uma account without restarting the server.
- Presets, live status, per-turn logs, and skill/item/spark readouts.

Training behavior is tunable through the active **preset** (rainbow weights, stat targets, energy thresholds, shop tiers, deck-match toggles, SP weight, and more).

---

## 🙏 Credits

Based on the **Sweepy** decision engine. This fork extends it with the training, shop, safety, and login features listed above.

---

## 📸 Screenshots

<img width="190" height="140" alt="image" src="https://github.com/user-attachments/assets/a376b9e0-832e-45ea-add4-499a9f76a284" />
<img width="190" height="158" alt="image" src="https://github.com/user-attachments/assets/428a7704-0729-4dc3-890f-246fb0a94774" />
<img width="190" height="140" alt="image" src="https://github.com/user-attachments/assets/65edac1a-91c0-4559-8393-7432418afa18" />
<img width="190" height="140" alt="image" src="https://github.com/user-attachments/assets/3193d3ce-2a3a-4a77-9ed6-c04702083b60" />
<img width="190" height="140" alt="image" src="https://github.com/user-attachments/assets/d58f6376-76c7-455e-a16d-9bb9d92db969" />
<img width="190" height="140" alt="image" src="https://github.com/user-attachments/assets/d097751f-966f-4f3f-ba5b-3608cac6bdbe" />
<img width="190" height="140" alt="image" src="https://github.com/user-attachments/assets/671eb304-cb0b-4f02-9023-ea313df2f987" />
<img width="190" height="140" alt="image" src="https://github.com/user-attachments/assets/f1ecf7d6-1e18-45d6-8143-66b877d9c786" />
<img width="190" height="140" alt="image" src="https://github.com/user-attachments/assets/94ea9609-54db-4322-a0f3-9168a70932e0" />
<img width="190" height="140" alt="image" src="https://github.com/user-attachments/assets/d64d2197-217f-40c5-a57e-3ccd5c868e2d" />
<img width="190" height="140" alt="image" src="https://github.com/user-attachments/assets/cacd2cf3-b880-4b1e-8818-af33a30bcf38" />
<img width="190" height="140" alt="image" src="https://github.com/user-attachments/assets/3bdd80ec-cb77-4637-9f61-e3f8fab8d85d" />
<img width="235" height="226" alt="image" src="https://github.com/user-attachments/assets/ffb9960a-347d-4d7f-8c0d-57ff96f72b6a" />
<img width="317" height="317" alt="image" src="https://github.com/user-attachments/assets/61c4c0dd-85bc-4517-84c1-021fcf5d47fa" />
<img width="428" height="605" alt="image" src="https://github.com/user-attachments/assets/07ca8a7f-3f89-4667-a5c6-d50ab5b10fe3" />
