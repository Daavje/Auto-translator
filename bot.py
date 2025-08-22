import discord
from discord.ext import commands
from deep_translator import GoogleTranslator
import os
import logging
import re

# ------------------------------
# Logging
# ------------------------------
logging.basicConfig(level=logging.INFO,
                    format="[%(asctime)s] %(levelname)s:%(name)s: %(message)s")
log = logging.getLogger("franco-arabic-bot")

# ------------------------------
# Bot setup
# ------------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True  # type: ignore[attr-defined]

bot = commands.Bot(command_prefix="!", intents=intents)

# Translator
translator = GoogleTranslator(source="auto", target="en")

# ------------------------------
# Franco-Arabic → Arabic mapping
# ------------------------------
FRANCO_MAP = {
    "2": "ء",
    "3": "ع",
    "4": "ش",
    "5": "خ",
    "6": "ط",
    "7": "ح",
    "8": "ق",
    "9": "ص",
    "a": "ا", "b": "ب", "t": "ت", "th": "ث",
    "j": "ج", "h": "ه", "kh": "خ", "d": "د",
    "dh": "ذ", "r": "ر", "z": "ز", "s": "س",
    "sh": "ش", "ṣ": "ص", "ḍ": "ض", "ṭ": "ط",
    "ẓ": "ظ", "ʿ": "ع", "gh": "غ", "f": "ف",
    "q": "ق", "k": "ك", "l": "ل", "m": "م",
    "n": "ن", "w": "و", "y": "ي",
}

def franco_to_arabic(text: str) -> str:
    """Convert simple Franco-Arabic to Arabic letters."""
    # eerst 2-char combinaties
    for combo in ['sh','kh','gh','th','dh']:
        text = text.replace(combo, FRANCO_MAP.get(combo, combo))
    # vervang individuele letters/nummers
    for k, v in FRANCO_MAP.items():
        text = text.replace(k, v)
    return text

# ------------------------------
# Helper functions
# ------------------------------
_normalize_re = re.compile(r"[\W_]+", re.UNICODE)

def normalize_text(s: str) -> str:
    return _normalize_re.sub(" ", s).strip().lower()

def should_send_translation(original: str, translated: str) -> bool:
    return normalize_text(original) != normalize_text(translated)

async def translate_text(text: str) -> str:
    try:
        arabic_text = franco_to_arabic(text)
        return translator.translate(arabic_text)
    except Exception as e:
        log.warning("Translation failed: %s", e)
        return text  # fallback

# ------------------------------
# Events
# ------------------------------
@bot.event
async def on_ready():
    log.info("✅ Logged in als %s (id=%s)", bot.user, getattr(bot.user, "id", "?"))

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    translation = await translate_text(message.content)
    if should_send_translation(message.content, translation):
        try:
            await message.channel.send(f"🌐 Translation: {translation}")
        except discord.HTTPException as e:
            log.error("Failed to send translation: %s", e)

    await bot.process_commands(message)

# ------------------------------
# Commands
# ------------------------------
@bot.command(name="translate", help="Translate provided text to English.")
async def translate_command(ctx: commands.Context, *, text: str):
    translation = await translate_text(text)
    if should_send_translation(text, translation):
        await ctx.send(f"🌐 Translation: {translation}")
    else:
        await ctx.send("ℹ️ That already looks like English.")

# ------------------------------
# Run bot
# ------------------------------
token = os.getenv("DISCORD_BOT_TOKEN", "JOUW_DISCORD_BOT_TOKEN_HIER")
bot.run(token)
