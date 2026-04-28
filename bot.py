import discord
from discord.ext import commands
from discord import app_commands
import os
from flask import Flask
from threading import Thread

# --- Discord 机器人核心逻辑 ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# 1. 按钮与状态管理看板
class PrintManageView(discord.ui.View):
    def __init__(self, requester: discord.Member):
        super().__init__(timeout=None) # 按钮永久有效
        self.requester = requester

    @discord.ui.button(label="开始打印", style=discord.ButtonStyle.primary, custom_id="btn_start")
    async def start_print(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.gold()
        embed.set_field_at(1, name="状态", value="正在打印 🖨️", inline=False)
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label="打印完成", style=discord.ButtonStyle.success, custom_id="btn_finish")
    async def finish_print(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 1. @用户发通知
        await interaction.channel.send(f"📢 通知：{self.requester.mention} 你的模型已打印完成，请尽快领取！")
        
        # 2. 修改卡片为最终状态
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.set_field_at(1, name="状态", value="✅ 已完成并归档", inline=False)
        
        # 3. 移动到归档频道 (读取环境变量中的 ID)
        archive_id = int(os.environ.get("ARCHIVE_CHANNEL_ID", 0))
        archive_channel = bot.get_channel(archive_id)
        if archive_channel:
            await archive_channel.send(embed=embed)
        else:
            await interaction.channel.send("⚠️ 警告：未找到归档频道，任务已标记完成但未转移。")
            
        # 4. 删除原频道的任务卡片
        await interaction.message.delete()

# 2. 必填参数弹窗 (Modal) - 包含组件修复
class PrintRequestModal(discord.ui.Modal):
    def __init__(self, file_attachment: discord.Attachment):
        super().__init__(title="补充打印参数")
        self.file_attachment = file_attachment
        
        # 定义输入框
        self.material = discord.ui.TextInput(label='材料 (如 PLA/PETG/ABS)', placeholder='请填写材料...', required=True)
        self.quantity = discord.ui.TextInput(label='打印数量', placeholder='1', required=True)
        
        # 将输入框加入到弹窗中
        self.add_item(self.material)
        self.add_item(self.quantity)

    async def on_submit(self, interaction: discord.Interaction):
        # 生成看板卡片
        embed = discord.Embed(title="📋 新打印任务", color=discord.Color.blue())
        embed.add_field(name="模型文件", value=f"[{self.file_attachment.filename}]({self.file_attachment.url})", inline=False)
        embed.add_field(name="状态", value="等待中 ⏳", inline=False)
        embed.add_field(name="材料", value=self.material.value, inline=True)
        embed.add_field(name="数量", value=self.quantity.value, inline=True)
        embed.set_footer(text=f"提交人: {interaction.user.display_name}")

        view = PrintManageView(interaction.user)
        await interaction.response.send_message(embed=embed, view=view)

# 3. 带附件的斜杠命令
@bot.tree.command(name="print", description="上传模型文件并提交打印需求")
@app_commands.describe(file="请上传你需要打印的模型文件 (强制必填)")
async def slash_print(interaction: discord.Interaction, file: discord.Attachment):
    # 直接呼出带有材料和数量的表单
    await interaction.response.send_modal(PrintRequestModal(file))

@bot.event
async def on_ready():
    await bot.tree.sync() 
    print(f'🤖 机器人已上线: {bot.user}')

# --- 假装自己是个网页服务 (绕过云平台的存活检查，配合 UptimeRobot 使用) ---
app = Flask(__name__)
@app.route('/')
def home():
    return "3D Print Bot is running smoothly!"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

# --- 启动器 ---
if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.run(os.environ.get("DISCORD_TOKEN"))
