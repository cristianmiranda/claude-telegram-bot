# 🤖 Claude Telegram Bot

A generic Telegram bot that interfaces with Claude Code CLI. It dynamically discovers commands from `.claude/commands/` directory.

## ✨ Features

- 🔍 Dynamically discovers slash commands from `.claude/commands/*.md` files
- 💬 Persistent sessions per user for multi-turn conversations
- 🔐 Authorization via user ID whitelist
- ⌨️ Automatic typing indicators during processing
- 📄 Message splitting for long responses

## 🐳 Usage with Docker

### 1️⃣ Create your project structure

Your project directory should have:

```
your-project/
├── .env                    # Bot configuration
├── .claude/
│   └── commands/           # Your command definitions
│       ├── command1.md
│       └── command2.md
├── CLAUDE.md               # Agent instructions
└── docker-compose.yml      # Docker Compose config
```

### 2️⃣ Create `.env` file

```env
TELEGRAM_BOT_TOKEN=your-bot-token-from-botfather
TELEGRAM_AUTHORIZED_USERS=123456789,987654321
TELEGRAM_BOT_NAME=My Bot Name
```

### 3️⃣ Create `docker-compose.yml`

```yaml
services:
  claude-bot:
    image: ghcr.io/cristianmiranda/claude-telegram-bot:latest
    restart: unless-stopped
    volumes:
      - ./:/app
      - ~/.claude:/home/claude/.claude  # Claude CLI authentication
```

### 4️⃣ Run the bot

```bash
docker-compose up -d
```

## 📝 Command Definition Format

Create `.md` files in `.claude/commands/` with YAML front-matter:

```markdown
---
description: "emoji - Short description of the command"
---

Instructions for Claude on how to handle this command...
```

The filename (without `.md`) becomes the command name:
- `balance.md` → `/balance`
- `my-command.md` → `/my_command` (hyphens convert to underscores)

## ⚙️ Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | ✅ | Bot token from @BotFather |
| `TELEGRAM_AUTHORIZED_USERS` | ✅ | Comma-separated user IDs |
| `TELEGRAM_BOT_NAME` | ❌ | Bot name (default: "Claude bot") |

## 📁 Volume Mounts

### Project Directory

Mount your entire project to `/app`:

```yaml
volumes:
  - ./:/app
```

The bot expects to find in `/app`:
- `.env` → Configuration
- `.claude/commands/` → Command definitions
- `CLAUDE.md` → Agent instructions (optional but recommended)

### 🔑 Claude CLI Authentication

Mount your local Claude CLI configuration to enable authentication:

```yaml
volumes:
  - ~/.claude:/home/claude/.claude
```

> ⚠️ The container runs as the `claude` user (not root) because the Claude CLI requires a non-root user. You must authenticate on the host machine first by running `claude` and completing the login flow.

## 🛠️ Local Development

```bash
cd claude-telegram-bot
pip install -e .
telegram-bot --config /path/to/your/project/.env
```

## 📄 License

MIT
