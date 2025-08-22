import discord
from discord.ext import commands
from translate import Translator
from franco_arabic_transliterator.franco_arabic_transliterator import FrancoArabicTransliterator
import logging
import os

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

# ------------------------------
# Translators
# ------------------------------
# Franco-Arabic -> Arabic
transliterator = FrancoArabicTransliterator()
# Arabic -> English
translator = Translator(from_lang="ar", to_lang="en")

# ------------------------------
# Helper functions
# ------------------------------
def franco_to_arabic(text: str) -> str:
    try:
        return transliterator.transliterate(text, method="lexicon")
    except Exception as e:
        log.warning("Transliteration failed: %s", e)
        return text

def arabic_to_english(text: str) -> str:
    try:
        return translator.translate(text)
    except Exception as e:
        log.warning("Translation failed: %s", e)
        return text

def full_translate(text: str) -> str:
    arabic_text = franco_to_arabic(text)
    english_text = arabic_to_english(arabic_text)
    return english_text

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

    translation = full_translate(message.content)
    if translation.strip() != message.content.strip():
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
    translation = full_translate(text)
    if translation.strip() != text.strip():
        await ctx.send(f"🌐 Translation: {translation}")
    else:
        await ctx.send("ℹ️ That already looks like English.")

# ------------------------------
# Run bot
# ------------------------------
token = os.getenv("DISCORD_BOT_TOKEN", "JOUW_DISCORD_BOT_TOKEN_HIER")
bot.run(token)
