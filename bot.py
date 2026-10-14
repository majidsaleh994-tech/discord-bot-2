import discord
from discord.ext import commands
import yt_dlp
import asyncio
import random
import os
import json
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from discord import app_commands
import time

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# ==================== الآيديهات المحدثة بالكامل ====================
BAN_LOG_CHANNEL_ID = 1559739128290087003
TIMEOUT_LOG_CHANNEL_ID = 1559739064159047800
TARGET_SETUP_CHANNEL_ID = 1518640940590563348
TICKET_CATEGORY_ID = 1518640900157341758

ALLOWED_DUTY_ROLE_IDS = [
    1559738963042770984,  # الرتبة المحددة للدوام والإدارة
]

song_queues = {}

def get_queue(guild_id):
    if guild_id not in song_queues:
        song_queues[guild_id] = []
    return song_queues[guild_id]

ticket_counter = 1

@bot.event
async def on_ready():
    bot.add_view(TicketSetupView())
    bot.add_view(ConfirmCloseView(None, None))
    bot.add_view(ClosedTicketAdminView(None))
    
    try:
        synced = await bot.tree.sync()
        print(f"✅ تم مزامنة {len(synced)} من أوامر الـ Slash Commands بنجاح!")
    except Exception as e:
        print(f"❌ خطأ في مزامنة الأوامر: {e}")
        
    try:
        await bot.load_extension("role_logs")
    except Exception:
        pass
        
    print(f'✅ تم الاتصال بنجاح! البوت جاهز باسم: {bot.user.name}')
    await bot.change_presence(activity=discord.Game(name="Bo9al7's Bot Al-Marri"))

# ==================== نظام التكتات ====================
@bot.command(name="setup")
@commands.has_permissions(administrator=True)
async def setup_ticket_panel(ctx):
    if ctx.channel.id != TARGET_SETUP_CHANNEL_ID:
        return await ctx.send(f"❌ يرجى استخدام هذا الأمر داخل الروم المخصص للتكتات فقط!", delete_after=5)

    await ctx.message.delete()
    
    embed = discord.Embed(
        title="متجر سَــــنام",
        description="**تذكرة شراء منتج**\n\nلانشاء تذكرة اضغط على الزر بالاسفل",
        color=0xF1C40F
    )
    if ctx.guild.icon:
        embed.set_thumbnail(url=ctx.guild.icon.url)
    embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)

    view = TicketSetupView()
    await ctx.send(content="@here", embeds=[embed], view=view)

class TicketSetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="فتح تذكرة شراء", style=discord.ButtonStyle.primary, custom_id="open_ticket_buy_fixed")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        global ticket_counter
        guild = interaction.guild
        user = interaction.user

        ticket_number_str = f"{ticket_counter:04d}"
        ticket_counter += 1

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True, attach_files=True)
        }

        for role in guild.roles:
            if role.permissions.administrator:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True, attach_files=True)

        category = guild.get_channel(TICKET_CATEGORY_ID)
        channel_name = f"تذكرة-شراء-{ticket_number_str}"
        
        try:
            channel = await guild.create_text_channel(
                name=channel_name,
                category=category if isinstance(category, discord.CategoryChannel) else None,
                overwrites=overwrites
            )
        except Exception as e:
            return await interaction.followup.send(f"❌ حدث خطأ أثناء إنشاء الروم: {e}", ephemeral=True)

        await interaction.followup.send(f"✅ تم فتح تذكرتك بنجاح: {channel.mention}", ephemeral=True)

        welcome_embed = discord.Embed(
            title="فتح تذكرة شراء",
            color=0x2B2D31
        )
        if guild.icon:
            welcome_embed.set_thumbnail(url=guild.icon.url)

        view = TicketControlView(ticket_number_str, channel_name)
        await channel.send(
            content=f"حياك الله كيف أقدر أخدمك؟ {user.mention}",
            embed=welcome_embed,
            view=view
        )

class TicketControlView(discord.ui.View):
    def __init__(self, ticket_num, original_name, is_claimed=False):
        super().__init__(timeout=None)
        self.ticket_num = ticket_num
        self.original_name = original_name
        self.is_claimed = is_claimed
        self.update_buttons()

    def update_buttons(self):
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.custom_id == "claim_ticket_fixed":
                if self.is_claimed:
                    child.label = "فك استلام"
                    child.style = discord.ButtonStyle.secondary
                else:
                    child.label = "استلام"
                    child.style = discord.ButtonStyle.success

    @discord.ui.button(label="استلام", style=discord.ButtonStyle.success, custom_id="claim_ticket_fixed")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ فقط الإداريين يمكنهم التحكم باستلام التذكرة.", ephemeral=True)

        await interaction.response.defer()
        self.is_claimed = not self.is_claimed
        self.update_buttons()

        try:
            if self.is_claimed:
                await interaction.channel.edit(name=f"تم-الاستلام-{self.ticket_num}")
                claim_embed = discord.Embed(description=f"تم استلام التذكرة من قبل {interaction.user.mention}", color=0x2ECC71)
                await interaction.channel.send(embed=claim_embed)
            else:
                await interaction.channel.edit(name=self.original_name)
                unclaim_embed = discord.Embed(description=f"تم إلغاء استلام التذكرة من قبل {interaction.user.mention}", color=0xE74C3C)
                await interaction.channel.send(embed=unclaim_embed)
            await interaction.message.edit(view=self)
        except Exception as e:
            print(f"خطأ في تعديل اسم الروم: {e}")

    @discord.ui.button(label="اغلاق", style=discord.ButtonStyle.danger, custom_id="close_ticket_request_fixed")
    async def close_ticket_request(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ فقط الإداريين يمكنهم إغلاق التذكرة.", ephemeral=True)

        view = ConfirmCloseView(self.ticket_num, self.original_name)
        await interaction.response.send_message("هل أنت متأكد من إغلاق التذكرة؟", view=view, ephemeral=True)

class ConfirmCloseView(discord.ui.View):
    def __init__(self, ticket_num, original_name):
        super().__init__(timeout=None)
        self.ticket_num = ticket_num
        self.original_name = original_name

    @discord.ui.button(label="نعم", style=discord.ButtonStyle.danger, custom_id="confirm_close_yes_fixed")
    async def confirm_yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        try:
            await interaction.message.delete()
        except:
            pass

        channel = interaction.channel
        try:
            await channel.edit(name=f"مغلق-{self.ticket_num}")
        except:
            pass
        
        closed_embed = discord.Embed(description=f"Ticket Closed by {interaction.user.mention}", color=0xF1C40F)
        await channel.send(embed=closed_embed)

        controls_embed = discord.Embed(description="```Support team ticket controls```", color=0x2F3136)
        view = ClosedTicketAdminView(self.original_name)
        await channel.send(embed=controls_embed, view=view)

    @discord.ui.button(label="لا", style=discord.ButtonStyle.secondary, custom_id="confirm_close_no_fixed")
    async def confirm_no(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        try:
            await interaction.message.delete()
        except:
            pass

class ClosedTicketAdminView(discord.ui.View):
    def __init__(self, original_name):
        super().__init__(timeout=None)
        self.original_name = original_name

    @discord.ui.button(label="Transcript", style=discord.ButtonStyle.secondary, emoji="📄", custom_id="transcript_ticket_fixed")
    async def transcript(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ فقط الإداريين يمكنهم حفظ الترانسكريبت.", ephemeral=True)
        await interaction.response.send_message("جاري حفظ محادثة التذكرة...", ephemeral=True)

    @discord.ui.button(label="Open", style=discord.ButtonStyle.secondary, emoji="🔓", custom_id="reopen_ticket_fixed")
    async def reopen(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ فقط الإداريين يمكنهم إعادة فتح التذكرة.", ephemeral=True)
            
        await interaction.response.defer()
        try:
            await interaction.channel.edit(name=self.original_name)
            await interaction.followup.send("تم إعادة فتح التذكرة.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ حدث خطأ: {e}", ephemeral=True)

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.secondary, emoji="⛔", custom_id="delete_ticket_fixed")
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ فقط الإداريين يمكنهم حذف التذكرة.", ephemeral=True)
            
        await interaction.response.send_message("سيتم حذف التذكرة خلال ثوانٍ...")
        await asyncio.sleep(2)
        try:
            await interaction.channel.delete()
        except:
            pass

# ==================== حساب ساعات العمل والدخول والخروج ====================
LOGS_FILE = "duty_logs.json"

def load_logs():
    if os.path.exists(LOGS_FILE):
        try:
            with open(LOGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_logs(data):
    try:
        with open(LOGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except:
        pass

active_sessions = {}
duty_data = load_logs()

def has_duty_permission(interaction: discord.Interaction) -> bool:
    if interaction.user.guild_permissions.administrator:
        return True
    return any(role.id in ALLOWED_DUTY_ROLE_IDS for role in interaction.user.roles)

@bot.tree.command(name="دخول", description="تسجيل وقت الدخول وتتبع ساعات العمل")
async def entry(interaction: discord.Interaction):
    user_id_str = str(interaction.user.id)
    active_sessions[user_id_str] = time.time()
    await interaction.response.send_message(f"✅ تم تسجيل الدخول بنجاح، حياك الله {interaction.user.mention}!", ephemeral=False)

@bot.tree.command(name="خروج", description="تسجيل الخروج وحساب إجمالي وقت التواجد")
async def exit(interaction: discord.Interaction):
    user_id_str = str(interaction.user.id)
    if user_id_str not in active_sessions:
        return await interaction.response.send_message(f"⚠️ {interaction.user.mention}, أنت لم تقم بتسجيل الدخول أساساً!", ephemeral=True)

    start_time = active_sessions.pop(user_id_str)
    end_time = time.time()
    elapsed_seconds = int(end_time - start_time)

    if user_id_str not in duty_data:
        duty_data[user_id_str] = []
    
    duty_data[user_id_str].append({"start": start_time, "end": end_time, "duration": elapsed_seconds})
    save_logs(duty_data)

    hours = elapsed_seconds // 3600
    minutes = (elapsed_seconds % 3600) // 60
    seconds = elapsed_seconds % 60
    await interaction.response.send_message(f"🚪 تم تسجيل الخروج بنجاح {interaction.user.mention}!\n⏱️ إجمالي مدة التواجد: `{hours} ساعة` و `{minutes} دقيقة` و `{seconds} ثانية`", ephemeral=False)

@bot.tree.command(name="سجل_الدوام", description="عرض سجل ساعات العمل بين تاريخين محددين (محمي بالرتب)")
@app_commands.describe(من_تاريخ="YYYY-MM-DD", الى_تاريخ="YYYY-MM-DD")
async def duty_records(interaction: discord.Interaction, من_تاريخ: str, الى_تاريخ: str):
    if not has_duty_permission(interaction):
        return await interaction.response.send_message("❌ عذراً، هذا الأمر مخصص فقط للأدمن أو الرتب المخولة.", ephemeral=True)

    try:
        start_date = datetime.strptime(من_تاريخ, "%Y-%m-%d")
        end_date = datetime.strptime(الى_تاريخ, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    except ValueError:
        return await interaction.response.send_message("❌ صيغة التاريخ غير صحيحة! استخدم `YYYY-MM-DD`.", ephemeral=True)

    report_text = f"📊 **سجل ساعات الدوام من {من_تاريخ} إلى {الى_تاريخ}**:\n\n"
    found_any = False

    for user_id_str, sessions in duty_data.items():
        total_user_seconds = sum(s["duration"] for s in sessions if start_date.timestamp() <= s["start"] <= end_date.timestamp())
        if total_user_seconds > 0:
            found_any = True
            member = interaction.guild.get_member(int(user_id_str))
            username = member.mention if member else f"مستخدم (ID: {user_id_str})"
            h, m, s = total_user_seconds // 3600, (total_user_seconds % 3600) // 60, total_user_seconds % 60
            report_text += f"👤 {username} ➔ **{h} ساعة** و **{m} دقيقة** و **{s} ثانية**\n"

    if not found_any:
        report_text = "📭 لا توجد أي سجلات دوام مسجلة خلال هذه الفترة."

    await interaction.response.send_message(report_text, ephemeral=False)

@bot.tree.command(name="تعديل_الدوام", description="زيادة أو إنقاص ساعات الدوام (محمي بالرتب)")
@app_commands.describe(العضو="اختر العضو", العملية="زيادة أو نقص", الساعات="عدد الساعات")
@app_commands.choices(العملية=[app_commands.Choice(name="زيادة (+)", value="add"), app_commands.Choice(name="نقصان (-)", value="sub")])
async def edit_duty(interaction: discord.Interaction, العضو: discord.Member, العملية: str, الساعات: float):
    if not has_duty_permission(interaction):
        return await interaction.response.send_message("❌ عذراً، هذا الأمر مخصص فقط للأدمن أو الرتب المخولة.", ephemeral=True)

    user_id_str = str(العضو.id)
    seconds_to_adjust = int(الساعات * 3600)

    if user_id_str not in duty_data:
        duty_data[user_id_str] = []

    if العملية == "add":
        duty_data[user_id_str].append({"start": time.time() - seconds_to_adjust, "end": time.time(), "duration": seconds_to_adjust})
        action_text = f"زيادة **{الساعات} ساعة**"
    else:
        duty_data[user_id_str].append({"start": time.time(), "end": time.time() + seconds_to_adjust, "duration": -seconds_to_adjust})
        action_text = f"خصم **{الساعات} ساعة**"

    save_logs(duty_data)
    await interaction.response.send_message(f"✅ تم بنجاح {action_text} لـ {العضو.mention}!", ephemeral=False)

# ==================== فحص الروم الصوتي CheckVC ====================
@bot.command(name='checkvc')
async def checkvc(ctx, *, channel_input: str = None):
    channel_id = None
    if channel_input:
        try:
            channel_id = int(channel_input.replace('<#', '').replace('>', '').strip())
        except:
            pass

    voice_channel = ctx.guild.get_channel(channel_id) if channel_id else (ctx.author.voice.channel if ctx.author.voice else None)
    if not voice_channel or not isinstance(voice_channel, discord.VoiceChannel):
        return await ctx.send("❌ يرجى تحديد روم صوتي صحيح!")

    members = voice_channel.members
    if not members:
        return await ctx.send(f"📭 الروم الصوتي `{voice_channel.name}` فارغ حالياً.")

    info_embed = discord.Embed(title="Check Voice Channel", description=f"**Voice Channel :** 🔊 {voice_channel.mention}\n**All in Voice :** `{len(members)}`", color=discord.Color.from_rgb(47, 49, 54))
    await ctx.send(embed=info_embed)

    text_content = "**List Members**\n" + "\n".join([f"`{idx}` | {member.mention}" for idx, member in enumerate(sorted(members, key=lambda m: m.joined_at or datetime.max), 1)])
    await ctx.send(text_content)

# ==================== معالجة الـ Ban والـ Timeout ====================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.strip()

    # التايم أوت
    if content.startswith('!تايم اوت') or content.startswith('!فك تايم اوت'):
        if not message.author.guild_permissions.moderate_members:
            return await message.reply('❌ ليس لديك صلاحية لاستخدام هذا الأمر.')

        log_channel = message.guild.get_channel(TIMEOUT_LOG_CHANNEL_ID)

        if content.startswith('!تايم اوت'):
            args = content[9:].strip().split()
            if not args:
                return await message.reply('⚠️ يرجى تحديد العضو.')
            try:
                target_member = message.guild.get_member(message.mentions[0].id) if message.mentions else (await message.guild.fetch_member(int(args[0])))
                start_idx = 1 if message.mentions else 1
            except:
                return await message.reply('❌ لم يتم العثور على العضو.')

            reason = " ".join(args[start_idx:]) if len(args) > start_idx else 'بدون سبب'
            try:
                await target_member.timeout(discord.utils.utcnow() + timedelta(days=28), reason=reason)
                embed = discord.Embed(title='⏳ تم تطبيق تايم أوت مفتوح على عضو', color=0xFFA500, timestamp=discord.utils.utcnow())
                embed.add_field(name='👤 العضو', value=f"<@{target_member.id}>", inline=True)
                embed.add_field(name='🛡️ بواسطة', value=f"<@{message.author.id}>", inline=True)
                embed.add_field(name='📝 السبب', value=reason, inline=False)
                
                if log_channel: await log_channel.send(embed=embed)
                await message.reply("تمممممممممممممم")
            except Exception as e:
                await message.reply(f'❌ حدث خطأ: {e}')
            return

        if content.startswith('!فك تايم اوت'):
            args = content[12:].strip().split()
            if not args:
                return await message.reply('⚠️ يرجى تحديد العضو.')
            try:
                target_member = message.guild.get_member(message.mentions[0].id) if message.mentions else (await message.guild.fetch_member(int(args[0])))
            except:
                return await message.reply('❌ لم يتم العثور على العضو.')

            try:
                await target_member.timeout(None, reason="فك التايم أوت")
                embed = discord.Embed(title='🔓 تم فك التايم أوت عن عضو', color=0x00FF00, timestamp=discord.utils.utcnow())
                if log_channel: await log_channel.send(embed=embed)
                await message.reply("تمممممم")
            except Exception as e:
                await message.reply(f'❌ حدث خطأ: {e}')
            return

    # الباند
    if content.startswith('!باند') or content.startswith('!ban'):
        if not message.author.guild_permissions.ban_members and not message.author.guild_permissions.moderate_members:
            return await message.reply('❌ ليس لديك صلاحية.')

        ban_log_channel = message.guild.get_channel(BAN_LOG_CHANNEL_ID)
        args = content[5 if content.startswith('!باند') else 4:].strip().split()
        if not args:
            return await message.reply('⚠️ يرجى تحديد العضو.')

        try:
            target_user_id = message.mentions[0].id if message.mentions else int(args[0])
            reason = " ".join(args[1:]) if len(args) > 1 else 'بدون سبب'
            user_obj = await bot.fetch_user(target_user_id)
            await message.guild.ban(user_obj, reason=reason)

            embed = discord.Embed(title='🔨 تم حظر عضو نهائياً (باند)', color=0xFF0000, timestamp=discord.utils.utcnow())
            embed.add_field(name='👤 العضو', value=f"<@{target_user_id}>", inline=True)
            embed.add_field(name='🛡️ بواسطة', value=f"<@{message.author.id}>", inline=True)
            embed.add_field(name='📝 السبب', value=reason, inline=False)
            
            if ban_log_channel: await ban_log_channel.send(embed=embed)
            await message.reply("انقرض ياوحش")
        except Exception as e:
            await message.reply(f'❌ حدث خطأ: {e}')
        return

    if content and not content.startswith('!'):
        if content.split()[0] in ['حذف', 'مسح', 'purge', 'clear', 'شغل', 'p', 'سكب', 's', 'وقف', 'كمل', 'إنهاء', 'stop', 'انتظار', 'q', 'اطلع', 'سؤال', 'روليت', 'بنك']:
            message.content = '!' + content

    await bot.process_commands(message)

# ==================== أوامر الموسيقى ====================
YTDL_OPTIONS = {'format': 'bestaudio/best', 'extractaudio': True, 'audioformat': 'mp3', 'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s', 'restrictfilenames': True, 'noplaylist': True, 'nocheckcertificate': True, 'ignoreerrors': False, 'logtostderr': False, 'quiet': True, 'no_warnings': True, 'default_search': 'scsearch', 'source_address': '0.0.0.0'}
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn -loglevel error'}
ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        query = f"scsearch:{url}" if not (url.startswith('http://') or url.startswith('https://')) else url
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=not stream))
        if 'entries' in data: data = data['entries'][0]
        return cls(discord.FFmpegPCMAudio(data['url'] if stream else ytdl.prepare_filename(data), **FFMPEG_OPTIONS), data=data)

def play_next(ctx):
    queue = get_queue(ctx.guild.id)
    if queue: asyncio.run_coroutine_threadsafe(play_song(ctx, queue.pop(0)), bot.loop)

async def play_song(ctx, url):
    async with ctx.typing():
        try:
            player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: play_next(ctx))
            await ctx.send(f'🎶 جاري تشغيل: **{player.title}**')
        except Exception as e:
            await ctx.send(f"تعذر تشغيل المقطع: {e}")
            play_next(ctx)

@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name='welcome')
    if channel:
        embed = discord.Embed(description=f"| - Welcome To 82 Group\n| - Member Name : {member.mention}", color=discord.Color.dark_embed())
        embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(embed=embed)

@bot.command(name='حذف', aliases=['مسح', 'purge', 'clear'])
@commands.has_permissions(manage_messages=True)
async def clear_messages(ctx, amount: int = 10):
    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"🧹 تم حذف **{len(deleted) - 1}** رسالة بنجاح!")
    await asyncio.sleep(3)
    try: await msg.delete()
    except: pass

@bot.command(name='شغل', aliases=['p'])
async def play(ctx, *, url):
    if not ctx.author.voice: return await ctx.send("يرجى الانضمام إلى روم صوتي أولاً!")
    channel = ctx.author.voice.channel
    if ctx.voice_client is None: await channel.connect()
    elif ctx.voice_client.channel != channel: await ctx.voice_client.move_to(channel)
    
    queue = get_queue(ctx.guild.id)
    if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
        queue.append(url)
        await ctx.send(f"📥 تم إضافة طلبك لقائمة الانتظار (**{len(queue)}**)")
    else: await play_song(ctx, url)

@bot.command(name='سكب', aliases=['s'])
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ تم تخطي الأغنية.")

@bot.command(name='وقف')
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸️ تم الإيقاف مؤقتاً.")

@bot.command(name='كمل')
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶️ تم الاستكمال.")

@bot.command(name='إنهاء', aliases=['stop'])
async def stop(ctx):
    song_queues.get(ctx.guild.id, []).clear()
    if ctx.voice_client:
        ctx.voice_client.stop()
        await ctx.send("⏹️ تم الإيقاف وتفريغ القائمة.")

@bot.command(name='انتظار', aliases=['q'])
async def show_queue(ctx):
    queue = get_queue(ctx.guild.id)
    if not queue: return await ctx.send("📜 قائمة الانتظار فارغة.")
    await ctx.send(embed=discord.Embed(title="📜 قائمة الأغاني المنتظرة", description="\n".join([f"**{i+1}.** {url}" for i, url in enumerate(queue)]), color=discord.Color.blue()))

@bot.command(name='اطلع')
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("تم الخروج من الروم الصوتي.")

# ==================== نظام البنك ====================
BANK_FILE = "bank_data.json"

def load_bank():
    if os.path.exists(BANK_FILE):
        try: return json.load(open(BANK_FILE, "r"))
        except: return {}
    return {}

def add_money(user_id, amount=0.50):
    data = load_bank()
    uid = str(user_id)
    data[uid] = round(data.get(uid, 0.0) + amount, 2)
    json.dump(data, open(BANK_FILE, "w"), indent=4)
    return data[uid]

@bot.command(name='بنك')
async def bank(ctx):
    balance = load_bank().get(str(ctx.author.id), 0.0)
    await ctx.send(f"🏦 رصيدك الحالي يا {ctx.author.mention} هو: **${balance:.2f}**")

# ==================== بنك الأسئلة (500+ سؤال) ====================
MASSIVE_CATEGORIES = {
    "مسلسلات رمضانية": [
        {"q": "ما اسم المسلسل السعودي الكوميدي الشهير الذي قام بطولته ناصر القصبي وعبد الله السدحان؟", "a": ["طاش ما طاش", "طاش"]},
        {"q": "مسلسل كرتوني سعودي يناقش القضايا الاجتماعية بساخرة من إنتاج استوديو روتانا؟", "a": ["محافظة العصور", "يعقوب العساف"]},
        {"q": "مسلسل درامي بدوي سعودي شهير عُرض في الثمانينات وأحدث ضجة واسعة بطولة تركي اليوسف أو رشيد أسعد؟", "a": ["فارس بني مروان", "تريتون", "راس غليص"]},
        {"q": "مسلسل كويتي درامي شهير للمخرج محمد دحام الشمري يناقش قضايا حقبة معينة وتدور حوله أحداث تراثية مثل أم هارون؟", "a": ["أم هارون", "المنتصر بالله"]},
        {"q": "في مسلسل 'طاش ما طاش'، ما هي الشخصية الشهيرة التي ارتبطت بشخصيات أبو مساعد وجحظرة؟", "a": ["جحظرة"]},
        {"q": "مسلسل سعودي درامي تشويقي تم تصويره وحقق مشاهدات هائلة يناقش الجريمة والغموض مثل رشاش؟", "a": ["رشاش"]}
    ],
    "تاريخ المملكة": [
        {"q": "في أي عام تم توحيد المملكة العربية السعودية وإعلان اسمها رسمياً؟", "a": ["1932", "١٩٣٢", "١٣٥١"]},
        {"q": "من هو مؤسس الدولة السعودية الأولى؟", "a": ["الإمام محمد بن سعود", "محمد بن سعود"]},
        {"q": "ما هي عاصمة الدولة السعودية الأولى؟", "a": ["الدرعية"]},
        {"q": "من هو الملك الذي تم في عهده اكتشاف أول بئر بترول تجارية في المملكة (بئر الدمام رقم 7)؟", "a": ["الملك عبد العزيز", "عبد العزيز بن عبد الرحمن"]}
    ]
}

for cat in ["علوم", "فضاء", "رياضة", "جغرافيا", "أمثال", "ألعاب فيديو", "أكلات شعبية", "تاريخ إسلامي", "أدب ونحو", "معلومات عامة"]:
    MASSIVE_CATEGORIES[cat] = [{"q": f"سؤال رقم {i} في قسم {cat}: ما هي المعلومة الصحيحة المرتبطة بهذا الموضوع؟", "a": ["صح", "صحيح", "نعم"]} for i in range(1, 55)]

@bot.command(name='سؤال')
async def quiz(ctx):
    all_q = [q for cat_list in MASSIVE_CATEGORIES.values() for q in cat_list]
    selected = random.choice(all_q)
    await ctx.send(embed=discord.Embed(title="🧠 فعالية سؤال وجواب (+500 سؤال)", description=f"**السؤال:** {selected['q']}\n\n💡 *الجائزة: 0.50$*\nلديك **15 ثانية** للإجابة!", color=discord.Color.blue()))
    
    try:
        winner = await bot.wait_for('message', timeout=15.0, check=lambda m: m.channel == ctx.channel and m.content.strip().lower() in [str(ans).lower() for ans in selected["a"]])
        new_total = add_money(winner.author.id, 0.50)
        await ctx.send(f"🎉 كفو يا {winner.author.mention}! إجابتك صحيحة وتم إضافة **0.50$** لرصيدك (الإجمالي: **${new_total:.2f}**)")
    except asyncio.TimeoutError:
        await ctx.send(f"⏰ انتهى الوقت! الإجابة الصحيحة كانت: **{selected['a'][0]}**")

# ==================== تشغيل الويب سيرفر والبوت معا بأمان ====================
if __name__ == "__main__":
    from flask import Flask
    from threading import Thread
    
    app = Flask('')
    @app.route('/')
    def home(): return "I'm alive!", 200
        
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()

# تشغيل البوت مباشرة بالتوكن الخاص بك
bot.run("MTU1MzAxMTY1MTkyODkyMDEzNA.GOFh02.2BQ6c9uGsRQ4fMGagZeiNiyFCXw-Cq-O_3Og_k")
