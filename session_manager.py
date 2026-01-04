"""Session management for maintaining conversation context per user."""

import json
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class SessionInfo:
    """Information about a user's session."""

    session_id: str
    created_at: str
    last_used: str
    message_count: int = 0

    def touch(self) -> None:
        """Update last_used timestamp and increment message count."""
        self.last_used = datetime.utcnow().isoformat() + "Z"
        self.message_count += 1


class SessionManager:
    """Manage Claude Code session IDs per Telegram user."""

    def __init__(self, sessions_file: Path):
        """Initialize session manager.

        Args:
            sessions_file: Path to JSON file for session persistence.
        """
        self.sessions_file = sessions_file
        self._sessions: dict[int, SessionInfo] = {}
        self._load()

    def _load(self) -> None:
        """Load sessions from JSON file."""
        if not self.sessions_file.exists():
            return

        try:
            with open(self.sessions_file, "r") as f:
                data = json.load(f)

            users = data.get("users", {})
            for user_id_str, session_data in users.items():
                try:
                    user_id = int(user_id_str)
                    self._sessions[user_id] = SessionInfo(**session_data)
                except (ValueError, TypeError):
                    continue
        except (json.JSONDecodeError, IOError):
            # Start fresh if file is corrupted
            self._sessions = {}

    def _save(self) -> None:
        """Persist sessions to JSON file."""
        data = {
            "users": {
                str(user_id): asdict(session)
                for user_id, session in self._sessions.items()
            }
        }

        with open(self.sessions_file, "w") as f:
            json.dump(data, f, indent=2)

    def get_session(self, user_id: int) -> Optional[SessionInfo]:
        """Get existing session for user.

        Args:
            user_id: Telegram user ID.

        Returns:
            SessionInfo if exists, None otherwise.
        """
        return self._sessions.get(user_id)

    def create_session(self, user_id: int) -> SessionInfo:
        """Create new session for user.

        Args:
            user_id: Telegram user ID.

        Returns:
            Newly created SessionInfo.
        """
        now = datetime.utcnow().isoformat() + "Z"
        session = SessionInfo(
            session_id=str(uuid.uuid4()),
            created_at=now,
            last_used=now,
            message_count=0,
        )
        self._sessions[user_id] = session
        self._save()
        return session

    def get_or_create_session(self, user_id: int) -> tuple[SessionInfo, bool]:
        """Get existing session or create new one.

        Args:
            user_id: Telegram user ID.

        Returns:
            Tuple of (SessionInfo, is_existing).
        """
        existing = self.get_session(user_id)
        if existing:
            return existing, True
        return self.create_session(user_id), False

    def update_session(self, user_id: int) -> None:
        """Update session's last_used timestamp.

        Args:
            user_id: Telegram user ID.
        """
        session = self._sessions.get(user_id)
        if session:
            session.touch()
            self._save()

    def clear_session(self, user_id: int) -> bool:
        """Clear session for user.

        Args:
            user_id: Telegram user ID.

        Returns:
            True if session existed and was cleared, False otherwise.
        """
        if user_id in self._sessions:
            del self._sessions[user_id]
            self._save()
            return True
        return False

    def get_all_sessions(self) -> dict[int, SessionInfo]:
        """Get all active sessions.

        Returns:
            Dict mapping user_id to SessionInfo.
        """
        return self._sessions.copy()
