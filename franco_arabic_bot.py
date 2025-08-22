"""
Discord bot: Auto-translate Franco Arabic (Arabizi) to English

Fixes the `RuntimeError: asyncio.run() cannot be called from a running event loop` by
using `bot.start()` when an event loop already exists (e.g. Jupyter/VSCode).

Usage
-----
1) Install deps:
   pip install discord.py deep-translator
2) Create a bot on https://discord.com/developers/applications, enable the
   "Message Content Intent" and invite it to your server.
3) Set your token via env var DISCORD_BOT_TOKEN or pass --token "..." at runtime.
4) Run as script:  python franco_arabic_bot.py
   In notebooks: running the cell will schedule the bot on the existing loop.

Extra
-----
- Adds a `!translate <text>` command for on-demand translation.
- Adds small, pure helper logic with unit tests. Run tests with:
    python franco_arabic_bot.py --run-tests
"""

import asyncio
import logging
import os
import re
import sys
from typing import Optional

import discord
from discord.ext import commands
from deep_translator import GoogleTranslator

# ----------------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s:%(name)s: %(message)s",
)
log = logging.getLogger("franco-arabic-bot")

# ----------------------------------------------------------------------------
# Discord Bot Setup
# ----------------------------------------------------------------------------
intents = discord.Intents.default()
# Needed so we can read message content (enable in Developer Portal too!)
intents.message_content = True
# Keep for broader compatibility with different discord.py versions
intents.messages = True  # type: ignore[attr-defined]

bot = commands.Bot(command_prefix="!", intents=intents)

# Translator (auto-detect -> English)
translator = GoogleTranslator(source="auto", target="en")

# ----------------------------------------------------------------------------
# Helper utilities (pure, testable)
# ----------------------------------------------------------------------------
_normalize_re = re.compile(r"[\W_]+", re.UNICODE)

def normalize_text(s: str) -> str:
    """Lowercase and collapse punctuation/whitespace for comparison."""
    return _normalize_re.sub(" ", s).strip().lower()


def should_send_translation(original: str, translated: str) -> bool:
    """Return True iff translation is meaningfully different from the original.

    We avoid spamming by not sending when the translation equals the original
    aside from case/punctuation differences.
    """
    return normalize_text(original) != normalize_text(translated)


async def translate_text(text: str) -> Optional[str]:
    """Translate text to English using GoogleTranslator. Returns the string or None on error."""
    try:
        return translator.translate(text)
    except Exception as e:  # pragma: no cover - network/lib errors
        log.warning("Translation failed: %s", e)
        return None

# ----------------------------------------------------------------------------
# Events & Commands
# ----------------------------------------------------------------------------
@bot.event
async def on_ready():
    log.info("✅ Logged in as %s (id=%s)", bot.user, getattr(bot.user, "id", "?"))


@bot.event
async def on_message(message: discord.Message):
    # Prevent loops & ignore other bots
    if message.author.bot:  # includes our own bot
        return

    # Perform translation
    translated = await translate_text(message.content)
    if translated is None:
        # Keep quiet in channel; just let commands continue
        await bot.process_commands(message)
        return

    # Only send if it's meaningfully different
    if should_send_translation(message.content, translated):
        try:
            await message.channel.send(f"🌐 Translation: {translated}")
        except discord.HTTPException as e:
            log.error("Failed to send translation: %s", e)

    # Allow commands to be processed
    await bot.process_commands(message)


@bot.command(name="translate", help="Translate provided text to English.")
async def translate_command(ctx: commands.Context, *, text: str):
    translated = await translate_text(text)
    if translated is None:
        await ctx.send("⚠️ Could not translate right now. Please try again.")
        return
    if should_send_translation(text, translated):
        await ctx.send(f"🌐 Translation: {translated}")
    else:
        await ctx.send("ℹ️ That already looks like English.")

# ----------------------------------------------------------------------------
# Startup (safe in both script and notebook/REPL environments)
# ----------------------------------------------------------------------------
async def _start_bot(token: str):
    await bot.start(token)


def run_bot(token: str):
    """Run the bot.

    - If no event loop is running (normal scripts), use asyncio.run().
    - If an event loop **is** running (e.g. Jupyter/VSCode), schedule bot.start()
      on the existing loop to avoid RuntimeError("asyncio.run() ...").
    """
    try:
        asyncio.run(_start_bot(token))
    except RuntimeError as e:
        if "asyncio.run() cannot be called from a running event loop" in str(e):
            # Environment already has an event loop (e.g., notebooks)
            loop = asyncio.get_event_loop()
            loop.create_task(_start_bot(token))
            print(
                "ℹ️ Detected an active event loop; scheduled bot.start() on it.\n"
                "   Keep this process/cell alive to keep the bot running."
            )
        else:
            raise


# ----------------------------------------------------------------------------
# CLI entry point and simple tests
# ----------------------------------------------------------------------------

def _run_tests():  # pragma: no cover - invoked via CLI
    import unittest

    class TestHelpers(unittest.TestCase):
        def test_normalize_text(self):
            self.assertEqual(normalize_text("Hello, World!"), "hello world")
            self.assertEqual(normalize_text("  SALAM__Alaikum  "), "salam alaikum")

        def test_should_send_translation_identical(self):
            self.assertFalse(should_send_translation("hello", "hello"))
            self.assertFalse(should_send_translation("Hello", "hello"))
            self.assertFalse(should_send_translation("hey!!!", "hey"))

        def test_should_send_translation_different(self):
            self.assertTrue(should_send_translation("3omri", "my life"))
            self.assertTrue(should_send_translation("7abibi", "my dear"))
            self.assertTrue(should_send_translation("ana kwayes", "i am fine"))

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestHelpers)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        sys.exit(1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Franco Arabic → English Discord bot")
    parser.add_argument("--token", type=str, default=os.getenv("DISCORD_BOT_TOKEN", "JOUW_DISCORD_BOT_TOKEN_HIER"))
    parser.add_argument("--run-tests", action="store_true", help="Run unit tests and exit")
    args = parser.parse_args()

    if args.run_tests:
        _run_tests()
    else:
        run_bot(args.token)
