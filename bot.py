import os
import sys
import random
import asyncio
import logging
import threading
import datetime
from typing import Optional
from http.server import HTTPServer, SimpleHTTPRequestHandler

import discord
from discord import app_commands
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

# أوامر Slash لا تحتاج صلاحية قراءة محتوى الرسائل
intents = discord.Intents.default()


class RailwayBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # الأوامر تُسجَّل على مستوى كل سيرفر (تظهر فورًا عند كتابة /)
        # بدلًا من المزامنة العامة (قد تستغرق حتى ساعة).
        # نحذف أي أوامر عامة قديمة حتى لا تظهر مكررة، ثم نعيد إضافة الأوامر محليًا.
        commands_list = list(self.tree.get_commands())
        self.tree.clear_commands(guild=None)
        await self.tree.sync()
        for cmd in commands_list:
            self.tree.add_command(cmd)
        log.info("تم حذف الأوامر العامة القديمة (إن وجدت)")


bot = RailwayBot()
tree = bot.tree

NUMBER_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
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
reminder_tasks = set()

COMMAND_GROUPS = [
    ("🛠️ عام", [
        ("/help", "عرض هذه القائمة"),
        ("/ping", "عرض زمن استجابة البوت"),
        ("/botinfo", "معلومات عن البوت"),
        ("/serverinfo", "معلومات عن السيرفر"),
        ("/userinfo [عضو]", "معلومات عن العضو"),
        ("/avatar [مستخدم]", "عرض الصورة الشخصية"),
    ]),
    ("🎮 ترفيه وأدوات", [
        ("/say <نص>", "يرسل البوت النص"),
        ("/coinflip", "رمي عملة (صورة أو كتابة)"),
        ("/roll [عدد الأوجه]", "رمي نرد (افتراضي 6)"),
        ("/8ball <سؤال>", "اسأل الكرة السحرية"),
        ("/choose <خيار> | <خيار>", "اختيار عشوائي بين الخيارات"),
        ("/poll <سؤال> <خيار1> <خيار2>", "تصويت بالتفاعلات (حتى 5 خيارات)"),
        ("/remind <ثواني> <نص>", "تذكير بعد مدة (حتى يوم)"),
    ]),
    ("🛡️ إدارة", [
        ("/clear <عدد>", "حذف رسائل (إدارة الرسائل)"),
        ("/kick <عضو> [سبب]", "طرد عضو (صلاحية الطرد)"),
        ("/ban <عضو> [سبب]", "حظر عضو (صلاحية الحظر)"),
        ("/timeout <عضو> <دقائق> [سبب]", "إسكات عضو مؤقتًا"),
    ]),
]


async def sync_guild_commands(guild: discord.Object):
    # نسخ الأوامر إلى السيرفر ومزامنتها فورًا
    bot.tree.copy_global_to(guild=guild)
    synced = await bot.tree.sync(guild=guild)
    log.info("تمت مزامنة %d أمر في السيرفر: %s", len(synced), guild.name)


@bot.event
async def on_guild_join(guild: discord.Guild):
    await sync_guild_commands(guild)


@bot.event
async def on_ready():
    print("=" * 40)
    print(f"Bot name   : {bot.user.name}")
    print(f"Bot ID     : {bot.user.id}")
    print(f"Guilds     : {len(bot.guilds)}")
    print(f"discord.py : {discord.__version__}")
    print("=" * 40)
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name="/help")
    )
    log.info("تم تسجيل الدخول بنجاح باسم: %s", bot.user.name)
    for guild in bot.guilds:
        await sync_guild_commands(guild)


# ===== عام =====
@tree.command(name="help", description="عرض قائمة الأوامر")
async def help_cmd(interaction: discord.Interaction):
    total = sum(len(cmds) for _, cmds in COMMAND_GROUPS)
    embed = discord.Embed(title="📖 قائمة الأوامر", color=discord.Color.blurple())
    for title, cmds in COMMAND_GROUPS:
        embed.add_field(
            name=title,
            value="\n".join(f"`{cmd}` — {desc}" for cmd, desc in cmds),
            inline=False,
        )
    embed.set_footer(text=f"إجمالي الأوامر: {total}")
    await interaction.response.send_message(embed=embed)


@tree.command(name="ping", description="عرض زمن استجابة البوت")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"البوت يعمل — زمن الاستجابة: **{latency} ms**",
        color=discord.Color.green(),
    )
    await interaction.response.send_message(embed=embed)


@tree.command(name="botinfo", description="معلومات عن البوت")
async def botinfo(interaction: discord.Interaction):
    embed = discord.Embed(title="🤖 معلومات البوت", color=discord.Color.blurple())
    embed.add_field(name="الاسم", value=bot.user.name, inline=True)
    embed.add_field(name="السيرفرات", value=str(len(bot.guilds)), inline=True)
    embed.add_field(name="زمن الاستجابة", value=f"{round(bot.latency * 1000)} ms", inline=True)
    embed.add_field(name="discord.py", value=discord.__version__, inline=True)
    await interaction.response.send_message(embed=embed)


@tree.command(name="serverinfo", description="معلومات عن السيرفر")
@app_commands.guild_only()
async def serverinfo(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(title=f"🏠 {guild.name}", color=discord.Color.blurple())
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="المالك", value=str(guild.owner), inline=True)
    embed.add_field(name="عدد الأعضاء", value=str(guild.member_count), inline=True)
    embed.add_field(name="تاريخ الإنشاء", value=discord.utils.format_dt(guild.created_at, "D"), inline=False)
    await interaction.response.send_message(embed=embed)


@tree.command(name="userinfo", description="معلومات عن عضو")
@app_commands.guild_only()
@app_commands.describe(member="العضو المراد معرفة معلوماته")
async def userinfo(interaction: discord.Interaction, member: Optional[discord.Member] = None):
    member = member or interaction.user
    embed = discord.Embed(
        title=f"👤 {member}",
        color=member.color if member.color.value else discord.Color.blurple(),
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="ID", value=str(member.id), inline=False)
    joined = discord.utils.format_dt(member.joined_at, "D") if member.joined_at else "غير معروف"
    embed.add_field(name="انضم للسيرفر", value=joined, inline=True)
    embed.add_field(name="تاريخ إنشاء الحساب", value=discord.utils.format_dt(member.created_at, "D"), inline=True)
    embed.add_field(name="أعلى رتبة", value=member.top_role.mention, inline=True)
    await interaction.response.send_message(embed=embed)


@tree.command(name="avatar", description="عرض الصورة الشخصية لمستخدم")
@app_commands.describe(user="المستخدم المراد عرض صورته")
async def avatar(interaction: discord.Interaction, user: Optional[discord.User] = None):
    user = user or interaction.user
    embed = discord.Embed(title=f"صورة {user.display_name}", color=discord.Color.blurple())
    embed.set_image(url=user.display_avatar.url)
    await interaction.response.send_message(embed=embed)


# ===== ترفيه وأدوات =====
@tree.command(name="say", description="يرسل البوت النص الذي تكتبه")
@app_commands.describe(text="النص المراد إرساله")
async def say(interaction: discord.Interaction, text: app_commands.Range[str, 1, 1900]):
    await interaction.response.send_message(text, allowed_mentions=discord.AllowedMentions.none())


@tree.command(name="coinflip", description="رمي عملة")
@app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
async def coinflip(interaction: discord.Interaction):
    result = random.choice(["صورة 🪙", "كتابة 🪙"])
    await interaction.response.send_message(f"النتيجة: **{result}**")


@tree.command(name="roll", description="رمي نرد")
@app_commands.describe(sides="عدد أوجه النرد (2 - 1000)")
@app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
async def roll(interaction: discord.Interaction, sides: app_commands.Range[int, 2, 1000] = 6):
    await interaction.response.send_message(
        f"🎲 رميت نردًا من {sides} أوجه: **{random.randint(1, sides)}**"
    )


@tree.command(name="8ball", description="اسأل الكرة السحرية")
@app_commands.describe(question="سؤالك")
@app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
async def eight_ball(interaction: discord.Interaction, question: str):
    await interaction.response.send_message(
        f"🎱 **السؤال:** {question}\n**الجواب:** {random.choice(EIGHT_BALL_ANSWERS)}"
    )


@tree.command(name="choose", description="اختيار عشوائي بين عدة خيارات")
@app_commands.describe(options="الخيارات مفصولة بـ | مثال: pizza | burger | sushi")
@app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
async def choose(interaction: discord.Interaction, options: str):
    items = [o.strip() for o in options.split("|") if o.strip()]
    if len(items) < 2:
        await interaction.response.send_message("⚠️ أدخل خيارين على الأقل مفصولين بـ |.", ephemeral=True)
        return
    await interaction.response.send_message(f"🤖 اخترت لك: **{random.choice(items)}**")


@tree.command(name="poll", description="إنشاء تصويت بالتفاعلات")
@app_commands.describe(
    question="السؤال",
    option1="الخيار الأول",
    option2="الخيار الثاني",
    option3="الخيار الثالث (اختياري)",
    option4="الخيار الرابع (اختياري)",
    option5="الخيار الخامس (اختياري)",
)
async def poll(
    interaction: discord.Interaction,
    question: str,
    option1: str,
    option2: str,
    option3: Optional[str] = None,
    option4: Optional[str] = None,
    option5: Optional[str] = None,
):
    options = [o for o in (option1, option2, option3, option4, option5) if o]
    embed = discord.Embed(title=f"📊 {question}", color=discord.Color.orange())
    embed.description = "\n".join(f"{NUMBER_EMOJIS[i]} {opt}" for i, opt in enumerate(options))
    await interaction.response.send_message(embed=embed)
    msg = await interaction.original_response()
    for i in range(len(options)):
        await msg.add_reaction(NUMBER_EMOJIS[i])


@tree.command(name="remind", description="تذكير بعد مدة")
@app_commands.describe(seconds="المدة بالثواني (1 - 86400)", text="نص التذكير")
async def remind(
    interaction: discord.Interaction,
    seconds: app_commands.Range[int, 1, 86400],
    text: str,
):
    await interaction.response.send_message(f"⏰ سأذكّرك بعد {seconds} ثانية.", ephemeral=True)

    async def _reminder():
        await asyncio.sleep(seconds)
        try:
            await interaction.channel.send(f"{interaction.user.mention} ⏰ تذكير: {text}")
        except discord.HTTPException:
            log.warning("فشل إرسال التذكير إلى %s", interaction.user)

    task = asyncio.create_task(_reminder())
    reminder_tasks.add(task)
    task.add_done_callback(reminder_tasks.discard)


# ===== إدارة =====
@tree.command(name="clear", description="حذف عدد من الرسائل في القناة")
@app_commands.describe(amount="عدد الرسائل (1 - 100)")
@app_commands.guild_only()
@app_commands.default_permissions(manage_messages=True)
@app_commands.checks.has_permissions(manage_messages=True)
@app_commands.checks.bot_has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100]):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"🧹 تم حذف {len(deleted)} رسالة.", ephemeral=True)


def _is_outranked(interaction: discord.Interaction, member: discord.Member) -> bool:
    # يمنع تنفيذ الإجراء على عضو رتبته أعلى أو مساوية (إلا لمالك السيرفر)
    return (
        member.top_role >= interaction.user.top_role
        and interaction.guild.owner_id != interaction.user.id
    )


@tree.command(name="kick", description="طرد عضو من السيرفر")
@app_commands.describe(member="العضو", reason="السبب (اختياري)")
@app_commands.guild_only()
@app_commands.default_permissions(kick_members=True)
@app_commands.checks.has_permissions(kick_members=True)
@app_commands.checks.bot_has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = None):
    reason = reason or "بدون سبب"
    if _is_outranked(interaction, member):
        await interaction.response.send_message("⛔ لا يمكنك طرد عضو رتبته أعلى منك أو مساوية لها.", ephemeral=True)
        return
    await member.kick(reason=f"{interaction.user}: {reason}")
    await interaction.response.send_message(f"👢 تم طرد {member} — السبب: {reason}")


@tree.command(name="ban", description="حظر عضو من السيرفر")
@app_commands.describe(member="العضو", reason="السبب (اختياري)")
@app_commands.guild_only()
@app_commands.default_permissions(ban_members=True)
@app_commands.checks.has_permissions(ban_members=True)
@app_commands.checks.bot_has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = None):
    reason = reason or "بدون سبب"
    if _is_outranked(interaction, member):
        await interaction.response.send_message("⛔ لا يمكنك حظر عضو رتبته أعلى منك أو مساوية لها.", ephemeral=True)
        return
    await member.ban(reason=f"{interaction.user}: {reason}", delete_message_seconds=0)
    await interaction.response.send_message(f"🔨 تم حظر {member} — السبب: {reason}")


@tree.command(name="timeout", description="إسكات عضو مؤقتًا")
@app_commands.describe(member="العضو", minutes="المدة بالدقائق (1 - 40320)", reason="السبب (اختياري)")
@app_commands.guild_only()
@app_commands.default_permissions(moderate_members=True)
@app_commands.checks.has_permissions(moderate_members=True)
@app_commands.checks.bot_has_permissions(moderate_members=True)
async def timeout(
    interaction: discord.Interaction,
    member: discord.Member,
    minutes: app_commands.Range[int, 1, 40320],
    reason: Optional[str] = None,
):
    reason = reason or "بدون سبب"
    if _is_outranked(interaction, member):
        await interaction.response.send_message("⛔ لا يمكنك إسكات عضو رتبته أعلى منك أو مساوية لها.", ephemeral=True)
        return
    until = discord.utils.utcnow() + datetime.timedelta(minutes=minutes)
    await member.timeout(until, reason=f"{interaction.user}: {reason}")
    await interaction.response.send_message(f"🔇 تم إسكات {member} لمدة {minutes} دقيقة — السبب: {reason}")


@tree.error
async def on_app_command_error_handler(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        msg = "⛔ ليست لديك صلاحية لاستخدام هذا الأمر."
    elif isinstance(error, app_commands.BotMissingPermissions):
        msg = "⛔ البوت يحتاج صلاحيات إضافية لتنفيذ هذا الأمر."
    elif isinstance(error, app_commands.CommandOnCooldown):
        msg = f"⏳ انتظر {error.retry_after:.1f} ثانية قبل استخدام الأمر مرة أخرى."
    elif isinstance(error, app_commands.NoPrivateMessage):
        msg = "⚠️ هذا الأمر يعمل داخل السيرفرات فقط."
    elif isinstance(error, app_commands.CheckFailure):
        msg = "⛔ لا تملك صلاحية لهذا الأمر."
    else:
        log.error("Unhandled app command error in %s", interaction.command, exc_info=error)
        msg = "❌ حدث خطأ غير متوقع أثناء تنفيذ الأمر."
    if interaction.response.is_done():
        await interaction.followup.send(msg, ephemeral=True)
    else:
        await interaction.response.send_message(msg, ephemeral=True)


if __name__ == "__main__":
    if not TOKEN:
        print("خطأ: يرجى وضع التوكن (DISCORD_TOKEN).")
        sys.exit(1)
    bot.run(TOKEN)
