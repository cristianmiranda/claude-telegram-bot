"""Main Telegram bot application."""

import logging
from functools import partial

from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler as TelegramMessageHandler,
    filters,
    ContextTypes,
)

from config import Config
from claude_runner import ClaudeRunner
from session_manager import SessionManager
from message_handler import MessageHandler

logger = logging.getLogger(__name__)


class ClaudeTelegramBot:
    """Generic Telegram bot powered by Claude Code.

    Dynamically discovers commands from .claude/commands/ directory.
    """

    def __init__(self, config: Config):
        """Initialize the bot.

        Args:
            config: Bot configuration.
        """
        self.config = config
        self.session_manager = SessionManager(config.sessions_file)
        self.claude_runner = ClaudeRunner(
            config.project_dir,
            config.claude_binary,
        )
        self.handler = MessageHandler(
            self.claude_runner,
            self.session_manager,
            config.authorized_users,
        )
        self.application = self._build_application()

    def _build_application(self) -> Application:
        """Build the Telegram bot application.

        Returns:
            Configured Application instance.
        """
        app = ApplicationBuilder().token(self.config.telegram_token).build()

        # Bot commands
        app.add_handler(CommandHandler("start", self._handle_start))
        app.add_handler(CommandHandler("help", self._handle_help))
        app.add_handler(CommandHandler("clear", self.handler.handle_clear))

        # Custom commands (dynamically discovered from .claude/commands/)
        for cmd in self.config.custom_commands:
            handler = self._make_command_handler(cmd)
            app.add_handler(CommandHandler(cmd, handler))

        # General message handler (must be last)
        app.add_handler(
            TelegramMessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self.handler.handle_message,
            )
        )

        # Error handler
        app.add_error_handler(self._handle_error)

        return app

    def _make_command_handler(self, command: str):
        """Create a command handler for a custom command.

        Args:
            command: Command name.

        Returns:
            Async handler function.
        """
        async def handler(
            update: Update,
            context: ContextTypes.DEFAULT_TYPE,
        ) -> None:
            await self.handler.handle_command(update, context, command)

        return handler

    async def _handle_start(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle /start command.

        Args:
            update: Telegram update object.
            context: Bot context.
        """
        if not update.message:
            return

        user = update.effective_user
        name = user.first_name if user else "User"

        # Build commands list dynamically
        cmd_lines = []
        for cmd, desc in sorted(self.config.custom_commands.items()):
            cmd_lines.append(f"- {desc}: /{cmd}")

        commands_text = "\n".join(cmd_lines) if cmd_lines else "- (no commands available)"

        bot_name = self.config.bot_name or "your assistant"
        welcome = (
            f"Hello {name}! I'm {bot_name}.\n\n"
            f"I can help you with:\n{commands_text}\n\n"
            "You can also send natural language messages.\n"
            "Use /clear to start a new session.\n"
            "Use /help for more information."
        )
        await update.message.reply_text(welcome)

    async def _handle_help(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle /help command.

        Args:
            update: Telegram update object.
            context: Bot context.
        """
        if not update.message:
            return

        # Build custom commands list dynamically
        cmd_lines = []
        for cmd, desc in sorted(self.config.custom_commands.items()):
            cmd_lines.append(f"/{cmd} - {desc}")

        custom_commands = "\n".join(cmd_lines) if cmd_lines else "(no commands available)"

        help_text = (
            "Available commands:\n\n"
            "General:\n"
            "/start - Welcome message\n"
            "/help - This help\n"
            "/clear - Clear session and start new\n\n"
            f"Commands:\n{custom_commands}\n\n"
            "You can send any message and it will be processed "
            "by Claude Code."
        )
        await update.message.reply_text(help_text)

    async def _handle_error(
        self,
        update: object,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle errors.

        Args:
            update: Telegram update object.
            context: Bot context with error info.
        """
        logger.error(f"Error handling update: {context.error}")

        if isinstance(update, Update) and update.message:
            await update.message.reply_text(
                "An error occurred. Please try again."
            )

    async def _set_commands(self) -> None:
        """Set bot commands for Telegram menu."""
        # Base commands
        commands = [
            BotCommand("start", "Welcome message"),
            BotCommand("help", "Show help"),
            BotCommand("clear", "Clear session and start new"),
        ]

        # Add custom commands dynamically
        for cmd, desc in sorted(self.config.custom_commands.items()):
            # Telegram limits description to 256 chars
            commands.append(BotCommand(cmd, desc[:256]))

        try:
            await self.application.bot.set_my_commands(commands)
            logger.info(
                f"Bot commands set successfully ({len(commands)} commands)"
            )
        except Exception as e:
            logger.error(f"Failed to set bot commands: {e}")

    def run(self) -> None:
        """Start the bot."""
        logger.info("Starting Claude Telegram Bot...")

        # Set up commands before starting
        async def post_init(app: Application) -> None:
            await self._set_commands()

        self.application.post_init = post_init

        # Run polling
        self.application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
        )
