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

BAN_LOG_CHANNEL_ID = 1557667087005122570
TIMEOUT_LOG_CHANNEL_ID = 1557647008699777074

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

# ==================== نظام التذاكر (Tickets) ====================
@bot.command(name="setup")
@commands.has_permissions(administrator=True)
async def setup_ticket_panel(ctx):
    target_channel_id = 1558665184921395292
    if ctx.channel.id != target_channel_id:
        return await ctx.send(f"❌ يرجى استخدام هذا الأمر داخل الروم المخصص فقط!", delete_after=5)

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

        category_id = 1558665231394283540
        category = guild.get_channel(category_id)

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
            return await interaction.response.send_message("❌ فقط الإداريين (Administrator) يمكنهم التحكم باستلام التذكرة.", ephemeral=True)

        await interaction.response.defer()

        self.is_claimed = not self.is_claimed
        self.update_buttons()

        try:
            if self.is_claimed:
                await interaction.channel.edit(name=f"تم-الاستلام-{self.ticket_num}")
                claim_embed = discord.Embed(
                    description=f"تم استلام التذكرة من قبل {interaction.user.mention}",
                    color=0x2ECC71
                )
                await interaction.channel.send(embed=claim_embed)
            else:
                await interaction.channel.edit(name=self.original_name)
                unclaim_embed = discord.Embed(
                    description=f"تم إلغاء استلام التذكرة من قبل {interaction.user.mention}",
                    color=0xE74C3C
                )
                await interaction.channel.send(embed=unclaim_embed)
            
            await interaction.message.edit(view=self)
        except Exception as e:
            print(f"خطأ في تعديل اسم أو حالة الروم: {e}")

    @discord.ui.button(label="اغلاق", style=discord.ButtonStyle.danger, custom_id="close_ticket_request_fixed")
    async def close_ticket_request(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ فقط الإداريين (Administrator) يمكنهم إغلاق التذكرة.", ephemeral=True)

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
        except Exception:
            pass

        channel = interaction.channel
        try:
            await channel.edit(name=f"مغلق-{self.ticket_num}")
        except Exception as e:
            print(f"خطأ في تعديل اسم الروم عند الإغلاق: {e}")
        
        closed_embed = discord.Embed(
            description=f"Ticket Closed by {interaction.user.mention}",
            color=0xF1C40F
        )
        await channel.send(embed=closed_embed)

        controls_embed = discord.Embed(
            description="```Support team ticket controls```",
            color=0x2F3136
        )
        
        view = ClosedTicketAdminView(self.original_name)
        await channel.send(embed=controls_embed, view=view)

    @discord.ui.button(label="لا", style=discord.ButtonStyle.secondary, custom_id="confirm_close_no_fixed")
    async def confirm_no(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        try:
            await interaction.message.delete()
        except Exception:
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
            return await interaction.response.send_message("❌ فقط الإداريين (Administrator) يمكنهم إعادة فتح التذكرة.", ephemeral=True)
            
        await interaction.response.defer()
        try:
            await interaction.channel.edit(name=self.original_name)
            await interaction.followup.send("تم إعادة فتح التذكرة وإرجاع اسمها السابق.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ حدث خطأ: {e}", ephemeral=True)

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.secondary, emoji="⛔", custom_id="delete_ticket_fixed")
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ فقط الإداريين (Administrator) يمكنهم حذف التذكرة.", ephemeral=True)
            
        await interaction.response.send_message("سيتم حذف التذكرة خلال ثوانٍ...")
        await asyncio.sleep(2)
        try:
            await interaction.channel.delete()
        except Exception as e:
            print(f"خطأ عند حذف القناة: {e}")

# ==================== 🕵️‍♂️ لعبة كود نيمز المتقدمة Codenames ====================

CODENAMES_WORDS_POOL = [
    "سيف", "أسد", "صقر", "شمس", "قمر", "نجم", "جبل", "بحر", "مطر", "نار",
    "برج", "حصان", "تاج", "قلعة", "خيمة", "رمح", "درع", "فرس", "ذهب", "فضة",
    "ليل", "سحاب", "رعد", "برق", "نخلة", "سفينة", "قصر", "صحراء", "غابة", "وادي",
    "صقر", "أسد", "فهد", "ذئب", "عقاب", "سهم", "خنجر", "بارود", "مدفع", "راحة"
]

class CodenamesHintModal(discord.ui.Modal, title="تقديم تلميح للفريق"):
    hint_word = discord.ui.TextInput(label="الكلمة الملمحة", placeholder="اكتب كلمة التلميح هنا...", required=True)
    count = discord.ui.TextInput(label="عدد الكلمات المرتبطة (1 إلى 10)", placeholder="أدخل رقماً من 1 إلى 10", min_length=1, max_length=2, required=True)

    def __init__(self, game_view):
        super().__init__()
        self.game_view = game_view

    async def on_submit(self, interaction: discord.Interaction):
        try:
            num = int(self.count.value.strip())
            if not (1 <= num <= 10):
                return await interaction.response.send_message("❌ يرجى إدخال عدد صحيح من 1 إلى 10!", ephemeral=True)
        except ValueError:
            return await interaction.response.send_message("❌ يرجى كتابة رقم صحيح فقط!", ephemeral=True)

        self.game_view.current_hint = self.hint_word.value.strip()
        self.game_view.hint_count = num
        self.game_view.guesses_made = 0

        color_name = "🔴 الفريق الأحمر" if self.game_view.current_turn == "red" else "🔵 الفريق الأزرق"
        embed = discord.Embed(
            title=f"💡 تلميح جديد من السباي ماستر ({color_name})",
            description=f"**التلميح:** `{self.game_view.current_hint}`\n**العدد المطلوب:** `{self.game_view.hint_count}`\n\nيمدكم تخمنون حتى **{num}** مرات، وبعدها يمديكم التوقف أو التخمين للمرة الـ **{num+1}** كحد إجباري!",
            color=0xE74C3C if self.game_view.current_turn == "red" else 0x3498DB
        )
        await interaction.response.send_message(embed=embed)
        await self.game_view.update_board_message(interaction)

class CodenamesWordButton(discord.ui.Button):
    def __init__(self, word, x, y, card_type):
        super().__init__(style=discord.ButtonStyle.secondary, label=word, row=x)
        self.word = word
        self.x = x
        self.y = y
        self.card_type = card_type  # 'red', 'blue', 'neutral', 'black'
        self.revealed = False

    async def callback(self, interaction: discord.Interaction):
        view: CodenamesGameView = self.view

        if view.current_turn == "red":
            if interaction.user in view.red_team and interaction.user != view.red_spymaster:
                pass
            else:
                return await interaction.response.send_message("❌ دور الفريق الأحمر فقط (اللاعبين)! أو أنك السباي ماستر.", ephemeral=True)
        else:
            if interaction.user in view.blue_team and interaction.user != view.blue_spymaster:
                pass
            else:
                return await interaction.response.send_message("❌ دور الفريق الأزرق فقط (اللاعبين)! أو أنك السباي ماستر.", ephemeral=True)

        if not view.current_hint:
            return await interaction.response.send_message("⚠️ انتظر حتى يقدم السباي ماستر التلميح أولاً!", ephemeral=True)

        if self.revealed:
            return await interaction.response.send_message("⚠️ هذه الكلمة تم كشفها مسبقاً!", ephemeral=True)

        self.revealed = True
        view.guesses_made += 1

        if self.card_type == "red":
            self.style = discord.ButtonStyle.danger
            self.label = f"🔴 {self.word}"
            view.red_score += 1
            got_correct = (view.current_turn == "red")
        elif self.card_type == "blue":
            self.style = discord.ButtonStyle.primary
            self.label = f"🔵 {self.word}"
            view.blue_score += 1
            got_correct = (view.current_turn == "blue")
        elif self.card_type == "neutral":
            self.style = discord.ButtonStyle.secondary
            self.label = f"⚪ {self.word}"
            got_correct = False
        elif self.card_type == "black":
            self.style = discord.ButtonStyle.dark
            self.label = f"💣 {self.word}"
            winner = "🔵 الفريق الأزرق" if view.current_turn == "red" else "🔴 الفريق الأحمر"
            for child in view.children:
                child.disabled = True
            embed = discord.Embed(title="💣 قنبلة الكرت الأسود!", description=f"اختار {interaction.user.mention} الكرت الأسود القاتل!\n\n🎉 **انتهت اللعبة وفاز {winner}!**", color=0x000000)
            await interaction.response.edit_message(view=view)
            return await interaction.followup.send(embed=embed)

        self.disabled = True

        if view.red_score >= 8:
            for child in view.children: child.disabled = True
            await interaction.response.edit_message(view=view)
            return await interaction.followup.send("🎉 **مبروك! كشف الفريق الأحمر (🔴) جميع كلماته وفاز باللعبة!**")
        elif view.blue_score >= 7:
            for child in view.children: child.disabled = True
            await interaction.response.edit_message(view=view)
            return await interaction.followup.send("🎉 **مبروك! كشف الفريق الأزرق (🔵) جميع كلماته وفاز باللعبة!**")

        max_allowed = view.hint_count + 1
        turn_ended = False

        if not got_correct:
            turn_ended = True
            reason = "اختيار كرت غير مطابق لفرقتك"
        elif view.guesses_made >= max_allowed:
            turn_ended = True
            reason = f"الوصول للحد الأقصى الإجباري للمحاولات ({max_allowed})"

        if turn_ended:
            view.current_turn = "blue" if view.current_turn == "red" else "red"
            view.current_hint = None
            view.hint_count = 0
            view.guesses_made = 0
            next_team = "🔵 الفريق الأزرق" if view.current_turn == "blue" else "🔴 الفريق الأحمر"
            await interaction.response.edit_message(view=view)
            await interaction.followup.send(f"🔄 **انتهى الدور ({reason})!** الانتقال إلى {next_team}.")
        else:
            await interaction.response.edit_message(view=view)

class CodenamesGameView(discord.ui.View):
    def __init__(self, red_team, blue_team, red_spymaster, blue_spymaster):
        super().__init__(timeout=600)
        self.red_team = red_team
        self.blue_team = blue_team
        self.red_spymaster = red_spymaster
        self.blue_spymaster = blue_spymaster
        self.current_turn = "red"
        self.red_score = 0
        self.blue_score = 0
        self.current_hint = None
        self.hint_count = 0
        self.guesses_made = 0
        self.board_message = None

        types = ['red']*8 + ['blue']*7 + ['neutral']*9 + ['black']*1
        random.shuffle(types)
        words = random.sample(CODENAMES_WORDS_POOL, 25)

        self.cards_info = []
        idx = 0
        for x in range(5):
            for y in range(5):
                card_type = types[idx]
                w = words[idx]
                self.cards_info.append({"word": w, "type": card_type, "x": x, "y": y})
                self.add_item(CodenamesWordButton(w, x, y, card_type))
                idx += 1

    async def update_board_message(self, interaction: discord.Interaction):
        curr_name = "🔴 الفريق الأحمر" if self.current_turn == "red" else "🔵 الفريق الأزرق"
        embed = discord.Embed(title="🕵️‍♂️ لعبة كود نيمز الجارية", color=0xE74C3C if self.current_turn == "red" else 0x3498DB)
        embed.add_field(name="الدور الحالي عند", value=curr_name, inline=True)
        embed.add_field(name="النقاط", value=f"🔴 أحمر: `{self.red_score}/8` | 🔵 أزرق: `{self.blue_score}/7`", inline=True)
        if self.current_hint:
            embed.add_field(name="التلميح الحالي", value=f"`{self.current_hint}` (المحاولات: {self.guesses_made}/{self.hint_count})", inline=False)
        else:
            embed.add_field(name="التلميح الحالي", value="في انتظار السباي ماستر بتقديم التلميح...", inline=False)
        
        await interaction.message.edit(embed=embed, view=self)

    @discord.ui.button(label="إرسال تلميح (لـ Spymaster)", style=discord.ButtonStyle.primary, row=4)
    async def give_hint(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_turn == "red" and interaction.user != self.red_spymaster:
            return await interaction.response.send_message("❌ فقط سباي ماستر الفريق الأحمر من يمكنه التلميح الآن!", ephemeral=True)
        elif self.current_turn == "blue" and interaction.user != self.blue_spymaster:
            return await interaction.response.send_message("❌ فقط سباي ماستر الفريق الأزرق من يمكنه التلميح الآن!", ephemeral=True)

        if self.current_hint:
            return await interaction.response.send_message("⚠️ تم تقديم تلميح لهذا الدور مسبقاً!", ephemeral=True)

        await interaction.response.send_modal(CodenamesHintModal(self))

    @discord.ui.button(label="إنهاء الدور اختياري ⏹️", style=discord.ButtonStyle.secondary, row=4)
    async def end_turn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_turn == "red" and interaction.user not in self.red_team:
            return await interaction.response.send_message("❌ فقط أعضاء الفريق الأحمر يمكنهم إنهاء الدور!", ephemeral=True)
        elif self.current_turn == "blue" and interaction.user not in self.blue_team:
            return await interaction.response.send_message("❌ فقط أعضاء الفريق الأزرق يمكنهم إنهاء الدور!", ephemeral=True)

        if self.guesses_made < self.hint_count:
            return await interaction.response.send_message(f"⚠️ يمديكم التوقف اختياري بعد الاستفادة من عدد التلميحات المطلوب أولاً ({self.guesses_made}/{self.hint_count})!", ephemeral=True)

        self.current_turn = "blue" if self.current_turn == "red" else "red"
        self.current_hint = None
        self.hint_count = 0
        self.guesses_made = 0

        next_team = "🔵 الفريق الأزرق" if self.current_turn == "blue" else "🔴 الفريق الأحمر"
        await interaction.response.send_message(f"⏹️ تم إنهاء الدور اختياري من قبل {interaction.user.mention}! انتقل الدور إلى {next_team}.")

class CodenamesLobbyView(discord.ui.View):
    def __init__(self, host):
        super().__init__(timeout=120)
        self.host = host
        self.red_team = []
        self.blue_team = []
        self.red_spymaster = None
        self.blue_spymaster = None

    @discord.ui.button(label="🔴 سباي ماستر أحمر", style=discord.ButtonStyle.danger)
    async def red_spy(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.red_spymaster:
            return await interaction.response.send_message("⚠️ يوجد سباي ماستر للفريق الأحمر بالفعل!", ephemeral=True)
        self.red_spymaster = interaction.user
        if interaction.user not in self.red_team: self.red_team.append(interaction.user)
        await interaction.response.send_message(f"👑 تم انضمام {interaction.user.mention} كـ **سباي ماستر للفريق الأحمر**!", ephemeral=False)

    @discord.ui.button(label="🔴 لاعب أحمر", style=discord.ButtonStyle.danger)
    async def red_player(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in self.red_team:
            self.red_team.append(interaction.user)
            await interaction.response.send_message(f"🔴 انضم {interaction.user.mention} للاعبي الفريق الأحمر!", ephemeral=False)
        else:
            await interaction.response.send_message("أنت مسجل بالفريق الأحمر مسبقاً!", ephemeral=True)

    @discord.ui.button(label="🔵 سباي ماستر أزرق", style=discord.ButtonStyle.primary)
    async def blue_spy(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.blue_spymaster:
            return await interaction.response.send_message("⚠️ يوجد سباي ماستر للفريق الأزرق بالفعل!", ephemeral=True)
        self.blue_spymaster = interaction.user
        if interaction.user not in self.blue_team: self.blue_team.append(interaction.user)
        await interaction.response.send_message(f"👑 تم انضمام {interaction.user.mention} كـ **سباي ماستر للفريق الأزرق**!", ephemeral=False)

    @discord.ui.button(label="🔵 لاعب أزرق", style=discord.ButtonStyle.primary)
    async def blue_player(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in self.blue_team:
            self.blue_team.append(interaction.user)
            await interaction.response.send_message(f"🔵 انضم {interaction.user.mention} للاعبي الفريق الأزرق!", ephemeral=False)
        else:
            await interaction.response.send_message("أنت مسجل بالفريق الأزرق مسبقاً!", ephemeral=True)

    @discord.ui.button(label="بدء اللعبة", style=discord.ButtonStyle.success, custom_id="start_game")
    async def start_game_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.host:
            return await interaction.response.send_message("❌ فقط منشئ اللعبة يمكنه بدء اللعبة!", ephemeral=True)
        if not self.red_spymaster or not self.blue_spymaster:
            return await interaction.response.send_message("⚠️ يجب تعيين سباي ماستر لكلا الفريقين أولاً!", ephemeral=True)

        await interaction.response.defer()

        game_view = CodenamesGameView(self.red_team, self.blue_team, self.red_spymaster, self.blue_spymaster)

        red_map = "🔴 **خريطة السباي ماستر للفريق الأحمر والكل:**\n"
        for item in game_view.cards_info:
            icon = "🔴" if item['type']=='red' else "🔵" if item['type']=='blue' else "⚪" if item['type']=='neutral' else "💣"
            red_map += f"• `{item['word']}` ➔ {icon}\n"

        try:
            await self.red_spymaster.send(red_map)
            await self.blue_spymaster.send(red_map)
        except Exception:
            pass

        embed = discord.Embed(
            title="🕵️‍♂️ بدأت لعبة كود نيمز الاحترافية!",
            description=f"**القائد المسير للعبة:** {self.host.mention}\n\n🔴 **الفريق الأحمر:**\n• **السباي ماستر:** {self.red_spymaster.mention}\n• **اللاعبون:** {', '.join([p.mention for p in self.red_team if p != self.red_spymaster])}\n\n🔵 **الفريق الأزرق:**\n• **السباي ماستر:** {self.blue_spymaster.mention}\n• **اللاعبون:** {', '.join([p.mention for p in self.blue_team if p != self.blue_spymaster])}\n\n💡 *تم إرسال خريطة الألوان للسباي ماسترز بالخاص!*",
            color=0x34495E
        )
        await interaction.followup.send(embed=embed, view=game_view)

@bot.command(name='كودنيمز', aliases=['codenames'])
async def start_codenames(ctx):
    view = CodenamesLobbyView(ctx.author)
    embed = discord.Embed(
        title="🕵️‍♂️ لعبة كود نيمز (Codenames)",
        description=f"فتح {ctx.author.mention} روم لعبة كود نيمز جديدة!\n\nاختر من الأزرار بالأسفل للانضمام إلى **الفريق الأحمر** أو **الفريق الأزرق**، أو استلام منصب **السباي ماستر**.",
        color=0x34495E
    )
    await ctx.send(embed=embed, view=view)

# ==================== بقية الألعاب (أونو / مافيا / بلوت / إكس أو) ====================

# 1. لعبة أونو UNO
class UnoLobbyView(discord.ui.View):
    def __init__(self, host):
        super().__init__(timeout=60)
        self.host = host
        self.players = [host]

    @discord.ui.button(label="انضمام للعبة 🃏", style=discord.ButtonStyle.success)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user in self.players:
            return await interaction.response.send_message("⚠️ أنت منضم بالفعل!", ephemeral=True)
        if len(self.players) >= 4:
            return await interaction.response.send_message("❌ اللوبي مكتمل (4 لاعبين كحد أقصى)!", ephemeral=True)
        
        self.players.append(interaction.user)
        await interaction.response.send_message(f"✅ انضم {interaction.user.mention} للعبة UNO!", ephemeral=False)

    @discord.ui.button(label="بدء اللعبة 🚀", style=discord.ButtonStyle.primary)
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.host:
            return await interaction.response.send_message("❌ فقط منشئ التحدي يمكنه بدء اللعبة!", ephemeral=True)
        if len(self.players) < 2:
            return await interaction.response.send_message("⚠️ يجب انضمام لاعبين اثنين على الأقل لبدء اللعبة!", ephemeral=True)
        
        self.stop()
        embed = discord.Embed(title="🃏 بدأت لعبة UNO!", description=f"اللاعبون: {', '.join([p.mention for p in self.players])}\nالدور الحالي عند: {self.players[0].mention}", color=0xE74C3C)
        await interaction.response.send_message(embed=embed)

@bot.command(name='اونو', aliases=['uno'])
async def start_uno(ctx):
    view = UnoLobbyView(ctx.author)
    embed = discord.Embed(title="🃏 تحدي لعبة أونو (UNO)", description=f"أنشأ {ctx.author.mention} روم لعبة أونو!\nاضغط **انضمام** للمشاركة (2-4 لاعبين).", color=0xE74C3C)
    await ctx.send(embed=embed, view=view)

# 2. لعبة مافيا Mafia
class MafiaJoinView(discord.ui.View):
    def __init__(self, host):
        super().__init__(timeout=60)
        self.host = host
        self.players = [host]

    @discord.ui.button(label="انضمام للمافيا 🔪", style=discord.ButtonStyle.danger)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user in self.players:
            return await interaction.response.send_message("⚠️ أنت في القائمة مسبقاً!", ephemeral=True)
        self.players.append(interaction.user)
        await interaction.response.send_message(f"✅ انضم {interaction.user.mention} للعبة مافيا!", ephemeral=False)

    @discord.ui.button(label="توزيع الأدوار 🎭", style=discord.ButtonStyle.primary)
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.host:
            return await interaction.response.send_message("❌ فقط صاحب اللوبي يوزع الأدوار!", ephemeral=True)
        if len(self.players) < 4:
            return await interaction.response.send_message("⚠️ تتطلب مافيا 4 لاعبين على الأقل!", ephemeral=True)

        roles = ["مافيا 🔪", "طبيب 🩺", "محقق 🔍"] + ["مواطن 👤"] * (len(self.players) - 3)
        random.shuffle(roles)

        for p, r in zip(self.players, roles):
            try:
                await p.send(f"🎭 دورك في لعبة مافيا السيرفر هو: **{r}**")
            except:
                pass

        await interaction.response.send_message("✅ تم توزيع الأدوار سراً في الخاص لجميع اللاعبين! بدأ الليل... 🌙")

@bot.command(name='مافيا', aliases=['mafia'])
async def start_mafia(ctx):
    view = MafiaJoinView(ctx.author)
    embed = discord.Embed(title="🔪 لعبة مافيا السيرفر", description=f"أنشأ {ctx.author.mention} لعبة مافيا جديدة!\nاضغط **انضمام** لدخول القائمة (4-8 لاعبين).", color=0x2C3E50)
    await ctx.send(embed=embed, view=view)

# 3. لعبة البلوت Baloot
class BalootLobbyView(discord.ui.View):
    def __init__(self, host):
        super().__init__(timeout=60)
        self.host = host
        self.players = [host]

    @discord.ui.button(label="انضمام للبلوت ♠️", style=discord.ButtonStyle.success)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user in self.players:
            return await interaction.response.send_message("⚠️ أنت منضم مسبقاً!", ephemeral=True)
        if len(self.players) >= 4:
            return await interaction.response.send_message("❌ اكتملت الجلسة (4 لاعبين)!", ephemeral=True)
        
        self.players.append(interaction.user)
        await interaction.response.send_message(f"✅ انضم {interaction.user.mention} لتربيعة البلوت!", ephemeral=False)

    @discord.ui.button(label="توزيع الأوراق 🃏", style=discord.ButtonStyle.primary)
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.host:
            return await interaction.response.send_message("❌ صاحب القعدة فقط يبدأ اللعبة!", ephemeral=True)
        if len(self.players) < 4:
            return await interaction.response.send_message("⚠️ لا تكتمل تربيعة البلوت إلا بـ 4 لاعبين!", ephemeral=True)

        embed = discord.Embed(
            title="♠️ بدأت صكة البلوت!",
            description=f"**الفريق الأول:** {self.players[0].mention} & {self.players[2].mention}\n**الفريق الثاني:** {self.players[1].mention} & {self.players[3].mention}\n\nجاري توزيع الأوراق سراً...",
            color=0x27AE60
        )
        await interaction.response.send_message(embed=embed)

@bot.command(name='بلوت', aliases=['baloot'])
async def start_baloot(ctx):
    view = BalootLobbyView(ctx.author)
    embed = discord.Embed(title="♠️ جلسة بلوت (Baloot)", description=f"حي الله {ctx.author.mention}! فتح صكة بلوت جديدة.\nاضغط **انضمام** لتقييد اسمك بالتربيعة (مطلوب 4 لاعبين).", color=0x27AE60)
    await ctx.send(embed=embed, view=view)

# 4. لعبة إكس أو Tic-Tac-Toe
class TicTacToeButton(discord.ui.Button):
    def __init__(self, x, y):
        super().__init__(style=discord.ButtonStyle.secondary, label="‎", row=x)
        self.x = x
        self.y = y

    async def callback(self, interaction: discord.Interaction):
        view: TicTacToeView = self.view
        if interaction.user != view.current_player:
            return await interaction.response.send_message("❌ ليس دورك الآن!", ephemeral=True)
        
        if view.board[self.x][self.y] != 0:
            return await interaction.response.send_message("⚠️ هذا المكان محجوز مسبقاً!", ephemeral=True)

        if view.current_player == view.playerX:
            self.style = discord.ButtonStyle.danger
            self.label = "X"
            view.board[self.x][self.y] = 1
            view.current_player = view.playerO
        else:
            self.style = discord.ButtonStyle.success
            self.label = "O"
            view.board[self.x][self.y] = -1
            view.current_player = view.playerX

        self.disabled = True
        winner = view.check_winner()
        
        if winner is not None:
            if winner == 1:
                content = f"🎉 الفائز هو {view.playerX.mention} مبروك!"
            elif winner == -1:
                content = f"🎉 الفائز هو {view.playerO.mention} مبروك!"
            else:
                content = "🤝 تعادل!"
            
            for child in view.children:
                child.disabled = True
            return await interaction.response.edit_message(content=content, view=view)

        await interaction.response.edit_message(content=f"دور اللاعب: {view.current_player.mention}", view=view)

class TicTacToeView(discord.ui.View):
    def __init__(self, playerX, playerO):
        super().__init__()
        self.playerX = playerX
        self.playerO = playerO
        self.current_player = playerX
        self.board = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
        for x in range(3):
            for y in range(3):
                self.add_item(TicTacToeButton(x, y))

    def check_winner(self):
        for row in self.board:
            if row[0] == row[1] == row[2] != 0: return row[0]
        for col in range(3):
            if self.board[0][col] == self.board[1][col] == self.board[2][col] != 0: return self.board[0][col]
        if self.board[0][0] == self.board[1][1] == self.board[2][2] != 0: return self.board[0][0]
        if self.board[0][2] == self.board[1][1] == self.board[2][0] != 0: return self.board[0][2]
        if all(cell != 0 for row in self.board for cell in row): return 0
        return None

@bot.command(name='تكس_او', aliases=['tictactoe'])
async def tictactoe(ctx, member: discord.Member):
    if member == ctx.author or member.bot:
        return await ctx.send("❌ لا يمكنك تحدي نفسك أو بوت!")
    view = TicTacToeView(ctx.author, member)
    await ctx.send(f"🎮 تحدي إكس أو بين {ctx.author.mention} و {member.mention}!\nالبداية مع: {ctx.author.mention}", view=view)

# 5. لعبة حجرة ورقة مقص
@bot.command(name='حجرة', aliases=['rps'])
async def rps(ctx, choice: str):
    choices = {"حجرة": "rock", "ورقة": "paper", "مقص": "scissors"}
    user_choice = choices.get(choice.lower())
    if not user_choice:
        return await ctx.send("❌ اختيار غير صحيح! استخدم: `حجرة` أو `ورقة` أو `مقص`.")
    
    bot_choice_ar = random.choice(list(choices.keys()))
    bot_choice = choices[bot_choice_ar]
    
    if user_choice == bot_choice:
        result = "🤝 تعادل!"
    elif (user_choice == "rock" and bot_choice == "scissors") or \
         (user_choice == "paper" and bot_choice == "rock") or \
         (user_choice == "scissors" and bot_choice == "paper"):
        result = "🎉 هنيئاً لك، لقد فزت!"
    else:
        result = "🤖 هاردلك، البوت فاز عليك!"
        
    embed = discord.Embed(title="✊ حجرة ورقة مقص", color=0xF1C40F)
    embed.add_field(name="اختيارك", value=choice, inline=True)
    embed.add_field(name="اختيار البوت", value=bot_choice_ar, inline=True)
    embed.add_field(name="النتيجة", value=result, inline=False)
    await ctx.send(embed=embed)

# 6. لعبة أسرع كتابة
WORDS_LIST = [
    # شخصيات وأنمي
    "لوفي", "ناروتو", "زورو", "سانجي", "ايرين", "مادارا", "توجي", "سايتاما", "ساسكي", "كاكاشي", "غوكو", "باكوغو", "توتورو", "لايت ياجامي", "ليفاي",
    "جوجوتسو كايسن", "هجوم العمالقة", "ون بيس", "دراغون بول", "انمي", "اوتاكو",
    
    # ألعاب الفيديو
    "جراند", "ريد ديد", "جود اوف وور", "ماين كرافت", "كول اوف ديوتي", "وارزون", "باتلفيلد", "فورتنايت", "فالورانت", "سايبربانك", "ايلدن رينج", "ذا لاست اوف اوس", "رزدنت ايفل", "اساسنز كريد", "انشارتد",
    "بلايستيشن", "اكس بوكس", "بي سي",
    
    # مسلسلات وأفلام
    "بريكنج باد", "جيم اوف ثرونز", "سترانجر ثينقز", "بيكي بلايندرز", "ذا اوفيس", "ذا بويز", "ذا ووكينج ديد", "رشاش", "طاش ما طاش", "شباب البومب", "سكويد جيم", "لوسيفر", "افنجرز", "باتمان", "سبايدرمان", "هاري بوتر", "الجوكر",
    "نتفلكس", "سينما",
    
    # طرب وفن شعبي
    "محمد عبده", "طلال مداح", "راشد الماجد", "عبد المجيد عبد الله", "ماجد المهندس", "رابح صقر", "الأماكن", "المسافر", "مقادير", "بعاد كنتم", "صوتك يناديني", "جمر الغضى",
    "عبادي الجوهر", "خالد عبد الرحمن", "جلسة طرب", "عود", "قانون",
    
    # الطبيعة (بحر، سماء، مطر، جبل وما شابهها)
    "بحر", "سماء", "مطر", "جبل", "صحراء", "غابة", "نهر", "سحاب", "برق", "رعد",
    "ليل", "نهار", "شمس", "قمر", "نجم", "وادي", "واحة", "نسيم", "عاصفة", "ضباب"
]

@bot.command(name='سرعة', aliases=['typing_game'])
async def typing_game(ctx):
    word = random.choice(WORDS_LIST)
    embed = discord.Embed(title="⌨️ تحدي أسرع كتابة", description=f"اكتب العبارة التالية بأسرع ما يمكن في الشات (لديك **5 ثوانٍ**):\n\n`{word}`", color=0x3498DB)
    await ctx.send(embed=embed)
    
    def check(m):
        return m.channel == ctx.channel and not m.author.bot and m.content.strip() == word

    try:
        msg = await ctx.bot.wait_for('message', timeout=5.0, check=check)
        new_total = add_money(msg.author.id, 5.00)
        await ctx.send(f"🏆 كفو يا {msg.author.mention}! أسرع واحد كتبها بدقة وصار الفائز!\n💰 تم إضافة **5.00$** إلى رصيدك بالبنك! (إجمالي رصيدك: **${new_total:.2f}**)")
    except asyncio.TimeoutError:
        await ctx.send(f"⏰ انتهى الوقت (5 ثوانٍ)! ما أحد كتب الكلمة (`{word}`) بالوقت المناسب.")
        
# ==================== حساب ساعات العمل (دخول / خروج / سجل) ====================
LOGS_FILE = "duty_logs.json"

def load_logs():
    if os.path.exists(LOGS_FILE):
        try:
            with open(LOGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_logs(data):
    try:
        with open(LOGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"خطأ في حفظ ملف السجلات: {e}")

active_sessions = {}
duty_data = load_logs()

DUTY_ADMIN_ROLE_ID = 1559695654475792394

@bot.tree.command(name="دخول", description="تسجيل وقت الدخول وتتبع ساعات العمل")
async def entry(interaction: discord.Interaction):
    user_id_str = str(interaction.user.id)

    if user_id_str in active_sessions:
        return await interaction.response.send_message(
            f"⚠️ {interaction.user.mention}، أنت مسجل دخول بالفعل!",
            ephemeral=True,
        )

    current_time = time.time()
    active_sessions[user_id_str] = current_time

    await interaction.response.send_message(
        f"✅ تم تسجيل الدخول بنجاح، حياك الله {interaction.user.mention}!",
        ephemeral=False,
    )

@bot.tree.command(name="خروج", description="تسجيل الخروج وحساب إجمالي وقت التواجد")
async def exit(interaction: discord.Interaction):
    user_id_str = str(interaction.user.id)

    if user_id_str not in active_sessions:
        return await interaction.response.send_message(
            f"⚠️ {interaction.user.mention}، أنت لم تقم بتسجيل الدخول أساساً أو أنك سجلت خروجك مسبقاً!",
            ephemeral=True,
        )

    start_time = active_sessions.pop(user_id_str)
    end_time = time.time()
    elapsed_seconds = int(end_time - start_time)

    if user_id_str not in duty_data:
        duty_data[user_id_str] = []

    duty_data[user_id_str].append(
        {"start": start_time, "end": end_time, "duration": elapsed_seconds}
    )
    save_logs(duty_data)

    hours = elapsed_seconds // 3600
    minutes = (elapsed_seconds % 3600) // 60
    seconds = elapsed_seconds % 60

    time_str = f"⏱️ إجمالي مدة التواجد: `{hours} ساعة` و `{minutes} دقيقة` و `{seconds} ثانية`"
    await interaction.response.send_message(
        f"🚪 تم تسجيل الخروج بنجاح {interaction.user.mention}!\n{time_str}",
        ephemeral=False,
    )

@bot.tree.command(name="سجل_الدوام", description="عرض سجل ساعات العمل بين تاريخين محددين")
@app_commands.describe(
    من_تاريخ="التاريخ البدء بصيغة YYYY-MM-DD",
    الى_تاريخ="التاريخ الانتهاء بصيغة YYYY-MM-DD",
)
async def duty_records(interaction: discord.Interaction, من_تاريخ: str, الى_تاريخ: str):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message(
            "❌ عذراً، هذا الأمر مخصص للإداريين فقط.", ephemeral=True
        )

    try:
        start_date = datetime.strptime(من_تاريخ, "%Y-%m-%d")
        end_date = datetime.strptime(الى_تاريخ, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59
        )
    except ValueError:
        return await interaction.response.send_message(
            "❌ صيغة التاريخ غير صحيحة! استخدم صيغة `YYYY-MM-DD`.",
            ephemeral=True,
        )

    report_text = f"📊 **سجل ساعات الدوام من {من_تاريخ} إلى {الى_تاريخ}**:\n\n"
    found_any = False

    for user_id_str, sessions in duty_data.items():
        total_user_seconds = 0
        for session in sessions:
            if start_date.timestamp() <= session["start"] <= end_date.timestamp():
                total_user_seconds += session["duration"]

        if total_user_seconds > 0:
            found_any = True
            member = interaction.guild.get_member(int(user_id_str))
            username = member.mention if member else f"مستخدم (ID: {user_id_str})"

            h = total_user_seconds // 3600
            m = (total_user_seconds % 3600) // 60
            s = total_user_seconds % 60
            report_text += f"👤 {username} ➔ **{h} ساعة** و **{m} دقيقة** و **{s} ثانية**\n"

    if not found_any:
        report_text = "📭 لا توجد أي سجلات دوام مسجلة خلال هذه الفترة."

    await interaction.response.send_message(report_text, ephemeral=False)

@bot.tree.command(name="تعديل_الدوام", description="زيادة أو إنقاص ساعات الدوام لمشرف معين")
@app_commands.describe(
    العضو="اختر العضو المراد تعديل ساعاته",
    العملية="اختر هل تريد زيادة أو نقص",
    الساعات="عدد الساعات (يمكنك وضع أرقام عشرية مثل 0.5 أو أرقام صحيحة)",
)
@app_commands.choices(
    العملية=[
        app_commands.Choice(name="زيادة (+)", value="add"),
        app_commands.Choice(name="نقصان (-)", value="sub"),
    ]
)
async def edit_duty(interaction: discord.Interaction, العضو: discord.Member, العملية: str, الساعات: float):
    has_permission = interaction.user.guild_permissions.administrator
    if not has_permission and any(role.id == DUTY_ADMIN_ROLE_ID for role in interaction.user.roles):
        has_permission = True

    if not has_permission:
        return await interaction.response.send_message(
            "❌ عذراً، هذا الأمر مخصص فقط لرتبة الإدارة المحددة أو الأدمن.",
            ephemeral=True,
        )

    user_id_str = str(العضو.id)
    seconds_to_adjust = int(الساعات * 3600)

    if user_id_str not in duty_data:
        duty_data[user_id_str] = []

    if العملية == "add":
        duty_data[user_id_str].append(
            {
                "start": time.time() - seconds_to_adjust,
                "end": time.time(),
                "duration": seconds_to_adjust,
            }
        )
        action_text = f"زيادة **{الساعات} ساعة**"
    else:
        duty_data[user_id_str].append(
            {
                "start": time.time(),
                "end": time.time() + seconds_to_adjust,
                "duration": -seconds_to_adjust,
            }
        )
        action_text = f"خصم **{الساعات} ساعة**"

    save_logs(duty_data)

    await interaction.response.send_message(
        f"✅ تم بنجاح {action_text} لـ {العضو.mention}!", ephemeral=False
    )

# ==================== فحص الروم الصوتي CheckVC ====================
@bot.command(name='checkvc', help='فحص الروم الصوتي وعرض الأعضاء')
async def checkvc(ctx, *, channel_input: str = None):
    channel_id = None
    if channel_input:
        clean_input = channel_input.replace('<#', '').replace('>', '').strip()
        try:
            channel_id = int(clean_input)
        except ValueError:
            pass

    voice_channel = None
    if channel_id:
        voice_channel = ctx.guild.get_channel(channel_id)
    
    if not voice_channel and ctx.author.voice:
        voice_channel = ctx.author.voice.channel

    if not voice_channel or not isinstance(voice_channel, discord.VoiceChannel):
        await ctx.send("❌ يرجى تحديد روم صوتي صحيح!")
        return

    members = voice_channel.members
    if not members:
        await ctx.send(f"📭 الروم الصوتي `{voice_channel.name}` فارغ حالياً.")
        return

    sorted_members = sorted(members, key=lambda m: m.joined_at if m.joined_at else datetime.max)
    info_embed = discord.Embed(
        title="Check Voice Channel",
        description=f"**Voice Channel :** 🔊 {voice_channel.mention}\n**All in Voice :** `{len(members)}`",
        color=discord.Color.from_rgb(47, 49, 54)
    )
    await ctx.send(embed=info_embed)

    text_content = "**List Members**\n"
    for idx, member in enumerate(sorted_members, start=1):
        text_content += f"`{idx}` | {member.mention}\n"
    await ctx.send(text_content)

# ==================== معالجة الرسائل والفعاليات والأوامر ====================
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    content = message.content.strip()

    if content.startswith('!تايم اوت') or content.startswith('!فك تايم اوت'):
        if not message.author.guild_permissions.moderate_members:
            await message.reply('❌ ليس لديك صلاحية لاستخدام هذا الأمر.')
            return

        log_channel = message.guild.get_channel(TIMEOUT_LOG_CHANNEL_ID)

        if content.startswith('!تايم اوت'):
            args = content[9:].strip().split()
            if not args:
                await message.reply('⚠️ يرجى تحديد العضو.')
                return

            target_member = None
            if message.mentions:
                target_member = message.guild.get_member(message.mentions[0].id)
                args_start_idx = 1
            else:
                try:
                    user_id = int(args[0])
                    target_member = message.guild.get_member(user_id) or await message.guild.fetch_member(user_id)
                    args_start_idx = 1
                except:
                    await message.reply('❌ لم يتم العثور على العضو.')
                    return

            duration_delta = discord.utils.utcnow() + timedelta(days=28)
            reason = " ".join(args[args_start_idx:]) if len(args) > args_start_idx else 'بدون سبب'

            try:
                await target_member.timeout(duration_delta, reason=reason)
                embed = discord.Embed(title='⏳ تم تطبيق تايم أوت مفتوح على عضو', color=0xFFA500, timestamp=discord.utils.utcnow())
                embed.add_field(name='👤 العضو', value=f"<@{target_member.id}>", inline=True)
                embed.add_field(name='🛡️ بواسطة', value=f"<@{message.author.id}>", inline=True)
                
                if log_channel:
                    await log_channel.send(embed=embed)
                else:
                    await message.channel.send(embed=embed)
                
                responses = ["تمممممممممممممم", "ابشرررررررررررررررر", "بس نايم اوت ؟ خل موضوعه عندي", "هو زعلك ؟ والله مايمشي"]
                await message.reply(random.choice(responses))
            except Exception as e:
                await message.reply(f'❌ حدث خطأ: {e}')
            return

        if content.startswith('!فك تايم اوت'):
            args = content[12:].strip().split()
            if not args:
                await message.reply('⚠️ يرجى تحديد العضو.')
                return

            target_member = None
            if message.mentions:
                target_member = message.guild.get_member(message.mentions[0].id)
            else:
                try:
                    user_id = int(args[0])
                    target_member = message.guild.get_member(user_id) or await message.guild.fetch_member(user_id)
                except:
                    await message.reply('❌ لم يتم العثور على العضو.')
                    return

            try:
                await target_member.timeout(None, reason="فك التايم أوت")
                embed = discord.Embed(title='🔓 تم فك التايم أوت عن عضو', color=0x00FF00, timestamp=discord.utils.utcnow())
                if log_channel:
                    await log_channel.send(embed=embed)
                await message.reply("تمممممم")
            except Exception as e:
                await message.reply(f'❌ حدث خطأ: {e}')
            return

    if content.startswith('!باند') or content.startswith('!ban') or content.startswith('!فك باند') or content.startswith('!unban'):
        if not message.author.guild_permissions.ban_members and not message.author.guild_permissions.moderate_members:
            await message.reply('❌ ليس لديك صلاحية لاستخدام هذا الأمر.')
            return

        ban_log_channel = message.guild.get_channel(BAN_LOG_CHANNEL_ID)

        if content.startswith('!باند') or content.startswith('!ban'):
            prefix_len = 5 if content.startswith('!باند') else 4
            args = content[prefix_len:].strip().split()
            if not args:
                await message.reply('⚠️ يرجى تحديد العضو.')
                return

            target_user_id = message.mentions[0].id if message.mentions else int(args[0])
            reason = " ".join(args[1:]) if len(args) > 1 else 'بدون سبب'

            try:
                user_obj = await bot.fetch_user(target_user_id)
                await message.guild.ban(user_obj, reason=reason)
                embed = discord.Embed(title='🔨 تم حظر عضو نهائياً (باند)', color=0xFF0000, timestamp=discord.utils.utcnow())
                embed.add_field(name='👤 العضو', value=f"<@{target_user_id}>", inline=True)
                if ban_log_channel:
                    await ban_log_channel.send(embed=embed)
                await message.reply("انقرض ياوحش")
            except Exception as e:
                await message.reply(f'❌ حدث خطأ: {e}')
            return

    if content == "سؤال":
        selected = random.choice(MASSIVE_QUESTIONS)
        embed = discord.Embed(
            title="🧠 فعالية سؤال وجواب", 
            description=f"**السؤال:** {selected['q']}\n\n💡 *الجائزة: 0.50$ تضاف لحسابك بالبنك عند الفوز!*\nلديك **5 ثوانٍ** للإجابة في الشات!", 
            color=discord.Color.blue()
        )
        await message.channel.send(embed=embed)

        def check_q(msg):
            if msg.channel.id != message.channel.id or msg.author.bot:
                return False
            if selected['q'] == "من اهطف واحد بالسيرفر؟":
                return True
            return msg.content.strip().lower() in [str(ans).lower() for ans in selected['a']]

        try:
            winner = await bot.wait_for('message', timeout=5.0, check=check_q)
            new_total = add_money(winner.author.id, 0.50)
            await message.channel.send(f"🎉 **كفو يا {winner.author.mention}!** إجابتك صحيحة.\n💰 تم إضافة **0.50$** إلى رصيدك بالبنك! (إجمالي رصيدك: **${new_total:.2f}**)")
        except asyncio.TimeoutError:
            await message.channel.send(f"⏰ انتهى الوقت (5 ثوانٍ) ولم يجُب أحد!")
        return

    if content and not content.startswith('!'):
        first_word = content.split()[0]
        if first_word in ['حذف', 'مسح', 'purge', 'clear', 'شغل', 'p', 'سكب', 's', 'وقف', 'كمل', 'إنهاء', 'stop', 'انتظار', 'q', 'اطلع', 'روليت', 'بنك', 'اونو', 'مافيا', 'كودنيمز', 'بلوت', 'تكس_او', 'حجرة', 'سرعة']:
            message.content = '!' + content

    await bot.process_commands(message)

# ==================== أوامر الموسيقى ====================
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'scsearch',
    'source_address': '0.0.0.0',
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -loglevel error'
}

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
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **FFMPEG_OPTIONS), data=data)

def play_next(ctx):
    queue = get_queue(ctx.guild.id)
    if len(queue) > 0:
        next_song = queue.pop(0)
        asyncio.run_coroutine_threadsafe(play_song(ctx, next_song), bot.loop)

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
    if not channel:
        return
    embed = discord.Embed(description=f"| - Welcome To 82 Group\n| - Member Name : {member.mention}", color=discord.Color.dark_embed())
    embed.set_thumbnail(url=member.display_avatar.url)
    await channel.send(embed=embed)

@bot.command(name='حذف', aliases=['مسح', 'purge', 'clear'])
@commands.has_permissions(manage_messages=True)
async def clear_messages(ctx, amount: int = 10):
    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"🧹 تم حذف **{len(deleted) - 1}** رسالة بنجاح!")
    await asyncio.sleep(3)
    try:
        await msg.delete()
    except:
        pass

@bot.command(name='شغل', aliases=['p'])
async def play(ctx, *, url):
    if not ctx.author.voice:
        return await ctx.send("يرجى الانضمام إلى روم صوتي أولاً!")
    channel = ctx.author.voice.channel
    if ctx.voice_client is None:
        await channel.connect()
    elif ctx.voice_client.channel != channel:
        await ctx.voice_client.move_to(channel)
    
    queue = get_queue(ctx.guild.id)
    if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
        queue.append(url)
        await ctx.send(f"📥 تم إضافة طلبك إلى قائمة الانتظار (**{len(queue)}**)")
    else:
        await play_song(ctx, url)

@bot.command(name='سكب', aliases=['s'])
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ تم تخطي الأغنية الحالية.")

@bot.command(name='وقف')
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸️ تم إيقاف التشغيل مؤقتاً.")

@bot.command(name='كمل')
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶️ تم استكمال التشغيل.")

@bot.command(name='إنهاء', aliases=['stop'])
async def stop(ctx):
    guild_id = ctx.guild.id
    if guild_id in song_queues:
        song_queues[guild_id].clear()
    if ctx.voice_client:
        ctx.voice_client.stop()
        await ctx.send("⏹️ تم إيقاف التشغيل وتفريغ القائمة.")

@bot.command(name='انتظار', aliases=['q'])
async def show_queue(ctx):
    queue = get_queue(ctx.guild.id)
    if not queue:
        return await ctx.send("📜 قائمة الانتظار فارغة.")
    description = "\n".join([f"**{i+1}.** {url}" for i, url in enumerate(queue)])
    embed = discord.Embed(title="📜 قائمة الأغاني المنتظرة", description=description, color=discord.Color.blue())
    await ctx.send(embed=embed)

@bot.command(name='اطلع')
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("تم الخروج من الروم الصوتي.")

# ==================== نظام البنك ====================
BANK_FILE = "bank_data.json"

def load_bank():
    if os.path.exists(BANK_FILE):
        with open(BANK_FILE, "r") as f:
            try: return json.load(f)
            except: return {}
    return {}

def save_bank(data):
    with open(BANK_FILE, "w") as f: json.dump(data, f, indent=4)

def add_money(user_id, amount=0.50):
    data = load_bank()
    uid = str(user_id)
    data[uid] = round(data.get(uid, 0.0) + amount, 2)
    save_bank(data)
    return data[uid]

@bot.command(name='بنك')
async def bank(ctx):
    user = ctx.author
    balance = load_bank().get(str(user.id), 0.0)
    await ctx.send(f"🏦 رصيدك الحالي يا {user.mention} هو: **${balance:.2f}**")

# ==================== بنك الأسئلة ====================
MASSIVE_QUESTIONS = [
    {"q": "من اهطف واحد بالسيرفر؟", "a": ["الجميع", "كلنا", "انت", "محد", "اي شي", "غير معروف"]},
    {"q": "ما اسم بطل لعبة ريد ديد ريديمشن 2؟", "a": ["آرثر مورجان", "ارثر مورجان", "arthur morgan"]},
    {"q": "ما اسم الشركة المنتجة للعبة جراند ثيفت أوتو (GTA)؟", "a": ["روكستار", "روكستار جيمز", "rockstar"]},
    {"q": "ما اسم اللعبة الشهيرة التي تعتمد على بناء المكعبات؟", "a": ["ماين كرافت", "minecraft"]},
    {"q": "ما اسم بطل سلسلة ألعاب جود أوف وور (God of War)؟", "a": ["كريتوس", "kratos"]},
    {"q": "ما اسم الشخصية الرئيسية في سلسلة العاب زيلدا؟", "a": ["لينك", "link"]},
    {"q": "ما اسم بطل مسلسل بريكنج باد الذي يلقب بـ هايزنبرغ؟", "a": ["والتر وايت", "walter white"]},
    {"q": "ما اسم المسلسل السعودي الشهير الذي ناقش قضايا الجريمة في الثمانينات؟", "a": ["رشاش"]},
    {"q": "ما اسم شخصية توماس شيلبي الرئيسية في أي مسلسل؟", "a": ["بيكي بلايندرز", "peaky blinders"]},
    {"q": "ما اسم الأنمي الشهير الذي يتحدث عن كنز الغراند لاين وقائدهم لوفي؟", "a": ["ون بيس", "one piece"]},
    {"q": "ما اسم بطل أنمي هجوم العمالقة؟", "a": ["إيرين", "ايرين", "eren"]},
    {"q": "ما اسم الممثل الذي لعب دور الجوكر في فيلم The Dark Knight؟", "a": ["هيث ليدجر", "heath ledger"]},
    {"q": "ما هي اللعبة الحربية التابعة لكود وتعتمد على الباتل رويال المجاني؟", "a": ["وارزون", "warzone"]},
    {"q": "ما اسم القرية التي ينتمي إليها ناروتو؟", "a": ["كونوها", "قرية كونوها"]},
    {"q": "ما اسم اللعبة الشهيرة ذات النمط الكرتوني للبناء والقتال من تطوير أسطورة إپك جيمز؟", "a": ["فورتنايت", "fortnite"]}
]

# ==================== تشغيل الويب سيرفر والبوت معاً ====================
if __name__ == "__main__":
    from flask import Flask
    from threading import Thread
    
    app = Flask('')
    @app.route('/')
    def home():
        return "I'm alive!", 200
        
    def run_flask():
        port = int(os.environ.get("PORT", 8080))
        app.run(host='0.0.0.0', port=port)
        
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    
    # ⚠️ استبدل النص التالي بالتوكن الحقيقي الخاص بك بين العلامتين التنصيص
    bot_token = "MTU1MzAxMTY1MTkyODkyMDEzNA.GQj9eF.6jRFlyaLwU_jS4m43Ix9KW5-QIkx-ERpPUj6zY"
    bot.run(bot_token)
