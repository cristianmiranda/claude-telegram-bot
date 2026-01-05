"""Handle Telegram messages and invoke Claude Code CLI."""

import asyncio
import logging
from typing import Optional

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from claude_runner import ClaudeRunner, ClaudeExecutionError
from session_manager import SessionManager
from utils import (
    split_message,
    format_chunks_with_markers,
    truncate_for_log,
    format_for_telegram,
)

logger = logging.getLogger(__name__)


class MessageHandler:
    """Handle incoming Telegram messages."""

    def __init__(
        self,
        claude_runner: ClaudeRunner,
        session_manager: SessionManager,
        authorized_users: set[int],
    ):
        """Initialize message handler.

        Args:
            claude_runner: Claude CLI runner instance.
            session_manager: Session manager instance.
            authorized_users: Set of authorized Telegram user IDs.
        """
        self.claude_runner = claude_runner
        self.session_manager = session_manager
        self.authorized_users = authorized_users

    def is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized.

        Args:
            user_id: Telegram user ID.

        Returns:
            True if authorized, False otherwise.
        """
        return user_id in self.authorized_users

    async def handle_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle incoming text message.

        Args:
            update: Telegram update object.
            context: Bot context.
        """
        if not update.effective_user or not update.message:
            return

        user_id = update.effective_user.id
        username = update.effective_user.username or str(user_id)

        # Authorization check
        if not self.is_authorized(user_id):
            logger.warning(f"Unauthorized access attempt from user {user_id}")
            await update.message.reply_text("Not authorized.")
            return

        message_text = update.message.text
        if not message_text:
            return

        logger.info(f"Message from {username}: {truncate_for_log(message_text)}")

        await self._process_with_claude(update, context, message_text)

    async def handle_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        command: str,
    ) -> None:
        """Handle a slash command.

        Args:
            update: Telegram update object.
            context: Bot context.
            command: Command name (e.g., "balance", "gastos").
        """
        if not update.effective_user or not update.message:
            return

        user_id = update.effective_user.id
        username = update.effective_user.username or str(user_id)

        # Authorization check
        if not self.is_authorized(user_id):
            logger.warning(f"Unauthorized command attempt from user {user_id}")
            await update.message.reply_text("Not authorized.")
            return

        logger.info(f"Command /{command} from {username}")

        # Commands are sent as slash commands to Claude
        # Convert underscore back to hyphen (Telegram uses _ but Claude uses -)
        claude_command = command.replace("_", "-")
        await self._process_with_claude(update, context, f"/{claude_command}")

    async def _process_with_claude(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        message: str,
    ) -> None:
        """Process message through Claude CLI.

        Args:
            update: Telegram update object.
            context: Bot context.
            message: Message to send to Claude.
        """
        user_id = update.effective_user.id

        # Get or create session
        session, is_existing = self.session_manager.get_or_create_session(user_id)
        logger.debug(
            f"Session for {user_id}: {session.session_id} "
            f"(existing={is_existing}, messages={session.message_count})"
        )

        # Send typing indicator
        await self._send_typing(update, context)

        try:
            # Run Claude with typing indicator refresh
            response = await self._run_with_typing(
                update, context, message, session.session_id, is_existing
            )

            # Update session
            self.session_manager.update_session(user_id)

            # Send response
            await self._send_response(update, response)

        except asyncio.TimeoutError:
            logger.error(f"Timeout processing message for user {user_id}")
            await update.message.reply_text(
                "The operation took too long. "
                "Try again or use /clear to start over."
            )
        except ClaudeExecutionError as e:
            logger.error(f"Claude error for user {user_id}: {e}")
            await update.message.reply_text(
                f"Error executing Claude: {e}\n\n"
                "Use /clear to start a new session."
            )
        except Exception as e:
            logger.exception(f"Unexpected error for user {user_id}: {e}")
            await update.message.reply_text(
                "An unexpected error occurred. "
                "Try again or use /clear to start over."
            )

    async def _send_typing(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Send typing indicator.

        Args:
            update: Telegram update object.
            context: Bot context.
        """
        try:
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id,
                action=ChatAction.TYPING,
            )
        except Exception as e:
            logger.debug(f"Failed to send typing indicator: {e}")

    async def _run_with_typing(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        message: str,
        session_id: str,
        resume: bool,
    ) -> str:
        """Run Claude while periodically refreshing typing indicator.

        Args:
            update: Telegram update object.
            context: Bot context.
            message: Message to send to Claude.
            session_id: Session ID.
            resume: Whether to resume existing session.

        Returns:
            Claude's response.
        """
        # Start Claude task
        claude_task = asyncio.create_task(
            self.claude_runner.run(message, session_id, resume)
        )

        # Refresh typing every 4 seconds while waiting
        while not claude_task.done():
            await self._send_typing(update, context)
            try:
                await asyncio.wait_for(asyncio.shield(claude_task), timeout=4.0)
            except asyncio.TimeoutError:
                continue

        return await claude_task

    async def _send_response(
        self,
        update: Update,
        response: str,
    ) -> None:
        """Send response, splitting if necessary.

        Args:
            update: Telegram update object.
            response: Response text to send.
        """
        if not response.strip():
            response = "(No response from Claude)"

        # Format for Telegram (wrap tables in code blocks, convert headers)
        response = format_for_telegram(response)

        # Split long messages
        chunks = split_message(response)
        chunks = format_chunks_with_markers(chunks)

        for chunk in chunks:
            try:
                await update.message.reply_text(chunk, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Failed to send HTML message: {e}")
                # Try plain text fallback
                try:
                    await update.message.reply_text(
                        chunk[:4000],
                        parse_mode=None,
                    )
                except Exception:
                    pass

    async def handle_clear(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle /clear command to reset session.

        Args:
            update: Telegram update object.
            context: Bot context.
        """
        if not update.effective_user or not update.message:
            return

        user_id = update.effective_user.id

        if not self.is_authorized(user_id):
            await update.message.reply_text("Not authorized.")
            return

        cleared = self.session_manager.clear_session(user_id)
        if cleared:
            logger.info(f"Session cleared for user {user_id}")
            await update.message.reply_text(
                "Session cleared. The next message will start a new conversation."
            )
        else:
            await update.message.reply_text(
                "No active session."
            )
