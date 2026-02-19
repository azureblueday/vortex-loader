# Vortex Loader

> Remote Execution Interface — Discord bot + Vercel API backend

---

## Project Structure

```
vortex-loader/
├── api/
│   ├── index.js        ← GET /          — dark landing page
│   └── control.js      ← POST /api/control — script control API
├── bot.py              ← Discord.py slash-command bot
├── config.json         ← Runtime config (auto-created, git-ignored)
├── vercel.json         ← Vercel routing config
├── package.json        ← Node deps for Vercel
├── requirements.txt    ← Python deps for the bot
└── .env.example        ← Environment variable template
```

---

## 1 — Deploy the Vercel Backend

### Prerequisites
- [Vercel CLI](https://vercel.com/docs/cli) installed (`npm i -g vercel`)
- A Vercel account

### Steps

```bash
cd vortex-loader
npm install          # install Vercel CLI locally
vercel               # follow prompts — deploy to Vercel
```

Set these **environment variables** in the Vercel dashboard
(`Project → Settings → Environment Variables`):

| Variable  | Description                          |
|-----------|--------------------------------------|
| `API_KEY`  | A long random secret string — must match the bot's `API_KEY` |

The two routes are:

| Route          | Method | Description          |
|----------------|--------|----------------------|
| `/`            | GET    | Dark landing page    |
| `/api/control` | POST   | Script control API   |

---

## 2 — Run the Discord Bot

### Prerequisites
- Python 3.11+
- A Discord application + bot token
  (enable **applications.commands** scope & **bot** scope)

### Install dependencies

```bash
pip install -r requirements.txt
```

### Configure environment

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

```env
DISCORD_TOKEN=your_discord_bot_token
API_URL=https://your-project.vercel.app
API_KEY=your_secret_api_key_here        # must match Vercel env var
```

### Start the bot

```bash
python bot.py
```

On first run the bot syncs slash commands globally (may take up to 1 hour to propagate to all servers, instant in the test guild).

---

## 3 — Configure via Discord

All configuration is done through `/config` slash commands (Administrator only).

| Command | Description |
|---------|-------------|
| `/config setlog #channel` | Set the channel where execution logs are posted |
| `/config setrole @role` | Set the role allowed to run scripts |
| `/config bindscript <name> #channel` | Restrict a script to a specific channel |
| `/config unbindscript <name>` | Remove channel restriction |
| `/config view` | Show current configuration |

---

## 4 — Script Commands

These require the configured allowed role.

| Command | Description |
|---------|-------------|
| `/run <script> <roblox_username>` | Execute a script for a Roblox user |
| `/setscript <script> <new_version>` | Update script to a new version |
| `/kickall <script> <reason> <roblox_username>` | Kick all players |
| `/shutdown <script>` | Send shutdown signal |
| `/status <script>` | Check script status |

---

## 5 — Adding New Scripts

No code changes required. Just:

1. Bind a channel: `/config bindscript myNewScript #channel`
2. Use the script commands from that channel

To implement real logic, edit the handler stubs in `api/control.js`:

```js
async function handleRun(data) { ... }
async function handleSetScript(data) { ... }
async function handleKickAll(data) { ... }
async function handleShutdown(data) { ... }
async function handleStatus(data) { ... }
```

---

## 6 — API Reference

**POST** `/api/control`

Headers:
```
Authorization: Bearer <API_KEY>
Content-Type: application/json
```

Body:
```json
{
  "action": "run",
  "data": {
    "script": "my_script",
    "roblox_username": "Player123"
  }
}
```

Response:
```json
{
  "success": true,
  "message": "Script executed successfully",
  "script": "my_script",
  "roblox_username": "Player123"
}
```

Valid actions: `run` · `set_script` · `kick_all` · `shutdown` · `status`

---

## Security Notes

- The `API_KEY` is validated on every request — keep it secret
- `config.json` is git-ignored and only lives on the bot host machine
- All sensitive IDs (channels, roles) are stored by Discord snowflake ID, not names
