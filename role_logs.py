import discord
from discord.ext import commands
import datetime

class RoleLogs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # آيدي روم سجلات الرولات المخصص
        self.LOG_CHANNEL_ID = 1553485936073908244
        
        # روابط الصور الجديدة للإعطاء والإزالة
        self.ROLE_ADD_ICON_URL = "https://media.discordapp.net/attachments/1390933149348790413/1392500394051108945/e1e2c025-74d2-4780-92ba-c2d716f742e4_1.png"
        self.ROLE_REMOVE_ICON_URL = "https://media.discordapp.net/attachments/1390933149348790413/1392500726491779245/ec06bac1-3b9c-462e-87ac-24a8802c4bf0.png"

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        # التحقق من وجود تغيير في الرولات
        if before.roles == after.roles:
            return

        guild = after.guild
        log_channel = guild.get_channel(self.LOG_CHANNEL_ID)
        if not log_channel:
            return

        # جلب بيانات المشرف الذي قام بالتعديل من الـ Audit Logs
        executor = None
        try:
            async for entry in guild.audit_logs(limit=3, action=discord.AuditLogAction.member_role_update):
                if entry.target.id == after.id:
                    executor = entry.user
                    break
        except Exception as e:
            print(f"خطأ أثناء جلب سجلات التدقيق: {e}")

        executor_mention = executor.mention if executor else "غير معروف"

        # ==================== 1. حالة إعطاء رول (Role Add) ====================
        added_roles = [role for role in after.roles if role not in before.roles]
        for role in added_roles:
            embed = discord.Embed(
                title="Role Add",
                description=f"**To :** {after.mention}\n**By :** {executor_mention}",
                color=discord.Color.from_rgb(47, 49, 54),
                timestamp=discord.utils.utcnow()
            )

            # أفتار العضو مصغر فوق يسار بجانب الاسم
            embed.set_author(name=after.name, icon_url=after.display_avatar.url)
            
            # صورة الإعطاء كبيرة فوق يمين (Thumbnail)
            embed.set_thumbnail(url=self.ROLE_ADD_ICON_URL)

            # المربع الداخلي يحتوي على اسم الرول فقط
            embed.add_field(
                name="\u200b",
                value=f"```\n✅ - {role.name}\n```",
                inline=False
            )

            guild_icon = guild.icon.url if guild.icon else None
            embed.set_footer(text=f".      {guild.name}", icon_url=guild_icon)

            await log_channel.send(embed=embed)

        # ==================== 2. حالة سحب رول (Role Remove) ====================
        removed_roles = [role for role in before.roles if role not in after.roles]
        for role in removed_roles:
            embed = discord.Embed(
                title="Role Remove",
                description=f"**To :** {after.mention}\n**By :** {executor_mention}",
                color=discord.Color.from_rgb(47, 49, 54),
                timestamp=discord.utils.utcnow()
            )

            # أفتار العضو مصغر فوق يسار بجانب الاسم
            embed.set_author(name=after.name, icon_url=after.display_avatar.url)
            
            # صورة الإزالة كبيرة فوق يمين (Thumbnail)
            embed.set_thumbnail(url=self.ROLE_REMOVE_ICON_URL)

            # المربع الداخلي يحتوي على اسم الرول فقط
            embed.add_field(
                name="\u200b",
                value=f"```\n❌ - {role.name}\n```",
                inline=False
            )

            guild_icon = guild.icon.url if guild.icon else None
            embed.set_footer(text=f".      {guild.name}", icon_url=guild_icon)

            await log_channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(RoleLogs(bot))
