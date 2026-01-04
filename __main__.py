"""CLI entry point for the Telegram bot."""

import logging
from pathlib import Path
from typing import Annotated, Optional

import typer

from config import Config
from bot import ClaudeTelegramBot

__version__ = "0.1.0"

app = typer.Typer(
    name="telegram-bot",
    help="Claude Telegram Bot - Interface with Claude Code via Telegram.",
    add_completion=False,
)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        typer.echo(f"claude-telegram-bot {__version__}")
        raise typer.Exit()


@app.command()
def main(
    config_path: Annotated[
        Optional[Path],
        typer.Option(
            "--config", "-c",
            help="Path to .env file. Defaults to .env in current directory.",
        ),
    ] = None,
    debug: Annotated[
        bool,
        typer.Option(
            "--debug", "-d",
            help="Enable debug logging.",
        ),
    ] = False,
    version: Annotated[
        bool,
        typer.Option(
            "--version", "-v",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit.",
        ),
    ] = False,
) -> None:
    """Start the Claude Telegram bot.

    The bot interfaces with Claude Code CLI to process messages,
    dynamically discovering commands from .claude/commands/ directory.
    """
    # Configure logging
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=log_level,
    )
    logger = logging.getLogger(__name__)

    try:
        # Load configuration
        logger.info("Loading configuration...")
        cfg = Config.load(config_path)
        logger.info(f"Project directory: {cfg.project_dir}")
        logger.info(f"Authorized users: {cfg.authorized_users}")
        logger.info(f"Discovered commands: {list(cfg.custom_commands.keys())}")

        # Create and run bot
        logger.info("Starting bot...")
        bot = ClaudeTelegramBot(cfg)
        bot.run()

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
