import os
import sys
import asyncio
import datetime
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
    ("!kick <عضو> [سبب]", "طرد عضو (يتطلب صلاحية الطرد)"),
    ("!ban <عضو> [سبب]", "حظر عضو (يتطلب صلاحية الحظر)"),
    ("!timeout <عضو> <دقائق> [سبب]", "إسكات عضو مؤقتًا"),
    ("!poll <سؤال> | <خيار> | <خيار>", "إنشاء تصويت بالتفاعلات"),
    ("!choose <خيار> | <خيار>", "اختيار عشوائي بين الخيارات"),
    ("!remind <ثواني> <نص>", "تذكير بعد مدة (حتى يوم)"),
    ("!botinfo", "معلومات عن البوت"),
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


# ===== أوامر الإدارة =====
@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
@commands.bot_has_permissions(kick_members=True)
@commands.guild_only()
async def kick(ctx, member: discord.Member, *, reason: str = "بدون سبب"):
    if member.top_role >= ctx.author.top_role and ctx.guild.owner_id != ctx.author.id:
        await ctx.send("⛔ لا يمكنك طرد عضو رتبته أعلى من رتبتك أو مساوية لها.")
        return
    await member.kick(reason=f"{ctx.author}: {reason}")
    await ctx.send(f"👢 تم طرد {member} — السبب: {reason}")


@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
@commands.bot_has_permissions(ban_members=True)
@commands.guild_only()
async def ban(ctx, member: discord.Member, *, reason: str = "بدون سبب"):
    if member.top_role >= ctx.author.top_role and ctx.guild.owner_id != ctx.author.id:
        await ctx.send("⛔ لا يمكنك حظر عضو رتبته أعلى من رتبتك أو مساوية لها.")
        return
    await member.ban(reason=f"{ctx.author}: {reason}", delete_message_seconds=0)
    await ctx.send(f"🔨 تم حظر {member} — السبب: {reason}")


@bot.command(name="timeout")
@commands.has_permissions(moderate_members=True)
@commands.bot_has_permissions(moderate_members=True)
@commands.guild_only()
async def timeout(ctx, member: discord.Member, minutes: int, *, reason: str = "بدون سبب"):
    if not 1 <= minutes <= 40320:  # حد ديسكورد: 28 يومًا
        await ctx.send("⚠️ المدة يجب أن تكون بين 1 و 40320 دقيقة (28 يومًا).")
        return
    until = discord.utils.utcnow() + datetime.timedelta(minutes=minutes)
    await member.timeout(until, reason=f"{ctx.author}: {reason}")
    await ctx.send(f"🔇 تم إسكات {member} لمدة {minutes} دقيقة — السبب: {reason}")


# ===== أوامر مساعدة وترفيه =====
NUMBER_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]


@bot.command(name="poll")
@commands.cooldown(1, 10, commands.BucketType.user)
async def poll(ctx, *, text: str):
    # الصيغة: !poll السؤال | خيار1 | خيار2 ...
    parts = [p.strip() for p in text.split("|") if p.strip()]
    if len(parts) < 3 or len(parts) - 1 > 10:
        await ctx.send("⚠️ الصيغة: `!poll السؤال | خيار1 | خيار2` (من 2 إلى 10 خيارات).")
        return
    question, options = parts[0], parts[1:]
    embed = discord.Embed(title=f"📊 {question}", color=discord.Color.orange())
    embed.description = "\n".join(f"{NUMBER_EMOJIS[i]} {opt}" for i, opt in enumerate(options))
    msg = await ctx.send(embed=embed)
    for i in range(len(options)):
        await msg.add_reaction(NUMBER_EMOJIS[i])


@bot.command(name="choose")
@commands.cooldown(1, 5, commands.BucketType.user)
async def choose(ctx, *, text: str):
    # الصيغة: !choose خيار1 | خيار2 | خيار3
    options = [p.strip() for p in text.split("|") if p.strip()]
    if len(options) < 2:
        await ctx.send("⚠️ الصيغة: `!choose خيار1 | خيار2` (خياران على الأقل).")
        return
    await ctx.send(f"🤖 اخترت لك: **{random.choice(options)}**")


@bot.command(name="remind")
async def remind(ctx, seconds: int, *, text: str):
    if not 1 <= seconds <= 86400:
        await ctx.send("⚠️ المدة يجب أن تكون بين 1 و 86400 ثانية (يوم).")
        return
    await ctx.send(f"⏰ سأذكّرك بعد {seconds} ثانية.")

    async def _reminder():
        await asyncio.sleep(seconds)
        try:
            await ctx.send(f"{ctx.author.mention} ⏰ تذكير: {text}")
        except discord.HTTPException:
            log.warning("Failed to send reminder to %s", ctx.author)

    bot.loop.create_task(_reminder())


@bot.command(name="botinfo")
async def botinfo(ctx):
    embed = discord.Embed(title="🤖 معلومات البوت", color=discord.Color.blurple())
    embed.add_field(name="الاسم", value=bot.user.name, inline=True)
    embed.add_field(name="السيرفرات", value=str(len(bot.guilds)), inline=True)
    embed.add_field(name="زمن الاستجابة", value=f"{round(bot.latency * 1000)} ms", inline=True)
    embed.add_field(name="discord.py", value=discord.__version__, inline=True)
    await ctx.send(embed=embed)



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

