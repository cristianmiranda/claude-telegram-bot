"""Execute Claude Code CLI and capture output."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ClaudeExecutionError(Exception):
    """Claude CLI execution failed."""

    pass


class ClaudeRunner:
    """Execute Claude Code CLI commands."""

    def __init__(
        self,
        project_dir: Path,
        claude_binary: str = "claude",
        timeout: float = 300.0,
    ):
        """Initialize Claude runner.

        Args:
            project_dir: Directory to run Claude from (where CLAUDE.md lives).
            claude_binary: Path to claude CLI binary.
            timeout: Maximum execution time in seconds.
        """
        self.project_dir = project_dir
        self.claude_binary = claude_binary
        self.timeout = timeout

    async def run(
        self,
        message: str,
        session_id: Optional[str] = None,
        resume: bool = False,
    ) -> str:
        """Run Claude Code CLI and return the response.

        Args:
            message: The message/prompt to send to Claude.
            session_id: Session ID for conversation continuity.
            resume: If True, use --resume instead of --session-id.

        Returns:
            Claude's response text.

        Raises:
            ClaudeExecutionError: If Claude CLI fails.
            asyncio.TimeoutError: If execution exceeds timeout.
        """
        cmd = [self.claude_binary]

        # Add session handling
        if resume and session_id:
            cmd.extend(["--resume", session_id])
        elif session_id:
            cmd.extend(["--session-id", session_id])

        # Skip permission prompts (safe: bot already has authorized users check)
        cmd.append("--dangerously-skip-permissions")

        # Add output flags and message (--verbose required for stream-json)
        cmd.extend(["-p", "--verbose", "--output-format", "stream-json", message])

        logger.debug(f"Running command: {' '.join(cmd[:5])}...")
        logger.debug(f"Working directory: {self.project_dir}")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.project_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise asyncio.TimeoutError(
                    f"Claude CLI timed out after {self.timeout} seconds"
                )

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"Claude CLI failed: {error_msg}")
                raise ClaudeExecutionError(f"Claude CLI failed: {error_msg}")

            # Parse streaming JSON output
            response_text = self._parse_stream_json(stdout.decode())
            return response_text

        except FileNotFoundError:
            raise ClaudeExecutionError(
                f"Claude CLI not found: {self.claude_binary}. "
                "Make sure Claude Code is installed and in PATH."
            )
        except PermissionError:
            raise ClaudeExecutionError(
                f"Permission denied executing: {self.claude_binary}"
            )

    def _parse_stream_json(self, output: str) -> str:
        """Parse streaming JSON output from Claude CLI.

        The CLI outputs JSON objects line by line.
        We extract assistant message content.

        Args:
            output: Raw stdout from Claude CLI.

        Returns:
            Combined assistant response text.
        """
        response_text: str = ""

        for line in output.strip().split("\n"):
            if not line:
                continue

            try:
                data = json.loads(line)

                # Handle different message types
                msg_type = data.get("type")

                if msg_type == "assistant":
                    # Assistant message with nested content
                    message = data.get("message", {})
                    if isinstance(message, dict):
                        content = message.get("content", [])
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                text = block.get("text", "")
                                if text:
                                    response_text = text

                elif msg_type == "result":
                    # Final result - this is the complete response
                    result = data.get("result", "")
                    if result and isinstance(result, str):
                        response_text = result

            except json.JSONDecodeError:
                # Not JSON, might be plain text output
                if line.strip() and not response_text:
                    response_text = line

        return response_text or output

    async def run_command(
        self,
        command: str,
        session_id: Optional[str] = None,
        resume: bool = False,
    ) -> str:
        """Run a slash command through Claude.

        This wraps the command in a way Claude Code understands.

        Args:
            command: Command name (e.g., "balance", "gastos").
            session_id: Session ID for conversation continuity.
            resume: If True, use --resume.

        Returns:
            Claude's response text.
        """
        # Format as a slash command that Claude will recognize
        message = f"/{command}"
        return await self.run(message, session_id, resume)
