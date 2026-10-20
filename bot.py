import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

# تشغيل خادم ويب بسيط لإيهام Render بأن التطبيق يعمل
def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    print(f"Web server started on port {port}")
    server.serve_forever()

# تشغيل خادم الويب في خلفية (Thread)
threading.Thread(target=run_web_server, daemon=True).start()

# --- إعدادات البوت ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'تم تسجيل الدخول بنجاح باسم: {bot.user.name}')

@bot.command(name='ping')
async def ping(ctx):
    await ctx.send('Pong! 🏓 البوت يعمل.')

if __name__ == "__main__":
    if not TOKEN:
        print("خطأ: يرجى وضع التوكن.")
    else:
        bot.run(TOKEN)