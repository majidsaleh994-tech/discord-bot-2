import discord
from discord.ext import commands
import random
import asyncio

# تحديد الصلاحيات اللازمة لقراءة الرسائل والأعضاء
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'✅ البوت يعمل بنجاح باسم: {bot.user}')

# --- 1. واجهة زر الانضمام للفعالية العامة ---
class EventView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=20)  # مدة التجميع 20 ثانية
        self.participants = []

    @discord.ui.button(label="انضمام للفعالية 🎯", style=discord.ButtonStyle.success)
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user in self.participants:
            await interaction.response.send_message("⚠️ أنت انضممت بالفعل!", ephemeral=True)
        else:
            self.participants.append(interaction.user)
            await interaction.response.send_message("✅ تم تسجيل انضمامك بنجاح!", ephemeral=True)

@bot.command(name='فعالية')
async def start_event(ctx):
    view = EventView()
    msg = await ctx.send("🎉 **بدأت فعالية جديدة!** اضغط على الزر لأسفله للانضمام. (معك 20 ثانية)", view=view)
    
    await view.wait()  # الانتظار لحين انتهاء الوقت

    # تعطيل الأزرار بعد انتهاء الوقت
    for item in view.children:
        item.disabled = True
    await msg.edit(view=view)

    if not view.participants:
        await ctx.send("❌ انتهى الوقت ولم ينضم أي شخص للفعالية.")
    else:
        winner = random.choice(view.participants)
        await ctx.send(f"🎉 **مبروك!** الفائز في الفعالية هو: {winner.mention} 👑")

# --- 2. لعبة الروليت الروسية بالأزرار ---
class RussianRouletteView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.bullet_index = random.randint(0, 5)  # رصاصة واحدة في مخزن من 6 حجرات
        self.current_chamber = 0

    @discord.ui.button(label="اسحب الزناد 💀", style=discord.ButtonStyle.danger)
    async def pull_trigger(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_chamber == self.bullet_index:
            for item in self.children:
                item.disabled = True
            await interaction.response.edit_message(view=self)
            await interaction.followup.send(f"💥 **بوووم!** خرجت الرصاصة في {interaction.user.mention}! لقد خسرت اللعبة 💀")
            self.stop()
        else:
            self.current_chamber += 1
            await interaction.response.send_message(f"⚙️ *كليك...* حجرة فارغة! نجا {interaction.user.mention} من الموت 😅")

@bot.command(name='روليت-روسية')
async def russian_roulette(ctx):
    view = RussianRouletteView()
    await ctx.send("🔫 **بدأت لعبة الروليت الروسية!** من يجرأ على سحب الزناد؟ (المخزن فيه 6 حجرات ورصاصة واحدة)", view=view)

# --- 3. روليت الروم الصوتي العشوائي ---
@bot.command(name='روليت')
async def roulette(ctx):
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("❌ يجب أن تكون داخل روم صوتي لبدء الروليت!")
        return

    channel = ctx.author.voice.channel
    members = [m for m in channel.members if not m.bot]

    if len(members) < 2:
        await ctx.send("⚠️ يجب أن يكون هناك شخصين على الأقل في الروم الصوتي!")
        return

    msg = await ctx.send("🎰 **جاري تدوير عجلة الروليت...** 🎰")
    await asyncio.sleep(3)
    
    chosen = random.choice(members)
    await msg.edit(content=f"🎯 **النتيجة:** وقعت القرعة على {chosen.mention}!")

# ضع التوكن الخاص ببوتك هنا بين العلامتين ''
bot.run('YOUR_BOT_TOKEN_HERE')