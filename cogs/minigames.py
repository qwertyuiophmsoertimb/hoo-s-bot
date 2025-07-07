import discord
from discord.ext import commands, tasks
from discord.ext.commands import MissingRequiredArgument
import random
from datetime import datetime, timedelta, date, timezone

# Import constants and data management functions
from config import (
    CONFIG, AUTHORIZED_USER_ID,
    FORTUNES, COLOR_MAP, PRAY_IMAGE_MAP,
    HUNTING_RESULTS, HUNT_IMAGE_MAP,
    SLOTS_SYMBOLS, SLOTS_WINNINGS,
    DRAW_EMOTES, SHOP_PET_LIST,
    MINIGAME_RESET_CHANNEL_ID
)
from data_manager import get_user_data, update_user_data, user_data # Import user_data directly for bot balance

# Global variables for the guess game
guess_cooldowns = {}
participants = set()
answer = random.randint(1, 774)
game_active = True
last_reset_day = date.today()

def get_user_avatar(user):
    return user.avatar.url if user.avatar else user.default_avatar.url

class Minigames(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daily_reset_task.start() # Start the daily reset task

    def cog_unload(self):
        self.daily_reset_task.cancel() # Cancel the task when cog is unloaded

    async def _reset_guess_game(self):
        global answer, game_active, guess_cooldowns, participants, last_reset_day
        answer = random.randint(1, 774)
        game_active = True
        guess_cooldowns = {}
        participants.clear()
        last_reset_day = date.today()

        channel = self.bot.get_channel(MINIGAME_RESET_CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                title="🔢 猜數字遊戲",
                description=("🎯 數字猜謎遊戲已重置！快來猜 1～774 的神秘數字吧！"),
                color=discord.Color.gold()
            )
            await channel.send(embed=embed)

    @tasks.loop(minutes=1)
    async def daily_reset_task(self):
        now = datetime.now()
        today = date.today()
        global last_reset_day
        if now.hour == 0 and last_reset_day != today:
            await self._reset_guess_game()
            print(f"[{now}] Daily guess game reset completed.")

    @commands.command(name="pray", help = "貓頭鷹抽籤")
    @commands.cooldown(1, 7200, commands.BucketType.user)
    async def pray(self, ctx):
        if ctx.channel.id != CONFIG["pray_channel_id"]:
            return

        result = random.randint(1, 7)
        message, coins, comment, feather_count = FORTUNES[result]

        lucky_number = random.randint(0, 9)
        lucky_color = random.choice(list(COLOR_MAP.keys()))
        embed_color = COLOR_MAP.get(lucky_color, discord.Color.default())

        user_id = str(ctx.author.id)
        user_profile = get_user_data(user_id)
        user_profile["coins"] += coins
        update_user_data(user_id, user_profile)
        
        embed = discord.Embed(
            title = "——貓頭鷹算命抽籤結果——",
            description = f"你抽到的是 **{message}**",
            color = embed_color
        )

        embed.add_field(name = "幸運數字", value = str(lucky_number), inline = True)
        embed.add_field(name = "幸運顏色", value = lucky_color, inline = True)
        embed.add_field(name = "你得到了", value = f"{feather_count} 根羽毛 🪶", inline = False)
        embed.add_field(name = "Mumei 評語", value = comment, inline = False)

        embed.set_thumbnail(url=get_user_avatar(ctx.author))

        image_url = PRAY_IMAGE_MAP.get(message)
        if  image_url:
            embed.set_image(url = image_url)

        embed.set_footer(text = f"{ctx.author.display_name} 的幸運簽", icon_url = get_user_avatar(ctx.author))

        response_message = await ctx.send(embed=embed)
        await response_message.add_reaction("<:MumeiPray:878706690525134878>")

    @pray.error
    async def pray_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            minutes = int(error.retry_after // 60)
            seconds = int(error.retry_after % 60)
            await ctx.send(f"籤紙不夠用啦!<:0_Rainbow:897482889082593300>，等 {minutes} 分 {seconds} 秒再回來吧。")

    @commands.command(name = "slots", help = "拉霸(50羽毛一次)")
    async def slots(self, ctx):
        if ctx.channel.id == CONFIG["slots_channel_id"]:
            user_id = str(ctx.author.id)
            user_profile = get_user_data(user_id)

            if user_profile["coins"] < 50:
                await ctx.send("你都Mei 錢了還賭哦<:0_AOA:897482887341965343>")
                return

            user_profile["coins"] -= 50
            update_user_data(user_id, user_profile)

            result = [random.choice(SLOTS_SYMBOLS) for _ in range(5)]
            await ctx.send(" ".join(result))

            counts = {symbol: result.count(symbol) for symbol in set(result)}
            best_symbol = max(counts, key=counts.get)
            match_count = counts[best_symbol]

            if match_count in SLOTS_WINNINGS:
                win_amount, message_template = SLOTS_WINNINGS[match_count]
                user_profile["coins"] += win_amount
                message = message_template.format(display_name=ctx.author.display_name, best_symbol=best_symbol)
                await ctx.send(f"{message}")
            else:
                await ctx.send("💔 Mei 了, 全Mei 了! 💔")

            update_user_data(user_id, user_profile)

    @commands.command(name="balance", help = "看看自己身上有多少羽毛")
    async def balance(self, ctx):
        user_id = str(ctx.author.id)
        user_profile = get_user_data(user_id)
        balance = user_profile["coins"]

        embed = discord.Embed(
            title = "🪶 羽毛餘額查詢",
            description = f"**{ctx.author.display_name}** 目前擁有 **{balance}** 根羽毛",
            color = discord.Color.from_str("#A0522D")
        )

        embed.set_author(
            name = ctx.author.display_name,
            icon_url = get_user_avatar(ctx.author)
        )
        await ctx.send(embed = embed)

    @commands.command(name="donate", help="投sc")
    async def donate(self, ctx, amount: int):
        if amount <= 0:
            await ctx.send("請輸入一個正確的數量來捐贈。")
            return

        user_id = str(ctx.author.id)
        user_profile = get_user_data(user_id)

        if user_profile["coins"] < amount:
            await ctx.send(f"不! 能! 把! 房! 租! 錢! 用! 來! 投! SC! <:0_Angy:902486572895711242>")
            return

        user_profile["coins"] -= amount
        update_user_data(user_id, user_profile)

        bot_id = str(self.bot.user.id)
        bot_data = get_user_data(bot_id) # Get bot's data
        bot_data["coins"] += amount
        update_user_data(bot_id, bot_data) # Update bot's data

        donation_total = bot_data["coins"]
        await self.bot.change_presence(activity=discord.Game(name=f"{donation_total} 根羽毛"))

        embed = discord.Embed(
            description=(f"感謝你抖內了 {amount} 根羽毛！")
        )
        await ctx.send(embed=embed)

    @commands.command(name="rank", help = "看看排名前十的佬有多富")
    async def rank(self, ctx):
        # user_data is imported directly from data_manager and is the global dict
        sorted_user_data = sorted(user_data.items(), key = lambda x: x[1]["coins"], reverse = True)

        leaderboard_text = f"{'排名':<4} {'成員':<26} {'數量':>6}\n"
        leaderboard_text += "=" * 45 + "\n"

        for rank, (user_id, data) in enumerate(sorted_user_data[:10], start=1):
            user = self.bot.get_user(int(user_id))
            username = user.name if user else "N/A"
            balance = data["coins"]

            leaderboard_text += f"{rank:<4}  {username:<30}  {balance}\n"

        embed = discord.Embed(
            title="🪶貓頭鷹十傑🪶\n 伺服器中羽毛蒐集量前十名",
            description=f"```{leaderboard_text}```",
            color=discord.Color.from_str("#A0522D")

        )
        await ctx.send(embed=embed)

    @commands.command(name = "hunt", help = "獵'人'")
    @commands.cooldown(1, 600, commands.BucketType.user)
    async def hunt(self, ctx):
        if ctx.channel.id != CONFIG["hunt_channel_id"]:
            return
        
        user_id = str(ctx.author.id)
        user_profile = get_user_data(user_id)
        
        result_key = random.randint(1, 24)

        message, coins, comment, feather_count = HUNTING_RESULTS[result_key]

        feathers = feather_count

        if result_key == 24:
           eligible_targets = [
               uid for uid in user_data
               if uid != user_id and user_data[uid].get("coins", 0) > 74
           ]
           if eligible_targets:
               target_id = random.choice(eligible_targets)
               target_user_profile = get_user_data(target_id)
               target_user_profile["coins"] -= 74
               update_user_data(target_id, target_user_profile)

               target_user = self.bot.get_user(int(target_id))
               target_name = target_user.name if target_user else "某個人"

               message = f"你在森林裡遇到了 {target_name},\n 一番文明且友好的交流後, 你拿到了一些羽毛"
               comment = f"你從 {target_name} 那裡蒐集到了一些羽毛！"
               feathers = 74
           else:
               message = "你四處尋找可偷的人，但森林空無一人。沒有找到可以偷取羽毛的對象。"
               comment = "你想偷羽毛，但沒有人可以偷。"
               feathers = 0

        user_profile["coins"] += feathers
        update_user_data(user_id, user_profile)

        embed = discord.Embed(
            title="——狩獵結果——",
        )
        embed.add_field(name="▲事件", value=message, inline=False)
        embed.add_field(name="▲結果", value=comment, inline=False)
        embed.add_field(name="▲你得到了", value=f"{feathers} 根羽毛 🪶", inline=False)
        embed.set_thumbnail(url=get_user_avatar(ctx.author))

        image_url = HUNT_IMAGE_MAP.get(result_key)
        if  image_url:
            embed.set_image(url = image_url)

        embed.set_footer(text = f"{ctx.author.display_name} 的狩獵結果", icon_url = get_user_avatar(ctx.author))
        response_message = await ctx.send(embed = embed)

    @hunt.error
    async def hunt_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            minutes = int(error.retry_after // 60)
            seconds = int(error.retry_after % 60)
            await ctx.send(f"要愛惜大自然!<:0_ThisIsFine:897482889061621760>，等 {minutes} 分 {seconds} 秒再回來吧。")

    @commands.command(name="trade", help="交易, 用法: trade @username 數量")
    async def trade(self, ctx, member: discord.Member, amount: int):
        sender_id = str(ctx.author.id)
        receiver_id = str(member.id)

        sender_profile = get_user_data(sender_id)
        receiver_profile = get_user_data(receiver_id)
        
        if sender_id == receiver_id:
            await ctx.send("你不能跟自己交易！")
            return

        if amount <= 0:
            await ctx.send("請輸入正確的羽毛數量。")
            return
        
        if sender_profile["coins"] < amount:
            await ctx.send("你沒有足夠的羽毛進行交易。")
            return

        sender_profile["coins"] -= amount
        receiver_profile["coins"] += amount
        
        update_user_data(sender_id, sender_profile)
        update_user_data(receiver_id, receiver_profile)

        embed = discord.Embed(
            title="💱 交易完成",
            description=(
                f"{ctx.author.mention} 將 **{amount}** 根羽毛 🪶 "
                f"轉交給了 {member.mention}。"
            ),
            color=discord.Color.green()
        )
        embed.set_footer(text="感謝使用貓頭鷹交易所")

        await ctx.send(embed=embed)

    @commands.command(name="guess", help="1 至 774, 猜一個數字")
    async def guess(self, ctx, number: int):
        global game_active, answer, guess_cooldowns, participants

        if not game_active:
            await ctx.send(f"你遲到了<:0_smug:1063896560854900827>，明天請早！")
            return

        if not (1 <= number <= 774):
            await ctx.send("請輸入 1 到 774 之間的整數。")
            return

        user_id = str(ctx.author.id)
        now = datetime.utcnow()

        last_guess = guess_cooldowns.get(user_id)
        if last_guess and now - last_guess < timedelta(hours=24):
            remaining = timedelta(hours=24) - (now - last_guess)
            hours, remainder = divmod(int(remaining.total_seconds()), 3600)
            minutes = remainder // 60
            await ctx.send(f"⏳ 你已猜過了！請等 {hours} 小時 {minutes} 分鐘後再回來。")
            return

        guess_cooldowns[user_id] = now
        participants.add(user_id)

        correct = number == answer
        user_profile = get_user_data(user_id)

        if correct:
            total_reward = 774
            num_players = len(participants)
            if num_players == 0:
                num_players = 1
            share = total_reward // num_players

            for uid in participants:
                player_profile = get_user_data(uid)
                player_profile["coins"] += share
                update_user_data(uid, player_profile)

            game_active = False
            message = (
                f"🎯 {ctx.author.display_name} 猜中了！答案是 {answer}！\n"
                f"💰 {num_players} 名Hooman 平分了 {total_reward} 根羽毛，每人獲得 {share} 根 🪶！"
            )
            participants.clear()

        else:
            diff = abs(number - answer)
            show_hint = len(participants) % 2 == 0 and diff <= 74

            if show_hint:
                if (number < answer):
                    hint = "太小了"
                else:
                    hint = "太大了"
                message = f"你猜的是 {number}，可惜答案不是。{hint}！"
            else:
                message = f"你猜的是 {number}，可惜答案不是。\n 等下次我心情好會給你提示喲<:0_smug:1063896560854900827>"

        embed = discord.Embed(
        title="🔢 猜數字遊戲",
        description=message,
        color=discord.Color.gold()
        )
        embed.set_footer(text=ctx.author.display_name, icon_url=get_user_avatar(ctx.author))
        await ctx.send(embed=embed)

    @guess.error
    async def guess_error(self, ctx, error):
        if isinstance(error, MissingRequiredArgument):
            await ctx.send("❗ 你忘了輸入數字！請輸入一個 1 到 774 的整數")

    @commands.command(name="guess_reset")
    async def guess_reset(self, ctx: commands.Context) -> None:
        if ctx.author.id != AUTHORIZED_USER_ID:
            await ctx.send("你沒有權限使用此指令")
            return

        await self._reset_guess_game()

    win_streaks = {}

    @commands.command(name="<", help="賭小, 30 一局, 輸的時候結算")
    async def guess_zero(self, ctx):
        await self._play_bet(ctx, 0)

    @commands.command(name=">", help="賭大, 30 一局, 輸的時候結算")
    async def guess_one(self, ctx):
        await self._play_bet(ctx, 1)

    async def _play_bet(self, ctx, guess: int):
        user_id = str(ctx.author.id)
        user_profile = get_user_data(user_id)
        streak = self.win_streaks.get(user_id, 0)

        guess_text = "小" if guess == 0 else "大"
        
        embed = discord.Embed(title="🎲 買大小結果", color=discord.Color.green())
        embed.set_author(name=ctx.author.display_name, icon_url=get_user_avatar(ctx.author))

        if streak == 0:
            if user_profile["coins"] < 30:
                embed.description = "❗你都Mei 錢了還賭哦<:0_AOA:897482887341965343> (需要 30 根羽毛)"
                await ctx.send(embed=embed)
                return
            user_profile["coins"] -= 30
            update_user_data(user_id, user_profile)

        result = random.randint(0, 1)
        result_text = "小" if result == 0 else "大"

        if result == guess:
            self.win_streaks[user_id] = streak + 10
            embed.add_field(name="✅ 結果", value=f"你猜的是 {guess_text}，抽出的結果是 {result_text}，你猜對了！", inline=False)
            embed.add_field(name="🔥 連勝獲得", value=f"{self.win_streaks[user_id]} 根羽毛", inline=False)
        else:
            reward = streak
            self.win_streaks[user_id] = 0
            user_profile["coins"] += reward
            update_user_data(user_id, user_profile)
            embed.color = discord.Color.red()
            embed.add_field(name="❌ 結果", value=f"你猜的是 {guess_text}，抽出的結果是 {result_text}，你猜錯了！", inline=False)
            embed.add_field(name="🎁 獎勵", value=f"你獲得了 {reward} 根羽毛 🪶，遊戲結束。", inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="draw", help="從四個emote 裏面抽出十個結果")
    async def draw(self, ctx):
        draws = []
        choices = list(DRAW_EMOTES.keys())
        weights = list(DRAW_EMOTES.values())

        total_weight = sum(weights)
        if total_weight == 0:
            await ctx.send("Error: All emote chances are 0%!")
            return

        for _ in range(10):
            result = random.choices(choices, weights=weights, k=1)[0]
            draws.append(result)

        embed = discord.Embed(
            title="🎰 抽獎機結果",
            description="".join(draws),
            color=discord.Color.from_str("#A0522D")
        )
        await ctx.send(embed=embed)

    @commands.command(name="shop", help="貓頭鷹寵物店：寵物列表")
    async def shop(self, ctx):
        embed = discord.Embed(
            title="──貓頭鷹寵物店──",
            description=SHOP_PET_LIST,
            color=discord.Color.from_str("#A0522D")
        )
        await ctx.send(embed=embed)

    @commands.command(name="take", help="讓管理員從某位使用者身上扣除羽毛")
    async def take(self, ctx, member: discord.Member, amount: int):
        if ctx.author.id != AUTHORIZED_USER_ID:
            await ctx.send("你沒有權限使用此指令")
            return

        if amount <= 0:
            await ctx.send("請輸入有效的金額。")
            return

        user_id = str(member.id)
        user_profile = get_user_data(user_id)

        print(f"DEBUG: !take command received. Target user: {member.display_name} ({user_id})")
        print(f"DEBUG: Amount to deduct: {amount}")
        print(f"DEBUG: User's coins BEFORE deduction: {user_profile['coins']}")

        if user_profile["coins"] < amount:
            await ctx.send(f"{member.display_name} 沒有足夠的羽毛可供扣除。")
            print(f"DEBUG: Deduction aborted: Insufficient coins ({user_profile['coins']} < {amount}).")
            return

        user_profile["coins"] -= amount
        print(f"DEBUG: User's coins AFTER deduction: {user_profile['coins']}")
        update_user_data(user_id, user_profile)

        await ctx.send(f"✅ **{amount}** 根羽毛已從 **{member.display_name}** 身上扣除。")

    @commands.command(name="give", help="讓管理員給予某位使用者羽毛")
    async def give(self, ctx, member: discord.Member, amount: int):
        if ctx.author.id != AUTHORIZED_USER_ID:
            await ctx.send("你沒有權限使用此指令")
            return

        if amount <= 0:
            await ctx.send("請輸入有效的金額。")
            return

        user_id = str(member.id)
        user_profile = get_user_data(user_id)

        print(f"DEBUG: !give command received. Target user: {member.display_name} ({user_id})")
        print(f"DEBUG: Amount to give: {amount}")
        print(f"DEBUG: User's coins BEFORE addition: {user_profile['coins']}")

        user_profile["coins"] += amount
        print(f"DEBUG: User's coins AFTER addition: {user_profile['coins']}")
        update_user_data(user_id, user_profile)

        await ctx.send(f"✅ 管理員給予了 **{member.display_name}** **{amount}** 根羽毛。")

async def setup(bot):
    await bot.add_cog(Minigames(bot))
