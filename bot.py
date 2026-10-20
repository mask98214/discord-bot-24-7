import os
import sys
import random
import logging
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

import discord
from discord.ext import commands
from dotenv import load_dotenv

# --- سجلات التشغيل ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("discord-bot")


# تشغيل خادم ويب بسيط لإبقاء الخدمة نشطة على Railway
def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHTTPRequestHandler)
    log.info("Web server started on port %s", port)
    server.serve_forever()


threading.Thread(target=run_web_server, daemon=True).start()

# --- إعدادات البوت ---
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

EIGHT_BALL_ANSWERS = [
    "نعم بالتأكيد ✅",
    "الأمر غير واضح، حاول مرة أخرى 🤔",
    "لا أعتقد ذلك ❌",
    "من المرجح ذلك 👍",
    "لا تعتمد على ذلك 🚫",
    "الإجابة نعم ✨",
    "الإجابة لا 🙅",
    "ربما 🎲",
]

COMMANDS_INFO = [
    ("!help", "عرض هذه القائمة"),
    ("!ping", "عرض زمن استجابة البوت"),
    ("!say <نص>", "إعادة النص وحذف رسالتك"),
    ("!coinflip", "رمي عملة (صورة أو كتابة)"),
    ("!roll [عدد الأوجه]", "رمي نرد (افتراضي 6)"),
    ("!8ball <سؤال>", "اسأل الكرة السحرية"),
    ("!avatar [عضو]", "عرض صورة العضو الشخصية"),
    ("!userinfo [عضو]", "معلومات عن العضو"),
    ("!serverinfo", "معلومات عن السيرفر"),
    ("!clear <عدد>", "حذف رسائل (يتطلب صلاحية إدارة الرسائل)"),
]


@bot.event
async def on_ready():
    print("=" * 40)
    print(f"Bot name   : {bot.user.name}")
    print(f"Bot ID     : {bot.user.id}")
    print(f"Guilds     : {len(bot.guilds)}")
    print(f"discord.py : {discord.__version__}")
    print("=" * 40)
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name="!help")
    )
    log.info("تم تسجيل الدخول بنجاح باسم: %s", bot.user.name)


@bot.command(name="help")
async def help_command(ctx):
    embed = discord.Embed(
        title="📖 قائمة الأوامر",
        description="\n".join(f"`{cmd}` — {desc}" for cmd, desc in COMMANDS_INFO),
        color=discord.Color.blurple(),
    )
    embed.set_footer(text=f"طلب بواسطة {ctx.author}")
    await ctx.send(embed=embed)


@bot.command(name="ping")
async def ping(ctx):
    latency = round(bot.latency * 1000)
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"البوت يعمل — زمن الاستجابة: **{latency} ms**",
        color=discord.Color.green(),
    )
    await ctx.send(embed=embed)


@bot.command(name="say")
async def say(ctx, *, text: str):
    try:
        await ctx.message.delete()
    except discord.HTTPException:
        pass
    await ctx.send(text[:1900])


@bot.command(name="coinflip")
@commands.cooldown(1, 5, commands.BucketType.user)
async def coinflip(ctx):
    result = random.choice(["صورة 🪙", "كتابة 🪙"])
    await ctx.send(f"النتيجة: **{result}**")


@bot.command(name="roll")
@commands.cooldown(1, 5, commands.BucketType.user)
async def roll(ctx, sides: int = 6):
    if not 2 <= sides <= 1000:
        await ctx.send("⚠️ عدد الأوجه يجب أن يكون بين 2 و 1000.")
        return
    await ctx.send(f"🎲 رميت نردًا من {sides} أوجه: **{random.randint(1, sides)}**")


@bot.command(name="8ball")
@commands.cooldown(1, 5, commands.BucketType.user)
async def eight_ball(ctx, *, question: str):
    await ctx.send(f"🎱 **السؤال:** {question}\n**الجواب:** {random.choice(EIGHT_BALL_ANSWERS)}")


@bot.command(name="avatar")
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"صورة {member.display_name}", color=discord.Color.blurple())
    embed.set_image(url=member.display_avatar.url)
    await ctx.send(embed=embed)


@bot.command(name="userinfo")
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(
        title=f"👤 {member}",
        color=member.color if member.color.value else discord.Color.blurple(),
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="ID", value=str(member.id), inline=False)
    embed.add_field(name="انضم للسيرفر", value=discord.utils.format_dt(member.joined_at, "D") if member.joined_at else "غير معروف", inline=True)
    embed.add_field(name="تاريخ إنشاء الحساب", value=discord.utils.format_dt(member.created_at, "D"), inline=True)
    embed.add_field(name="أعلى رتبة", value=member.top_role.mention, inline=True)
    await ctx.send(embed=embed)


@bot.command(name="serverinfo")
@commands.guild_only()
async def serverinfo(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"🏠 {guild.name}", color=discord.Color.blurple())
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="المالك", value=str(guild.owner), inline=True)
    embed.add_field(name="عدد الأعضاء", value=str(guild.member_count), inline=True)
    embed.add_field(name="تاريخ الإنشاء", value=discord.utils.format_dt(guild.created_at, "D"), inline=False)
    await ctx.send(embed=embed)


@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
@commands.guild_only()
async def clear(ctx, amount: int):
    if not 1 <= amount <= 100:
        await ctx.send("⚠️ العدد يجب أن يكون بين 1 و 100.")
        return
    deleted = await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🧹 تم حذف {len(deleted) - 1} رسالة.", delete_after=5)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("⛔ ليست لديك صلاحية لاستخدام هذا الأمر.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"⚠️ ناقص معامل: `{error.param.name}`. اكتب `!help` لمعرفة الاستخدام.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("⚠️ قيمة غير صالحة للمعامل. تحقق من الأمر وحاول مرة أخرى.")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ انتظر {error.retry_after:.1f} ثانية قبل استخدام الأمر مرة أخرى.")
    elif isinstance(error, commands.NoPrivateMessage):
        await ctx.send("⚠️ هذا الأمر يعمل داخل السيرفرات فقط.")
    else:
        log.error("Unhandled command error in %s", ctx.command, exc_info=error)
        await ctx.send("❌ حدث خطأ غير متوقع أثناء تنفيذ الأمر.")


if __name__ == "__main__":
    if not TOKEN:
        print("خطأ: يرجى وضع التوكن (DISCORD_TOKEN).")
        sys.exit(1)
    bot.run(TOKEN)

