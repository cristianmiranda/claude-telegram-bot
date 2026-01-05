"""Configuration loading from .env file."""

import re
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
import os


def discover_commands(project_dir: Path) -> dict[str, str]:
    """Discover custom commands from .claude/commands/ directory.

    Reads all .md files and extracts the description from YAML front-matter.

    Args:
        project_dir: Path to project root (where .claude/ lives).

    Returns:
        Dict mapping command name to description.
        Example: {"balance": "View all account balances"}
    """
    commands_dir = project_dir / ".claude" / "commands"
    commands = {}

    if not commands_dir.exists():
        return commands

    for md_file in commands_dir.glob("*.md"):
        # Command name: filename without .md, replace - with _
        cmd_name = md_file.stem.replace("-", "_")

        # Read file and extract description from YAML front-matter
        try:
            content = md_file.read_text(encoding="utf-8")
            # Match YAML front-matter: ---\ndescription: "..."\n---
            match = re.search(
                r'^---\s*\n.*?description:\s*["\'](.+?)["\']\s*\n.*?---',
                content,
                re.DOTALL,
            )
            if match:
                description = match.group(1)
                # Remove emoji prefix if present (e.g., " - Ver saldos")
                if " - " in description:
                    description = description.split(" - ", 1)[1]
                commands[cmd_name] = description
            else:
                # Fallback: use command name as description
                commands[cmd_name] = cmd_name.replace("_", " ").title()
        except Exception:
            # Skip files that can't be read
            continue

    return commands


@dataclass
class Config:
    """Bot configuration loaded from environment."""

    telegram_token: str
    authorized_users: set[int]
    project_dir: Path
    sessions_file: Path
    custom_commands: dict[str, str] = field(default_factory=dict)
    bot_name: str = "Claude bot"
    claude_binary: str = "claude"
    claude_model: str | None = None

    @classmethod
    def load(cls, env_path: Path | None = None) -> "Config":
        """Load configuration from .env file.

        Args:
            env_path: Path to .env file. If None, searches in current dir.

        Returns:
            Config instance with loaded values.

        Raises:
            ValueError: If required environment variables are missing.
        """
        if env_path:
            env_path = Path(env_path).resolve()
            if not env_path.exists():
                raise ValueError(f".env file not found at: {env_path}")
            load_dotenv(env_path)
        else:
            load_dotenv()

        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            raise ValueError(
                f"TELEGRAM_BOT_TOKEN not found in environment. "
                f"Loaded from: {env_path if env_path else 'default .env'}"
            )

        users_str = os.getenv("TELEGRAM_AUTHORIZED_USERS", "")
        if not users_str:
            raise ValueError("TELEGRAM_AUTHORIZED_USERS not found in environment")

        authorized_users = set()
        for user_id in users_str.split(","):
            user_id = user_id.strip()
            if user_id:
                try:
                    authorized_users.add(int(user_id))
                except ValueError:
                    raise ValueError(f"Invalid user ID: {user_id}")

        if not authorized_users:
            raise ValueError("No authorized users configured")

        # Determine project directory (where CLAUDE.md lives)
        if env_path:
            project_dir = env_path.parent.resolve()
        else:
            project_dir = Path.cwd().resolve()

        # Store sessions in user's home directory (writable in Docker)
        home_dir = Path.home()
        sessions_file = home_dir / ".telegram-sessions.json"

        # Discover custom commands from .claude/commands/
        custom_commands = discover_commands(project_dir)

        # Optional bot name for personalization
        bot_name = os.getenv("TELEGRAM_BOT_NAME", "Claude bot")

        # Optional Claude model (e.g., "sonnet", "opus", "haiku")
        claude_model = os.getenv("CLAUDE_MODEL")

        return cls(
            telegram_token=token,
            authorized_users=authorized_users,
            project_dir=project_dir,
            sessions_file=sessions_file,
            custom_commands=custom_commands,
            bot_name=bot_name,
            claude_model=claude_model,
        )
