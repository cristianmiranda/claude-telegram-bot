# Claude Telegram Bot

A generic Telegram bot that interfaces with Claude Code CLI. It dynamically discovers commands from `.claude/commands/` directory.

## Features

- Dynamically discovers slash commands from `.claude/commands/*.md` files
- Persistent sessions per user for multi-turn conversations
- Authorization via user ID whitelist
- Automatic typing indicators during processing
- Message splitting for long responses

## Usage with Docker

### 1. Build the image

```bash
docker build -t claude-telegram-bot ./claude-telegram-bot
```

### 2. Create your project structure

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

### 3. Create `.env` file

```env
TELEGRAM_BOT_TOKEN=your-bot-token-from-botfather
TELEGRAM_AUTHORIZED_USERS=123456789,987654321
TELEGRAM_BOT_NAME=My Bot Name
```

### 4. Create `docker-compose.yml`

```yaml
services:
  claude-bot:
    image: claude-telegram-bot
    restart: unless-stopped
    volumes:
      - ./:/app
```

### 5. Run the bot

```bash
docker-compose up -d
```

## Command Definition Format

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

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | Bot token from @BotFather |
| `TELEGRAM_AUTHORIZED_USERS` | Yes | Comma-separated user IDs |
| `TELEGRAM_BOT_NAME` | No | Bot name (default: "Claude bot") |

## Volume Mount

Mount your entire project to `/app`:

```yaml
volumes:
  - ./:/app
```

The bot expects to find in `/app`:
- `.env` - Configuration
- `.claude/commands/` - Command definitions
- `CLAUDE.md` - Agent instructions (optional but recommended)

## Local Development

```bash
cd claude-telegram-bot
pip install -e .
telegram-bot --config /path/to/your/project/.env
```

## License

MIT
