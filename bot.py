import discord
from discord.ext import commands
from deep_translator import GoogleTranslator
import os
import logging
from pyarabic.araby import transcribe

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
# Helper functions
# ------------------------------
def arabizi_to_arabic(text: str) -> str:
    """
    Convert Franco-Arabic (Arabizi) to Arabic letters using pyarabic's transcribe.
    This handles standard Arabizi spelling and phonetic variants.
    """
    try:
        return transcribe(text)
    except Exception as e:
        log.warning("Arabizi to Arabic conversion failed: %s", e)
        return text  # fallback

async def translate_text(text: str) -> str:
    """
    Convert Franco-Arabic to Arabic, then translate to English.
    """
    try:
        arabic_text = arabizi_to_arabic(text)
        translation = translator.translate(arabic_text)
        return translation
    except Exception as e:
        log.warning("Translation failed: %s", e)
        return text

def should_send_translation(original: str, translated: str) -> bool:
    return original.strip().lower() != translated.strip().lower()

# ------------------------------
# Events
# ------------------------------
@bot.event
async def on_ready():
    log.info("✅ Logged in as %s (id=%s)", bot.user, getattr(bot.user, "id", "?"))

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
