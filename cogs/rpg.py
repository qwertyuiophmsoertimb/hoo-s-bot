import discord
from discord.ext import commands, tasks
import asyncio
import random
from datetime import datetime, timezone

# Import constants and data management functions
from config import (
    INITIAL_PLAYER_PROFILE, XP_TO_NEXT_LEVEL, MAX_PLAYER_LEVEL, UPGRADE_STAT_PER_LEVEL,
    WEAPON_TEMPLATES, ARMOR_TEMPLATES, ACCESSORY_TEMPLATES, ALL_ITEM_TEMPLATES, SHOP_ITEMS,
    BOSS_PHYSICAL_PHASE_ID, BOSS_MAGICAL_PHASE_ID, CRIMSON_BEHEMOTH_ENEMY_ID,
    GAME_EVENTS, GAME_OUTCOMES, ALL_PLAYABLE_EVENT_IDS, SHOP_CHANCE, ITEM_DROP_CHANCE,
    RUN_EVENT_LIMIT, GLOBAL_ITEM_POOL, GAME_EMOJIS,
    PRIVATE_CHANNEL_EMOJI, REQUIRED_REACTIONS_FOR_PRIVATE_CHANNEL, AUTHORIZED_USER_ID
)
from data_manager import get_user_data, update_user_data, save_user_data, user_data # Import user_data directly for bot balance

# Global dictionary to track active RPG sessions
active_questionnaires = {}
private_channel_requests = {} # Needs to be global for on_raw_reaction_add

class RPG(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_for_expired_channels.start() # Start the background task

    def cog_unload(self):
        self.check_for_expired_channels.cancel() # Cancel the task when cog is unloaded

    @tasks.loop(minutes=1)
    async def check_for_expired_channels(self):
        current_time = datetime.now(timezone.utc)
        channels_to_delete = []

        for channel_id, deletion_time in list(self.bot.temporary_text_channels.items()): # Access via bot instance
            if current_time >= deletion_time:
                channels_to_delete.append(channel_id)

        for channel_id in channels_to_delete:
            channel = self.bot.get_channel(channel_id)
            if channel:
                try:
                    if channel_id in active_questionnaires:
                        await self._send_run_summary(channel, active_questionnaires[channel_id])
                        print(f"DEBUG: Sent summary for active game in expiring general temp channel: {channel.name}")

                    await channel.delete()
                    del self.bot.temporary_text_channels[channel_id] # Access via bot instance
                    print(f'Deleted expired temporary text channel: {channel.name} ({channel.id})')
                except discord.Forbidden as e:
                    print(f'Bot does not have permissions to delete channel: {channel.name} ({channel.id}) - {e}')
                except discord.HTTPException as e:
                    print(f'Failed to delete channel {channel.name}: {e}')
            else:
                del self.bot.temporary_text_channels[channel_id] # Access via bot instance
                print(f'Removed tracking for non-existent channel ID: {channel_id}')

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return

        # Handle private channel creation reactions for RPG channels
        if payload.message_id in private_channel_requests:
            request_data = private_channel_requests[payload.message_id]
            if str(payload.emoji) == PRIVATE_CHANNEL_EMOJI:
                guild = self.bot.get_guild(payload.guild_id)
                if not guild: return
                member = guild.get_member(payload.user_id)
                if not member:
                    try:
                        member = await guild.fetch_member(payload.user_id)
                    except (discord.NotFound, discord.Forbidden):
                        return

                if member.id not in request_data['users']:
                    request_data['users'].add(member.id)
                    current_reaction_count = len(request_data['users'])

                    original_channel = self.bot.get_channel(payload.channel_id)
                    if original_channel and current_reaction_count < REQUIRED_REACTIONS_FOR_PRIVATE_CHANNEL:
                        try:
                            embed = discord.Embed(
                                title="頻道創建中",
                                description=f"**{current_reaction_count}/{REQUIRED_REACTIONS_FOR_PRIVATE_CHANNEL}** 位玩家已響應以創建私人頻道 ({member.display_name} 已加入)",
                                color=discord.Color.orange()
                            )
                            await original_channel.send(embed=embed, delete_after=10)
                        except discord.Forbidden as e:
                            print(f"Bot lacks permissions to send progress message in {original_channel.name}: {e}")
                        except discord.HTTPException as e:
                            print(f"Bot failed to send progress message in {original_channel.name}: {e}")

                    if current_reaction_count >= REQUIRED_REACTIONS_FOR_PRIVATE_CHANNEL and not request_data['creation_initiated']:
                        request_data['creation_initiated'] = True
                        original_message_channel = self.bot.get_channel(payload.channel_id)
                        if original_message_channel:
                            try:
                                original_message = await original_message_channel.fetch_message(payload.message_id)
                                await original_message.clear_reactions()
                                embed = discord.Embed(
                                    title="頻道創建中",
                                    description="🎉 頻道創建已完成! 🎉",
                                    color=discord.Color.green()
                                )
                                await original_message.edit(embed=embed)
                            except discord.Forbidden as e:
                                print(f"Failed to clear reactions or edit message: {e}")
                            except discord.HTTPException as e:
                                print(f"Failed to clear reactions or edit message: {e}")

                        reacted_members = []
                        for user_id in request_data['users']:
                            reacted_member = guild.get_member(user_id)
                            if reacted_member:
                                reacted_members.append(reacted_member)
                            else:
                                try:
                                    fetched_member = await guild.fetch_member(user_id)
                                    reacted_members.append(fetched_member)
                                except (discord.NotFound, discord.Forbidden):
                                    pass

                        organizer_id = request_data.get('organizer_id')
                        if organizer_id:
                            organizer_user_data = get_user_data(organizer_id)
                            current_coins = organizer_user_data.get('coins', 0)
                            fee = 100

                            fee_message = ""
                            if fee > 0 and current_coins > 0:
                                actual_deduction = min(fee, current_coins)
                                organizer_user_data['coins'] = max(0, current_coins - actual_deduction)
                                update_user_data(organizer_id, organizer_user_data)
                                organizer_member = guild.get_member(organizer_id)
                                organizer_name = organizer_member.display_name if organizer_member else f"User {organizer_id}"
                                fee_message = f"\n**{organizer_name}** 支付了 **{actual_deduction} 羽毛** 作為組織費"
                                if actual_deduction < fee:
                                    fee_message += " (因羽毛不足未能扣除全部100羽毛)"
                                fee_message += f" 剩餘羽毛: {organizer_user_data['coins']}"
                            else:
                                organizer_member = guild.get_member(organizer_id)
                                organizer_name = organizer_member.display_name if organizer_member else f"User {organizer_id}"
                                fee_message = f"\n**{organizer_name}**的組織費為0羽毛（bug 或羽毛不足）。未收取費用"
                            
                            if original_message_channel:
                                await original_message_channel.send(fee_message, delete_after=15)

                        category = guild.get_channel(request_data['category_id']) if request_data['category_id'] else None
                        await self._create_rpg_channel(
                            guild, reacted_members, request_data['name'], category
                        )
                        if payload.message_id in private_channel_requests:
                            del private_channel_requests[payload.message_id]
            return

        # Handle in-game event reactions
        if payload.channel_id in active_questionnaires:
            game_state = active_questionnaires[payload.channel_id]

            if payload.message_id == game_state['prompt_message_id']:
                guild = self.bot.get_guild(payload.guild_id)
                if not guild: return

                channel = self.bot.get_channel(payload.channel_id)
                if not channel: return

                member = guild.get_member(payload.user_id)
                if not member:
                    try:
                        member = await guild.fetch_member(payload.user_id)
                    except (discord.NotFound, discord.Forbidden):
                        return

                if member and member.id in game_state['participants']:
                    current_event_data = GAME_EVENTS.get(game_state['current_event_id'])
                    valid_emojis = []
                    if current_event_data:
                        if game_state['current_event_id'] == "shop_encounter":
                            for i, item_id in enumerate(game_state['shop_current_items']):
                                valid_emojis.append(GAME_EMOJIS[str(i + 1)])
                            valid_emojis.append(GAME_EMOJIS['X'])
                        else:
                            for option_key in current_event_data['options'].keys():
                                if option_key in GAME_EMOJIS:
                                    valid_emojis.append(GAME_EMOJIS[option_key])
                    
                    if str(payload.emoji) in valid_emojis:
                        async with game_state['lock']:
                            game_state['votes'][member.id] = str(payload.emoji)

                            if len(game_state['votes']) == len(game_state['participants']):
                                await self._process_event_results(payload.channel_id)
                    else:
                        if channel:
                            try:
                                message = await channel.fetch_message(payload.message_id)
                                await message.remove_reaction(payload.emoji, member)
                            except (discord.Forbidden, discord.HTTPException):
                                pass

    async def _create_rpg_channel(self, guild: discord.Guild, members: list[discord.Member], name: str, category: discord.CategoryChannel = None):
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }
        for member in members:
            if member:
                overwrites[member] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        try:
            new_channel = await guild.create_text_channel(
                name=name, category=category, overwrites=overwrites
            )

            member_mentions = ", ".join([member.mention for member in members])
            embed = discord.Embed(
                title=f"歡迎來到 #{new_channel.name}!",
                description=f"{member_mentions}, 你的任務開始了! 進入遺址並找到成員的藏品吧 ",
                color=discord.Color.blue()
            )
            await new_channel.send(embed=embed)
            await self._start_game_session(new_channel, members)

        except discord.Forbidden:
            embed = discord.Embed(
                title="Permission Error", description="I don't have permission to create private channels!", color=discord.Color.red()
            )
            print(f'Bot does not have permissions to create private channels in {guild.name}.')
        except discord.HTTPException as e:
            embed = discord.Embed(
                title="Channel Creation Error", description=f"An error occurred while creating the channel: {e}", color=discord.Color.red()
            )
            print(f'Failed to create private channel in {guild.name}: {e}')

    def _calculate_item_stats(self, item_id: str, item_level: int) -> dict:
        template = ALL_ITEM_TEMPLATES.get(item_id)
        if not template: return {}

        calculated_stats = {}
        base_effect = template.get('base_effect', {})

        for stat, base_value in base_effect.items():
            scaled_value = base_value + (item_level - 1) * UPGRADE_STAT_PER_LEVEL.get(stat, 0)
            calculated_stats[stat] = scaled_value
        
        return calculated_stats

    def _check_level_up(self, user_data_obj: dict) -> dict:
        current_level = user_data_obj.get('level', 1)
        current_xp = user_data_obj['stats'].get('xp', 0)

        while current_level < MAX_PLAYER_LEVEL:
            xp_needed_for_next_level = XP_TO_NEXT_LEVEL.get(current_level, 50 * current_level + 50)
            
            if current_xp >= xp_needed_for_next_level:
                current_xp -= xp_needed_for_next_level
                current_level += 1
                user_data_obj['stat_points'] = user_data_obj.get('stat_points', 0) + 1
                
                user_data_obj['level'] = current_level
                user_data_obj['stats']['xp'] = current_xp
            else:
                break

        if current_level >= MAX_PLAYER_LEVEL:
            user_data_obj['level'] = MAX_PLAYER_LEVEL
            user_data_obj['stats']['xp'] = 0
        
        return user_data_obj

    async def _start_game_session(self, channel: discord.TextChannel, participants: list[discord.Member]):
        players_run_stats = {}
        for member in participants:
            user_data_obj = get_user_data(member.id)
            
            run_stats = {
                'hp': user_data_obj['stats']['hp'],
                'strength': user_data_obj['stats']['strength'],
                'defense': user_data_obj['stats']['defense'],
                'intelligence': user_data_obj['stats']['intelligence'],
                'faith': user_data_obj['stats']['faith'],
                'coins': user_data_obj['coins'],
                'initial_coins_at_run_start': user_data_obj['coins'],
                'xp': 0,
                'kronii_attack_counter': 0
            }

            equipped_weapon_id = user_data_obj.get('equipped_weapon')
            if equipped_weapon_id and equipped_weapon_id in user_data_obj['inventory']:
                weapon_level = user_data_obj['inventory'][equipped_weapon_id]['level']
                weapon_bonuses = self._calculate_item_stats(equipped_weapon_id, weapon_level)
                for stat, bonus in weapon_bonuses.items():
                    run_stats[stat] = run_stats.get(stat, 0) + bonus
            
            equipped_armor_id = user_data_obj.get('equipped_armor')
            if equipped_armor_id and equipped_armor_id in user_data_obj['inventory']:
                armor_level = user_data_obj['inventory'][equipped_armor_id]['level']
                armor_bonuses = self._calculate_item_stats(equipped_armor_id, armor_level) 
                for stat, bonus in armor_bonuses.items():
                    run_stats[stat] = run_stats.get(stat, 0) + bonus

            equipped_accessory_id = user_data_obj.get('equipped_accessory')
            if equipped_accessory_id and equipped_accessory_id in user_data_obj['inventory']:
                run_stats['equipped_accessory'] = equipped_accessory_id

            players_run_stats[member.id] = run_stats

        active_questionnaires[channel.id] = {
            'participants': {member.id for member in participants},
            'players': players_run_stats,
            'current_event_id': "start_adventure",
            'prompt_message_id': None,
            'votes': {},
            'lock': asyncio.Lock(),
            'events_completed': 0,
            'enemy_current_hp': None,
            'enemy_data': None,
            'shop_current_items': [],
            'boss_current_phase': None,
            'boss_phase_transitioned': False,
            'consecutive_tie_count': 0,
            'seen_events': set()
        }
        await self._send_next_event(channel)

    def _get_player_stats_string(self, players_data: dict) -> str:
        stat_lines = []
        for user_id, stats in players_data.items():
            member = self.bot.get_user(user_id)
            name = member.display_name if member else f"User {user_id}"
            
            stat_lines.append(
                f"**{name}**: HP: {stats['hp']}, Str: {stats['strength']}, Def: {stats['defense']}, Int: {stats['intelligence']}, Faith: {stats['faith']}"
            )
        return "\n".join(stat_lines)

    async def _send_next_event(self, channel: discord.TextChannel, force_current: bool = False):
        if channel.id not in active_questionnaires: return

        game_state = active_questionnaires[channel.id]
        
        if all(player_stats['hp'] <= 0 for player_stats in game_state['players'].values()) and game_state['current_event_id'] not in [BOSS_PHYSICAL_PHASE_ID, BOSS_MAGICAL_PHASE_ID, "outcome_run_completed"]:
            game_state['current_event_id'] = "outcome_run_completed"
            await self._send_run_summary(channel, game_state)
            return
        
        next_event_to_send_id = None

        if force_current:
            next_event_to_send_id = game_state['current_event_id']
        elif game_state['events_completed'] == 0 and game_state['current_event_id'] == "start_adventure":
            next_event_to_send_id = "start_adventure"
        elif game_state['enemy_current_hp'] is not None and game_state['enemy_current_hp'] > 0 and game_state['current_event_id'] in [BOSS_PHYSICAL_PHASE_ID, BOSS_MAGICAL_PHASE_ID]:
            next_event_to_send_id = game_state['current_event_id']
        elif game_state['enemy_current_hp'] is not None and game_state['enemy_current_hp'] > 0 and game_state['current_event_id'] in GAME_EVENTS and 'combat_type' in GAME_EVENTS[game_state['current_event_id']]:
            next_event_to_send_id = game_state['current_event_id']
        elif game_state['events_completed'] >= RUN_EVENT_LIMIT and game_state['current_event_id'] not in [BOSS_PHYSICAL_PHASE_ID, BOSS_MAGICAL_PHASE_ID]:
            next_event_to_send_id = BOSS_PHYSICAL_PHASE_ID
            if game_state['enemy_current_hp'] is None or game_state['enemy_data'] is None:
                boss_initial_template = GAME_EVENTS[BOSS_PHYSICAL_PHASE_ID]
                game_state['enemy_current_hp'] = boss_initial_template['enemy_hp']
                game_state['enemy_data'] = {
                    'hp': boss_initial_template['enemy_hp'],
                    'attack_value': boss_initial_template['enemy_attack_value'],
                    'defense': boss_initial_template['enemy_defense'],
                    'intelligence_attack': boss_initial_template['enemy_intelligence_attack']
                }
                game_state['boss_current_phase'] = "physical"
                game_state['boss_phase_transitioned'] = False
        elif random.random() < SHOP_CHANCE and game_state['current_event_id'] != "shop_encounter" and game_state['enemy_current_hp'] is None:
            next_event_to_send_id = "shop_encounter"
        else:
            game_state['enemy_current_hp'] = None
            game_state['enemy_data'] = None

            potential_random_events = [
                eid for eid in ALL_PLAYABLE_EVENT_IDS
                if eid not in [BOSS_PHYSICAL_PHASE_ID, BOSS_MAGICAL_PHASE_ID, CRIMSON_BEHEMOTH_ENEMY_ID, "shop_encounter"]
            ]
            
            weights = []
            possible_choices = []

            for event_id_candidate in potential_random_events:
                if event_id_candidate in game_state['seen_events']:
                    weights.append(0.2)
                else:
                    weights.append(1.0)
                possible_choices.append(event_id_candidate)
            
            if all(event_id_candidate in game_state['seen_events'] for event_id_candidate in potential_random_events):
                game_state['seen_events'].clear()
                weights = [1.0 for _ in potential_random_events]
                print(f"DEBUG: All playable random events seen, resetting seen_events for channel {channel.id}")

            if not possible_choices:
                next_event_to_send_id = random.choice(ALL_PLAYABLE_EVENT_IDS)
            else:
                next_event_to_send_id = random.choices(possible_choices, weights=weights, k=1)[0]
            
        game_state['current_event_id'] = next_event_to_send_id
        event_data = GAME_EVENTS.get(next_event_to_send_id)

        if not event_data:
            embed = discord.Embed(
                title="Game Error: Event Not Found",
                description="發生錯誤，無法加載下一個事件。冒險已結束",
                color=discord.Color.red()
            )
            await channel.send(embed=embed)
            del active_questionnaires[channel.id]
            return

        if next_event_to_send_id in GAME_EVENTS and 'combat_type' in GAME_EVENTS[next_event_to_send_id] and \
           next_event_to_send_id not in [BOSS_PHYSICAL_PHASE_ID, BOSS_MAGICAL_PHASE_ID] and game_state['enemy_current_hp'] is None:
            game_state['enemy_current_hp'] = event_data['enemy_hp']
            game_state['enemy_data'] = {
                'hp': event_data['enemy_hp'],
                'attack_value': event_data['enemy_attack_value'],
                'defense': event_data['enemy_defense']
            }
        
        current_party_stats = self._get_player_stats_string(game_state['players'])

        embed = discord.Embed(
            description=event_data["text"],
            color=discord.Color.blue()
        )

        if game_state['enemy_current_hp'] is not None and game_state['enemy_data'] is not None:
            enemy_name = "敵人"
            if next_event_to_send_id.startswith("abyssal_shadow_lord"):
                enemy_name = "深淵暗影領主"
            elif next_event_to_send_id == CRIMSON_BEHEMOTH_ENEMY_ID:
                enemy_name = "熔岩巨獸"
            embed.description += f"\n**{enemy_name} HP:** {game_state['enemy_current_hp']}/{game_state['enemy_data']['hp']}"

        if 'image_url' in event_data and event_data['image_url']:
            cache_busted_url = f"{event_data['image_url']}?v={int(datetime.now().timestamp())}"
            embed.set_image(url=cache_busted_url)

        options_to_display = {}
        if next_event_to_send_id == "shop_encounter":
            embed.title = "神秘商人! 💰"
            embed.description = "神秘商人貪婪地看著你們身上的羽毛!\n\n"
            
            num_items_to_show = random.randint(3, min(5, len(SHOP_ITEMS)))
            available_shop_items = [item_id for item_id in SHOP_ITEMS.keys() if item_id not in game_state['shop_current_items']]
            
            if len(available_shop_items) < num_items_to_show:
                selected_item_ids = random.sample(list(SHOP_ITEMS.keys()), num_items_to_show)
            else:
                selected_item_ids = random.sample(available_shop_items, num_items_to_show)
            
            game_state['shop_current_items'] = selected_item_ids

            for i, item_id in enumerate(selected_item_ids):
                item = SHOP_ITEMS[item_id]
                option_number_str = str(i + 1)
                options_to_display[option_number_str] = {
                    "text": f"{item['name']} - Cost: {item['cost']} Coins. {item['description']}",
                    "next_id": item_id,
                    "effect": item['effect'],
                    "cost": item['cost']
                }
                embed.add_field(
                    name=f"{GAME_EMOJIS.get(option_number_str, option_number_str)} {option_number_str}",
                    value=f"{item['name']} (Cost: {item['cost']} Coins)",
                    inline=False
                )
            
            options_to_display['X'] = {
                "text": "離開商店 👋",
                "next_id": "random_event_after_shop",
                "effect": {}
            }
            embed.add_field(name=f"{GAME_EMOJIS.get('X', 'X')} X", value="Leave the shop", inline=False)
        else:
            for option_key, option_details in event_data["options"].items():
                embed.add_field(name=f"{GAME_EMOJIS.get(option_key, option_key)} {option_details['text']}", value="\u200B", inline=False)

        embed.add_field(name="\n當前隊伍狀態", value=current_party_stats, inline=False)
        embed.set_footer(text=f"選擇你的回應! (Event {game_state['events_completed'] + 1}/{RUN_EVENT_LIMIT})")

        if next_event_to_send_id not in ["shop_encounter"] and 'combat_type' not in event_data:
            remaining_tries = 2 - game_state['consecutive_tie_count']
            if remaining_tries <= 2:
                embed.set_footer(text=f"選擇你的反應！ (事件 {game_state['events_completed'] + 1}/{RUN_EVENT_LIMIT}) | 平局剩餘嘗試次數: {remaining_tries}")
            else:
                embed.set_footer(text=f"選擇你的反應！ (事件 {game_state['events_completed'] + 1}/{RUN_EVENT_LIMIT})")
        else:
            embed.set_footer(text=f"選擇你的反應！ (事件 {game_state['events_completed'] + 1}/{RUN_EVENT_LIMIT})")

        try:
            prompt_message = await channel.send(embed=embed)
            game_state['prompt_message_id'] = prompt_message.id

            if next_event_to_send_id == "shop_encounter":
                for i in range(len(game_state['shop_current_items'])):
                    await prompt_message.add_reaction(GAME_EMOJIS[str(i + 1)])
                await prompt_message.add_reaction(GAME_EMOJIS['X'])
            else:
                for option_key in event_data["options"].keys():
                    await prompt_message.add_reaction(GAME_EMOJIS.get(option_key, option_key))
            
            game_state['votes'] = {}

        except discord.Forbidden:
            embed = discord.Embed(
                title="Adventure Halted: Permission Error", description="I don't have permission to present the next event here. Please check my permissions.", color=discord.Color.red()
            )
            await channel.send(embed=embed)
        except discord.HTTPException as e:
            embed = discord.Embed(
                title="Failed to Send Event", description=f"An error occurred while sending the event: {e}", color=discord.Color.red()
            )
            print(f"Failed to send event: {e}")

    async def _process_combat_round(self, channel: discord.TextChannel, game_state: dict, chosen_option_key: str) -> tuple[str, bool]:
        result_description = ""
        combat_ended = False

        current_event_id = game_state['current_event_id']
        current_enemy_data = game_state['enemy_data']
        enemy_current_hp = game_state['enemy_current_hp']
        current_event_template = GAME_EVENTS[current_event_id]
        
        is_boss_fight = current_event_id.startswith("abyssal_shadow_lord")

        rps_moves = ["rock", "paper", "scissors"]
        enemy_move = random.choice(rps_moves)
        player_move_map = {"1": "rock", "2": "paper", "3": "scissors"}
        player_chosen_rps_move = player_move_map.get(chosen_option_key)

        rps_multiplier = 0.0
        rps_outcome_text = ""
        if player_chosen_rps_move == enemy_move:
            rps_multiplier = 0.5
            rps_outcome_text = "平局! 攻擊打在了護甲上"
        elif (player_chosen_rps_move == "rock" and enemy_move == "scissors") or \
             (player_chosen_rps_move == "paper" and enemy_move == "rock") or \
             (player_chosen_rps_move == "scissors" and enemy_move == "paper"):
            rps_multiplier = 1.0
            rps_outcome_text = "你們贏了! 攻擊造成了完整傷害!"
        else:
            rps_multiplier = 0.0
            rps_outcome_text = "你們輸了! 攻擊被閃避掉了"
        
        enemy_display_name = "敵人"
        if current_event_id.startswith("abyssal_shadow_lord"):
            enemy_display_name = "深淵暗影領主"
        elif current_event_id == CRIMSON_BEHEMOTH_ENEMY_ID:
            enemy_display_name = "熔岩巨獸"

        result_description += f"{enemy_display_name} 以 **{enemy_move.capitalize()}**回擊!\n"
        result_description += f"你的隊伍選擇了 **{player_chosen_rps_move.capitalize()}**! {rps_outcome_text}\n\n"
        
        if is_boss_fight and game_state['boss_current_phase'] == "physical" and not game_state['boss_phase_transitioned'] and enemy_current_hp <= (current_enemy_data['hp'] * 0.5):
            game_state['boss_current_phase'] = "magical"
            game_state['boss_phase_transitioned'] = True
            game_state['current_event_id'] = BOSS_MAGICAL_PHASE_ID
            current_event_template = GAME_EVENTS[BOSS_MAGICAL_PHASE_ID]
            
            result_description += "\n**THE ABYSSAL SHADOW LORD SHIFTS!** 它的裝甲剝落，內部的黑魔法被完全解放!\n"
            current_enemy_data['attack_value'] = current_event_template['enemy_attack_value']
            current_enemy_data['defense'] = current_event_template['enemy_defense']
            current_enemy_data['intelligence_attack'] = current_event_template.get('enemy_intelligence_attack', 0)
            game_state['enemy_data'] = current_enemy_data

        damage_taken_summary = []
        
        enemy_damage_dealt_base = current_enemy_data['attack_value']
        
        if current_event_template['combat_type'] == "physical":
            result_description += f"{enemy_display_name} 揮出了 **P = mv**!\n"
            for user_id_int in game_state['participants']:
                player_run_stats = game_state['players'][user_id_int]
                if player_run_stats['hp'] <= 0: continue
                
                damage_taken = max(1, enemy_damage_dealt_base - player_run_stats['defense'])
                player_run_stats['hp'] -= damage_taken
                player_run_stats['hp'] = max(0, player_run_stats['hp'])
                damage_taken_summary.append(f"{self.bot.get_user(user_id_int).display_name} 受到了 {damage_taken} 物理傷害 (HP: {player_run_stats['hp']})")
        elif current_event_template['combat_type'] == "magical":
            result_description += f"{enemy_display_name} 施放了 **V = IR**!\n"
            
            if is_boss_fight and random.random() < current_event_template.get('special_attack_chance', 0):
                aoe_damage_base = current_event_template['enemy_intelligence_attack']
                aoe_damage_text = "N = N0 * 2^(t/T)"
                result_description += f"領主蓄力施放了 **{aoe_damage_text}**! 一道黑色的衝擊波衝向了隊伍!\n"
                for user_id_int in game_state['participants']:
                    player_run_stats = game_state['players'][user_id_int]
                    if player_run_stats['hp'] <= 0: continue
                    
                    damage_taken = aoe_damage_base
                    damage_taken = max(50, damage_taken)
                    player_run_stats['hp'] -= damage_taken
                    player_run_stats['hp'] = max(0, player_run_stats['hp'])
                    damage_taken_summary.append(f"{self.bot.get_user(user_id_int).display_name} 受到了 {damage_taken} 魔法傷害 (HP: {player_run_stats['hp']})")
            else:
                for user_id_int in game_state['participants']:
                    player_run_stats = game_state['players'][user_id_int]
                    if player_run_stats['hp'] <= 0: continue

                    damage_taken = enemy_damage_dealt_base
                    player_run_stats['hp'] -= damage_taken
                    player_run_stats['hp'] = max(0, player_run_stats['hp'])
                    damage_taken_summary.append(f"{self.bot.get_user(user_id_int).display_name} 受到了 {damage_taken} 魔法傷害 (HP: {player_run_stats['hp']})")

        result_description += "\n" + "\n".join(damage_taken_summary) + "\n\n"

        if all(player_stats['hp'] <= 0 for player_stats in game_state['players'].values()):
            result_description += "\n**💀 你們的隊伍全滅! 艾路owl 會送你們回互助會 💀**\n"
            combat_ended = True
            return result_description, combat_ended
        
        total_damage_to_enemy_this_round = 0
        detailed_combat_log = []
        
        detailed_combat_log.append(f"本輪傷害類型: **{current_event_template['combat_type'].capitalize()}**.")
        detailed_combat_log.append(f"{enemy_display_name} 防禦: **{current_enemy_data['defense']}**.")
        detailed_combat_log.append(f"RPS 攻擊結果: **{rps_outcome_text}** (傷害判定: {rps_multiplier:.1f})")

        for user_id_int in game_state['participants']:
            player_run_stats = game_state['players'][user_id_int]
            if player_run_stats['hp'] <= 0:
                continue

            user_data_obj = get_user_data(user_id_int)
            equipped_weapon_id = user_data_obj.get('equipped_weapon')
            wielder_name = self.bot.get_user(user_id_int).display_name if self.bot.get_user(user_id_int) else f"User {user_id_int}"

            weapon_template = ALL_ITEM_TEMPLATES.get(equipped_weapon_id)
            
            player_raw_physical_damage = 0
            player_raw_magical_damage = 0
            player_healed_for = 0
            
            detailed_combat_log.append(f"\n--- {wielder_name}的回合 (武器: {weapon_template['name'] if weapon_template else 'None'}) ---")

            equipped_accessory_id = user_data_obj.get('equipped_accessory')
            if equipped_accessory_id == "auto_healing_amulet":
                healing_amount = ACCESSORY_TEMPLATES["auto_healing_amulet"]["special_skill"]["effect"]["hp_restore"]
                target_max_hp = user_data_obj['stats']['hp']
                healed_for = min(target_max_hp - player_run_stats['hp'], healing_amount)
                if healed_for > 0:
                    player_run_stats['hp'] = min(target_max_hp, player_run_stats['hp'] + healing_amount)
                    detailed_combat_log.append(f"💚✨ **{wielder_name}的自療護符** 恢復了{healed_for} HP! (Current HP: {player_run_stats['hp']}).")
                else:
                    detailed_combat_log.append(f"💚✨ **{wielder_name}的自療護符** 嘗試治療，但{wielder_name}生命值已滿")

            if equipped_weapon_id:
                if equipped_weapon_id == "sword":
                    player_raw_physical_damage = player_run_stats['strength']
                    detailed_combat_log.append(f"🗡️ **{wielder_name} 的長鋏** 揮出了斬擊!")
                elif equipped_weapon_id == "staff":
                    player_raw_magical_damage = player_run_stats['intelligence']
                    detailed_combat_log.append(f"🪄 **{wielder_name} 的髡枝** 施放了法術!")
                elif equipped_weapon_id == "kronii":
                    kronii_template = WEAPON_TEMPLATES["kronii"]
                    
                    player_run_stats['kronii_attack_counter'] += 1

                    if (player_run_stats['kronii_attack_counter'] % 12) == 0:
                        mixed_hit_spec = kronii_template['round_based_damage']['mixed_hit']
                        player_raw_physical_damage = player_run_stats['strength'] * mixed_hit_spec['strength_multiplier']
                        player_raw_magical_damage = player_run_stats['intelligence'] * mixed_hit_spec['intelligence_multiplier']
                        detailed_combat_log.append(f"**{wielder_name} 的時分** 在第12次攻擊時釋放出強大的斬擊!")
                    else:
                        physical_multiplier_normal = kronii_template['round_based_damage']['physical_multiplier_normal']
                        player_raw_physical_damage = player_run_stats['strength'] * physical_multiplier_normal
                        detailed_combat_log.append(f"**{wielder_name} 的時分** 斬出物理攻擊 (攻擊循環: {player_run_stats['kronii_attack_counter'] % 12} of 11).")
                elif equipped_weapon_id == "fauna":
                    if rps_multiplier > 0:
                        healing_amount = int(player_run_stats['faith'] * WEAPON_TEMPLATES["fauna"]["healing_multiplier"] * rps_multiplier) 
                        
                        for member_id in game_state['participants']:
                            target_player_run_stats = game_state['players'][member_id]
                            if target_player_run_stats['hp'] > 0:
                                target_user_data_obj = get_user_data(member_id)
                                target_max_hp = target_user_data_obj['stats']['hp']
                                healed_for_target = min(target_max_hp - target_player_run_stats['hp'], healing_amount)
                                if healed_for_target > 0:
                                    target_player_run_stats['hp'] = min(target_max_hp, target_player_run_stats['hp'] + healing_amount)
                                    player_healed_for += healed_for_target
                                    target_member_name = self.bot.get_user(member_id).display_name if self.bot.get_user(member_id) else f"User {member_id}"
                                    detailed_combat_log.append(f"**{target_member_name}** 被 **{wielder_name}的 淬靈金果** 治療了 {healed_for_target} 生命值 (總生命值: {target_player_run_stats['hp']})。")
                                else:
                                    target_member_name = self.bot.get_user(member_id).display_name if self.bot.get_user(member_id) else f"User {member_id}"
                                    detailed_combat_log.append(f"**{target_member_name}** 嘗試治療，但生命值已滿。")
                    else:
                        detailed_combat_log.append(f"**{wielder_name} 的淬靈金果** 因RPS結果無法治療。")
                elif equipped_weapon_id == "moom":
                    dagger_template = WEAPON_TEMPLATES["moom"]
                    num_hits = 1
                    for _ in range(dagger_template.get("max_extra_hits", 0)):
                        if random.random() < dagger_template.get("multi_hit_chance", 0):
                            num_hits += 1
                    player_raw_physical_damage = player_run_stats['strength'] * num_hits
                    detailed_combat_log.append(f"**{wielder_name} 的文明的進程** 攻擊了 {num_hits} 次!")
                elif equipped_weapon_id == "bae":
                    action_weights = WEAPON_TEMPLATES["bae"]["random_action_chance"]
                    actions = list(action_weights.keys())
                    weights = list(action_weights.values())
                    chosen_action = random.choices(actions, weights=weights, k=1)[0]

                    if chosen_action == 'physical_damage':
                        player_raw_physical_damage = player_run_stats['strength']
                        detailed_combat_log.append(f"**{wielder_name} 的子骰** 發出物理攻擊！")
                    elif chosen_action == 'magical_damage':
                        player_raw_magical_damage = player_run_stats['intelligence']
                        detailed_combat_log.append(f"**{wielder_name} 的子骰** 發出魔法衝擊!")
                    elif chosen_action == 'healing':
                        if rps_multiplier > 0:
                            healing_amount = int((player_run_stats['faith'] + 1) * rps_multiplier)
                            target_max_hp = user_data_obj['stats']['hp']
                            healed_for = min(target_max_hp - player_run_stats['hp'], healing_amount)
                            player_run_stats['hp'] = min(target_max_hp, player_run_stats['hp'] + healing_amount)
                            player_healed_for += healed_for
                            if healed_for > 0:
                                detailed_combat_log.append(f"**{wielder_name} 的子骰** 發出治療能量，恢復了 {healed_for} HP (總生命值: {player_run_stats['hp']}).")
                            else:
                                detailed_combat_log.append(f"**{wielder_name} 的子骰** 嘗試治療，但生命值已滿。")
                        else:
                            detailed_combat_log.append(f"**{wielder_name} 的子骰** 因RPS結果無法治療")
                elif equipped_weapon_id == "irys":
                    player_raw_magical_damage = player_run_stats['intelligence']
                    detailed_combat_log.append(f"**{wielder_name} 的拿非利水晶** 施放了魔法攻擊！")
                    if rps_multiplier > 0:
                        healing_amount = int(player_run_stats['faith'] * WEAPON_TEMPLATES["irys"]["healing_multiplier"] * rps_multiplier)
                        
                        target_max_hp = user_data_obj['stats']['hp']
                        healed_for = min(target_max_hp - player_run_stats['hp'], healing_amount)
                        player_run_stats['hp'] = min(target_max_hp, player_run_stats['hp'] + healing_amount)
                        player_healed_for += healed_for
                        if healed_for > 0:
                            detailed_combat_log.append(f"並恢復了 {healed_for} 生命值 (總生命值: {player_run_stats['hp']})。")
                        else:
                            detailed_combat_log.append(f"並嘗試治療，但生命值已滿。")
                    else:
                        detailed_combat_log.append(f"但因RPS結果無法治療。")
                elif equipped_weapon_id == "sana":
                    player_raw_physical_damage = player_run_stats['strength']
                    player_max_hp_from_profile = user_data_obj['stats']['hp']
                    deduced_hp = player_max_hp_from_profile - player_run_stats['hp']
                    if deduced_hp > 0:
                        axe_template = WEAPON_TEMPLATES["sana"]
                        bonus_damage = deduced_hp * axe_template.get("deduced_hp_damage_multiplier", 0)
                        player_raw_physical_damage += bonus_damage
                        detailed_combat_log.append(f"**{wielder_name}的星球力場** 從失去的生命值中造成額外傷害！")
                    else:
                        detailed_combat_log.append(f"**{wielder_name}的星球力場** 未造成額外傷害")
                elif equipped_weapon_id == "voidwalkers_edge":
                    void_template = WEAPON_TEMPLATES["voidwalkers_edge"]
                    damage_multiplier_per_hp_lost_percent = void_template['special_attack']['damage_multiplier_per_hp_lost_percent']
                    enemy_total_hp = current_enemy_data['hp']
                    enemy_hp_lost_percent = ((enemy_total_hp - game_state['enemy_current_hp']) / enemy_total_hp) * 100
                    bonus_damage_multiplier = enemy_hp_lost_percent * damage_multiplier_per_hp_lost_percent

                    player_raw_physical_damage = player_run_stats['strength'] * (1 + bonus_damage_multiplier)
                    player_raw_magical_damage = player_run_stats['intelligence'] * (1 + bonus_damage_multiplier)
                    detailed_combat_log.append(f"**{wielder_name}'s Voidwalker's Edge** scales with enemy HP lost!")
            else:
                player_raw_physical_damage = player_run_stats['strength']
                player_raw_magical_damage = player_run_stats['intelligence']
                detailed_combat_log.append(f"**{wielder_name}** 沒有裝備武器，依靠基本攻擊")

            final_physical_damage = max(0, int(player_raw_physical_damage * rps_multiplier) - current_enemy_data['defense'])
            final_magical_damage = int(player_raw_magical_damage * rps_multiplier)

            player_contributed_damage_this_player = final_physical_damage + final_magical_damage
            total_damage_to_enemy_this_round += player_contributed_damage_this_player
            
            detailed_combat_log.append(f"**{wielder_name}** 造成了 **{player_contributed_damage_this_player}** 傷害 ({final_physical_damage} 物理, {final_magical_damage} 魔法) 以及治療了 {player_healed_for} HP.")

        game_state['enemy_current_hp'] = max(0, game_state['enemy_current_hp'] - total_damage_to_enemy_this_round)

        if detailed_combat_log:
            result_description += "\n**Combat Log:**\n" + "\n".join(detailed_combat_log) + "\n"

        if game_state['enemy_current_hp'] <= 0:
            enemy_name_display = "深淵暗影領主" if is_boss_fight else "敵人"
            result_description += f"\n**🌟 {enemy_name_display} 已被擊敗! 🌟**\n"
            for user_id_int in game_state['participants']:
                player_run_stats = game_state['players'][user_id_int]
                if is_boss_fight:
                    player_run_stats['coins'] += 10
                    player_run_stats['xp'] += 100
                    
                    user_data_obj = get_user_data(user_id_int)
                    if "auto_healing_amulet" not in user_data_obj['inventory']:
                        user_data_obj['inventory']["auto_healing_amulet"] = {"level": 1}
                        update_user_data(user_id_int, user_data_obj)
                        result_description += f"**{self.bot.get_user(user_id_int).display_name}** 撿到了: **{ALL_ITEM_TEMPLATES['auto_healing_amulet']['name']}**!\n"
                    else:
                        player_run_stats['coins'] += 5
                        result_description += f"**{self.bot.get_user(user_id_int).display_name}** 已經擁有 **自療護符**, (+5 羽毛)\n"
                else:
                    player_run_stats['coins'] += random.randint(10, 30)
                    player_run_stats['xp'] += random.randint(20, 50)
                    if random.random() < ITEM_DROP_CHANCE and GLOBAL_ITEM_POOL:
                        dropped_item_id = random.choice(GLOBAL_ITEM_POOL)
                        dropped_item_template = ALL_ITEM_TEMPLATES[dropped_item_id]
                        user_data_obj = get_user_data(user_id_int)
                        if dropped_item_id not in user_data_obj['inventory']:
                            user_data_obj['inventory'][dropped_item_id] = {"level": 1}
                            update_user_data(user_id_int, user_data_obj)
                            result_description += f"**{self.bot.get_user(user_id_int).display_name}** 撿到了: **{dropped_item_template['name']}**!\n"
                        else:
                            result_description += f"**{self.bot.get_user(user_id_int).display_name}** 撿到了: **{dropped_item_template['name']}**, 但他已經有了 (+1 羽毛)\n"
                            player_run_stats['coins'] += 1
            save_user_data()

            game_state['enemy_current_hp'] = None
            game_state['enemy_data'] = None
            game_state['shop_current_items'] = []
            game_state['events_completed'] += 1
            game_state['consecutive_tie_count'] = 0

            if is_boss_fight:
                combat_ended = True
                game_state['boss_current_phase'] = None
                game_state['boss_phase_transitioned'] = False
            else:
                combat_ended = False

        else:
            result_description += f"\n_The {enemy_display_name} 剩餘 **{game_state['enemy_current_hp']} HP** 請自求多福!_\n"
            combat_ended = False

        return result_description, combat_ended

    async def _process_event_results(self, channel_id: int):
        if channel_id not in active_questionnaires: return

        game_state = active_questionnaires[channel_id]
        channel = self.bot.get_channel(channel_id)
        if not channel: return

        votes = game_state['votes']
        current_event_id = game_state['current_event_id']
        event_data = GAME_EVENTS.get(current_event_id)

        try:
            previous_message = await channel.fetch_message(game_state['prompt_message_id'])
            await previous_message.clear_reactions()
        except (discord.Forbidden, discord.HTTPException):
            pass

        if not event_data:
            embed = discord.Embed(
                title="Game Error: Path Vanished", description="An internal error occurred with the adventure. Ending it prematurely.", color=discord.Color.red()
            )
            await channel.send(embed=embed)
            del active_questionnaires[channel.id]
            return

        vote_counts = {emoji_code: 0 for emoji_code in GAME_EMOJIS.values()}
        for user_id, emoji_reacted_with in votes.items():
            if emoji_reacted_with in vote_counts:
                vote_counts[emoji_reacted_with] += 1

        relevant_emojis = []
        if current_event_id == "shop_encounter":
            for i in range(len(game_state['shop_current_items'])):
                relevant_emojis.append(GAME_EMOJIS[str(i + 1)])
            relevant_emojis.append(GAME_EMOJIS['X'])
        else:
            for option_key in event_data['options'].keys():
                if option_key in GAME_EMOJIS:
                    relevant_emojis.append(GAME_EMOJIS[option_key])

        max_votes = -1
        winning_emojis = []
        for emoji_code, count in vote_counts.items():
            if emoji_code not in relevant_emojis: continue

            if count > max_votes:
                max_votes = count
                winning_emojis = [emoji_code]
            elif count == max_votes:
                winning_emojis.append(emoji_code)

        result_description = ""
        chosen_option_key = None
        
        if len(winning_emojis) == 1:
            winning_emoji = winning_emojis[0]
            for key, emoji_val in GAME_EMOJIS.items():
                if emoji_val == winning_emoji:
                    chosen_option_key = key
                    break

            game_state['consecutive_tie_count'] = 0
            
            if current_event_id == "shop_encounter":
                if chosen_option_key == 'X':
                    result_description += "隊伍選擇離開商人，繼續他們的旅程"
                    game_state['events_completed'] += 1
                    game_state['shop_current_items'] = []
                    await channel.send(embed=discord.Embed(description=result_description, color=discord.Color.blue()))
                    await self._send_next_event(channel)
                    return
                else:
                    try:
                        item_index = int(chosen_option_key) - 1
                        item_id = game_state['shop_current_items'][item_index]
                    except (ValueError, IndexError):
                        item_id = None

                    item = SHOP_ITEMS.get(item_id)
                    if item:
                        successful_purchasers = []
                        failed_purchasers = []
                        
                        for user_id_int in game_state['participants']:
                            member = self.bot.get_user(user_id_int)
                            member_name = member.display_name if member else f"User {user_id_int}"
                            
                            user_data_obj = get_user_data(user_id_int)
                            player_run_stats = game_state['players'][user_id_int]

                            if user_data_obj['coins'] >= item['cost']:
                                user_data_obj['coins'] -= item['cost']
                                
                                for stat, change in item['effect'].items():
                                    if stat in ['hp', 'strength', 'defense', 'intelligence', 'faith']:
                                        player_run_stats[stat] = player_run_stats.get(stat, 0) + change
                                    elif stat in ['coins', 'xp']:
                                        user_data_obj[stat] = user_data_obj.get(stat, 0) + change
                                        player_run_stats[stat] = player_run_stats.get(stat, 0) + change

                                update_user_data(user_id_int, user_data_obj)
                                successful_purchasers.append(member_name)
                            else:
                                failed_purchasers.append(member_name)
                        
                        if successful_purchasers:
                            result_description += f"**{' and '.join(successful_purchasers)}** 已購入 **{item['name']}**!\n"
                            result_description += f"物品的臨時效果已被觸發\n"
                        if failed_purchasers:
                            result_description += f"**{' and '.join(failed_purchasers)}** 沒有足夠羽毛 (需要{item['cost']}) 而無法購買  **{item['name']}**\n"

                        if item_id in game_state['shop_current_items']:
                            game_state['shop_current_items'].remove(item_id)

                        save_user_data()
                        result_description += "\n To be continue..."
                        await channel.send(embed=discord.Embed(description=result_description, color=discord.Color.blue()))
                        await self._send_next_event(channel)
                        return
                    else:
                        result_description += f"Invalid shop item selected"
                        await channel.send(embed=discord.Embed(description=result_description, color=discord.Color.red()))
                        await self._send_next_event(channel)
                        return
            elif 'combat_type' in event_data:
                round_description, combat_ended = await self._process_combat_round(channel, game_state, chosen_option_key)
                result_description += round_description

                await channel.send(embed=discord.Embed(description=result_description, color=discord.Color.dark_red() if not combat_ended else discord.Color.gold()))

                if combat_ended:
                    await self._send_run_summary(channel, game_state)
                else:
                    await self._send_next_event(channel)
                return
            else:
                result_description += f"你選擇了'{event_data['options'][chosen_option_key]['text']}'. "
                
                if event_data['options'][chosen_option_key].get('effect'):
                    effect_changes_display = []
                    for user_id_int in game_state['participants']:
                        player_run_stats = game_state['players'][user_id_int]
                        if player_run_stats['hp'] > 0:
                            for stat, change in event_data['options'][chosen_option_key]['effect'].items():
                                if stat in ['coins', 'xp']:
                                    user_data_obj = get_user_data(user_id_int)
                                    user_data_obj[stat] = user_data_obj.get(stat, 0) + change
                                    update_user_data(user_id_int, user_data_obj)
                                    player_run_stats[stat] = player_run_stats.get(stat, 0) + change
                                else:
                                    player_run_stats[stat] = player_run_stats.get(stat, 0) + change
                                effect_changes_display.append(f"{'+' if change >= 0 else ''}{change} {stat.capitalize()}")
                    if effect_changes_display:
                        result_description += f"**效果:** {', '.join(sorted(list(set(effect_changes_display))))} (所有成員都可以享有效果)\n"
                    else:
                        result_description += "無其他效果"
                    save_user_data()
                
                game_state['events_completed'] += 1
                game_state['shop_current_items'] = []
                
                if event_data['options'][chosen_option_key].get('next_id') and event_data['options'][chosen_option_key].get('next_id') != "random_event":
                    game_state['current_event_id'] = event_data['options'][chosen_option_key].get('next_id')
                    await channel.send(embed=discord.Embed(description=result_description, color=discord.Color.blue()))
                    await self._send_next_event(channel, force_current=True)
                else:
                    game_state['current_event_id'] = random.choice(ALL_PLAYABLE_EVENT_IDS)
                    await channel.send(embed=discord.Embed(description=result_description, color=discord.Color.blue()))
                    await self._send_next_event(channel)
                return
        else:
            game_state['consecutive_tie_count'] += 1
            
            if game_state['consecutive_tie_count'] >= 2:
                result_description += "隊伍因意見不合發生爭執 一番文明友善且和平的溝通後 全員陣亡 冒險結束！\n"
                await channel.send(embed=discord.Embed(description=result_description, color=discord.Color.dark_red()))
                await self._send_run_summary(channel, game_state)
                return
            else:
                remaining_ties = 2 - game_state['consecutive_tie_count']
                result_description += f"**平局！** 隊伍陷入選擇困難! 或者有人手賤按錯!\n 隨便啦 反正你們還有{remaining_ties}次機會\n"
                
                if current_event_id == "shop_encounter":
                    result_description += "請重新投票或選擇離開商店。"
                elif 'combat_type' in event_data:
                    result_description += f"_{'深淵暗影領主' if current_event_id.startswith('abyssal_shadow_lord') else '敵人'} 仍有 **{game_state['enemy_current_hp']} 生命值** 剩餘。請自求多福！_\n"
                else:
                    result_description += "事件將重新開始，請再次投票！\n"
                
                await channel.send(embed=discord.Embed(description=result_description, color=discord.Color.dark_grey()))
                await self._send_next_event(channel, force_current=True)
                return

        await self._send_run_summary(channel, game_state)

    async def _send_run_summary(self, channel: discord.TextChannel, game_state: dict):
        summary_description = f"**冒險總結!**\n\n"
        
        for user_id_int, player_run_stats in game_state['players'].items():
            user_id_str = str(user_id_int)
            member = self.bot.get_user(user_id_int)
            name = member.display_name if member else f"User {user_id_int}"

            user_data_obj = get_user_data(user_id_int)
            user_data_obj['stats']['xp'] = user_data_obj['stats'].get('xp', 0) + player_run_stats.get('xp', 0)
            user_data_obj['coins'] = player_run_stats['coins']
            user_data_obj = self._check_level_up(user_data_obj)
            user_data_obj['physical_damage_tracker'] = 0
            update_user_data(user_id_int, user_data_obj)

            summary_description += f"**{name}**: 獲得了 **{player_run_stats.get('xp', 0)}** XP\n"
            summary_description += f"   *現時等級*: Level: {user_data_obj['level']}\n"
        save_user_data()
            
        summary_embed = discord.Embed(
            title="冒險結束",
            description=summary_description,
            color=discord.Color.gold()
        )
        summary_embed.set_footer(text=f"你的進程已被儲存 此頻道將在30秒後刪除")
        await channel.send(embed=summary_embed)
        
        if channel.id in active_questionnaires:
            del active_questionnaires[channel.id] 

        await asyncio.sleep(30)
        try:
            if channel.id in self.bot.temporary_text_channels:
                del self.bot.temporary_text_channels[channel.id]
            await channel.delete()
            print(f"Deleted RPG channel: {channel.name} ({channel.id}) after game conclusion.")
        except discord.Forbidden:
            print(f"Bot lacks permissions to delete RPG channel: {channel.name} ({channel.id}).")
        except discord.HTTPException as e:
            print(f"Failed to delete RPG channel {channel.name} ({channel.id}): {e}")

    @commands.command(name='pg', help='RPG 用法: owl pg')
    async def rpg(self, ctx, name: str = "rpg-adventure", category_id: int = None):
        if not ctx.guild:
            await ctx.send("This command can only be used in a server.")
            return

        category = None
        if category_id:
            category = self.bot.get_channel(category_id)
            if not isinstance(category, discord.CategoryChannel):
                await ctx.send(f"❌ Category ID `{category_id}` is not a valid category. Please provide a valid category ID or omit it.")
                return
        elif ctx.channel.category:
            category = ctx.channel.category
        elif ctx.guild.categories:
            category = ctx.guild.categories[0]

        target_parent = category if category else ctx.guild
        if not target_parent.permissions_for(ctx.guild.me).manage_channels:
            await ctx.send("I need 'Manage Channels' permission to create private channels in that category (or this server). Please grant me this permission.")
            return

        embed = discord.Embed(
            title=f"RPG 組隊請求: '{name}'",
            description=f"**{ctx.author.display_name}** 正在建立冒險隊伍! "
                        f"回應 {PRIVATE_CHANNEL_EMOJI} 以加入隊伍 "
                        f"仍需 **{REQUIRED_REACTIONS_FOR_PRIVATE_CHANNEL}** 隊員才可以出發!",
            color=discord.Color.orange()
        )
        request_message = await ctx.send(embed=embed)
        await request_message.add_reaction(PRIVATE_CHANNEL_EMOJI)

        private_channel_requests[request_message.id] = {
            'organizer_id': ctx.author.id,
            'name': name,
            'category_id': category.id if category else None,
            'users': {ctx.author.id},
            'creation_initiated': False
        }

    @commands.command(name='profile', help='View your profile and stats.')
    async def profile(self, ctx):
        user_id = ctx.author.id
        user_profile = get_user_data(user_id)

        equipped_weapon_id = user_profile.get("equipped_weapon")
        equipped_armor_id = user_profile.get("equipped_armor")
        equipped_accessory_id = user_profile.get("equipped_accessory")

        weapon_display = "None"
        weapon_stats_display = ""
        if equipped_weapon_id and equipped_weapon_id in user_profile['inventory']:
            weapon_data = user_profile['inventory'][equipped_weapon_id]
            weapon_level = weapon_data.get('level', 1)
            weapon_template = ALL_ITEM_TEMPLATES.get(equipped_weapon_id)
            if weapon_template:
                weapon_display = f"{weapon_template['name']} (Lvl {weapon_level})"
                calculated_stats = self._calculate_item_stats(equipped_weapon_id, weapon_level)
                if calculated_stats:
                    weapon_stats_display = ", ".join([f"{s.capitalize()}: {v}" for s, v in calculated_stats.items()])
        
        armor_display = "None"
        armor_stats_display = ""
        if equipped_armor_id and equipped_armor_id in user_profile['inventory']:
            armor_data = user_profile['inventory'][equipped_armor_id]
            armor_level = armor_data.get('level', 1)
            armor_template = ALL_ITEM_TEMPLATES.get(equipped_armor_id)
            if armor_template:
                armor_display = f"{armor_template['name']} (Lvl {armor_level})"
                calculated_stats = self._calculate_item_stats(equipped_armor_id, armor_level)
                if calculated_stats:
                    armor_stats_display = ", ".join([f"{s.capitalize()}: {v}" for s, v in calculated_stats.items()])

        accessory_display = "None"
        accessory_skill_display = ""
        if equipped_accessory_id and equipped_accessory_id in user_profile['inventory']:
            accessory_template = ALL_ITEM_TEMPLATES.get(equipped_accessory_id)
            if accessory_template:
                accessory_display = accessory_template['name']
                if accessory_template.get('special_skill'):
                    accessory_skill_display = f"Skill: {accessory_template['special_skill']['name']} - {accessory_template['special_skill']['description']}"

        xp_needed_for_next_level = XP_TO_NEXT_LEVEL.get(user_profile['level'], 'N/A')
        current_xp = user_profile['stats'].get('xp', 0)
        xp_to_go = xp_needed_for_next_level - current_xp if isinstance(xp_needed_for_next_level, int) else 'N/A'
        
        embed = discord.Embed(
            title=f"👤 {ctx.author.display_name}的資料 👤",
            color=discord.Color.gold()
        )
        embed.add_field(name="Level", value=user_profile['level'], inline=True)
        embed.add_field(name="Coins 💰", value=user_profile['coins'], inline=True)
        embed.add_field(name="Stat Points", value=user_profile.get('stat_points', 0), inline=True)
        
        embed.add_field(name="HP ❤️", value=user_profile['stats']['hp'], inline=False)
        embed.add_field(name="Strength 💪", value=user_profile['stats']['strength'], inline=True)
        embed.add_field(name="Defense 🛡️", value=user_profile['stats']['defense'], inline=True)
        embed.add_field(name="Intelligence 🧠", value=user_profile['stats']['intelligence'], inline=True)
        embed.add_field(name="Faith ⚜️", value=user_profile['stats']['faith'], inline=True)

        embed.add_field(name="XP ✨", value=f"{current_xp}/{xp_needed_for_next_level} (Next: {xp_to_go})", inline=False)
        
        embed.add_field(name="已裝備武器", value=weapon_display, inline=False)
        if weapon_stats_display:
            embed.add_field(name="武器屬性", value=weapon_stats_display, inline=True)
        
        embed.add_field(name="已裝備盔甲", value=armor_display, inline=False)
        if armor_stats_display:
            embed.add_field(name="盔甲屬性", value=armor_stats_display, inline=True)

        embed.add_field(name="已裝備飾品", value=accessory_display, inline=False)
        if accessory_skill_display:
            embed.add_field(name="飾品屬性", value=accessory_skill_display, inline=True)

        await ctx.send(embed=embed)

    @commands.command(name='inv', help='你的背包~背到現在還沒爛~ 用法: owl inv')
    async def inventory(self, ctx):
        user_id = ctx.author.id
        user_profile = get_user_data(user_id)
        
        inventory_items = user_profile.get('inventory', {})
        if not inventory_items:
            embed = discord.Embed(
                title=f"🎒 {ctx.author.display_name}'s Inventory 🎒",
                description="身體沒有靈魂是死的 背包沒有物品是窮死的",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return

        equipped_weapon = user_profile.get('equipped_weapon')
        equipped_armor = user_profile.get('equipped_armor')
        equipped_accessory = user_profile.get('equipped_accessory')

        item_list = []
        for item_id, item_data in inventory_items.items():
            template = ALL_ITEM_TEMPLATES.get(item_id)
            if template:
                level = item_data.get('level', 1)
                status = []
                if item_id == equipped_weapon:
                    status.append("EQUIPPED WEAPON")
                if item_id == equipped_armor:
                    status.append("EQUIPPED ARMOR")
                if item_id == equipped_accessory:
                    status.append("EQUIPPED ACCESSORY")
                
                status_str = f" ({', '.join(status)})" if status else ""
                item_list.append(f"**{template['name']}** (Lvl {level}){status_str}")
            else:
                item_list.append(f"Unknown Item: `{item_id}` (Lvl {item_data.get('level', 1)}){status_str}")

        embed = discord.Embed(
            title=f"🎒 {ctx.author.display_name}的背包 🎒",
            description="\n".join(item_list),
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

    @commands.command(name='equip', help='裝備物品 用法: !equip [item_id]')
    async def equip(self, ctx, item_id: str):
        user_id = ctx.author.id
        user_profile = get_user_data(user_id)

        item_id_lower = item_id.lower()

        if item_id_lower not in user_profile.get('inventory', {}):
            await ctx.send(f"❌ 你的背包裡沒有 `{item_id}`")
            return

        item_template = ALL_ITEM_TEMPLATES.get(item_id_lower)
        if not item_template:
            await ctx.send(f"❌ 無法選中 請確認裝備類型 `{item_id}`.")
            return

        item_type = item_template['type']
        old_equipped_item_name = "nothing"

        if item_type == "weapon":
            old_equipped_weapon_id = user_profile.get('equipped_weapon')
            if old_equipped_weapon_id:
                old_equipped_item_template = ALL_ITEM_TEMPLATES.get(old_equipped_weapon_id)
                if old_equipped_item_template:
                    old_equipped_item_name = old_equipped_item_template['name']
            user_profile['equipped_weapon'] = item_id_lower
        elif item_type == "armor":
            old_equipped_armor_id = user_profile.get('equipped_armor')
            if old_equipped_armor_id:
                old_equipped_item_template = ALL_ITEM_TEMPLATES.get(old_equipped_armor_id)
                if old_equipped_item_template:
                    old_equipped_item_name = old_equipped_item_template['name']
            user_profile['equipped_armor'] = item_id_lower
        elif item_type == "accessory":
            old_equipped_accessory_id = user_profile.get('equipped_accessory')
            if old_equipped_accessory_id:
                old_equipped_item_template = ALL_ITEM_TEMPLATES.get(old_equipped_accessory_id)
                if old_equipped_item_template:
                    old_equipped_item_name = old_equipped_item_template['name']
            user_profile['equipped_accessory'] = item_id_lower
        else:
            await ctx.send(f"❌ 物品 `{item_id}` 無法選中, 請確認裝備類型.")
            return

        update_user_data(user_id, user_profile)
        item_name = item_template['name']
        await ctx.send(f"✅ 你已裝備 **{item_name}**! (替換了 {old_equipped_item_name}).")

    @commands.command(name='unequip', help='解除裝備 用法: owl unequip [type: weapon/armor/accessory]')
    async def unequip(self, ctx, item_type: str):
        user_id = ctx.author.id
        user_profile = get_user_data(user_id)
        item_type_lower = item_type.lower()
        unequipped_item_name = "nothing"

        if item_type_lower == "weapon":
            if user_profile.get('equipped_weapon'):
                old_equipped_item_template = ALL_ITEM_TEMPLATES.get(user_profile['equipped_weapon'])
                if old_equipped_item_template:
                    unequipped_item_name = old_equipped_item_template['name']
                user_profile['equipped_weapon'] = None
                await ctx.send(f"✅ 你已解除裝備 **{unequipped_item_name}**.")
            else:
                await ctx.send("ℹ️ 你沒有裝備任何武器")
                return
        elif item_type_lower == "armor":
            if user_profile.get('equipped_armor'):
                old_equipped_item_template = ALL_ITEM_TEMPLATES.get(user_profile['equipped_armor'])
                if old_equipped_item_template:
                    unequipped_item_name = old_equipped_item_template['name']
                user_profile['equipped_armor'] = None
                await ctx.send(f"✅ 你已解除裝備 **{unequipped_item_name}**.")
            else:
                await ctx.send("ℹ️ 你沒有裝備任何盔甲")
                return
        elif item_type_lower == "accessory":
            if user_profile.get('equipped_accessory'):
                old_equipped_item_template = ALL_ITEM_TEMPLATES.get(user_profile['equipped_accessory'])
                if old_equipped_item_template:
                    unequipped_item_name = old_equipped_item_template['name']
                user_profile['equipped_accessory'] = None
                await ctx.send(f"✅ 你已解除裝備 **{unequipped_item_name}**.")
            else:
                await ctx.send("ℹ️ 你沒有任何飾品")
                return
        else:
            await ctx.send("❌ 無法選中 請確認裝備類型")
            return

        update_user_data(user_id, user_profile)

    @commands.command(name='upgrade', help='裝備升級/進化 用法: owl upgrade [item_id]')
    async def upgrade(self, ctx, item_id: str):
        user_id = ctx.author.id
        user_profile = get_user_data(user_id)

        item_id_lower = item_id.lower()

        if item_id_lower not in user_profile.get('inventory', {}):
            await ctx.send(f"❌ 你的背包裡沒有 `{item_id}`")
            return

        item_data = user_profile['inventory'][item_id_lower]
        item_template = ALL_ITEM_TEMPLATES.get(item_id_lower)

        if not item_template:
            await ctx.send(f"❌ 物品種類不正確 `{item_id}` 無法被升級 ")
            return
        
        if item_template.get('type') == 'accessory':
            await ctx.send(f"❌ **{item_template['name']}** 是飾品且無法被升級")
            return

        current_level = item_data.get('level', 1)
        max_level = item_template.get('max_level', 5)
        
        if current_level >= max_level:
            if "evolves_to" in item_template:
                evolved_item_id = item_template['evolves_to']
                evolved_item_template = ALL_ITEM_TEMPLATES.get(evolved_item_id)
                if evolved_item_template:
                    evolution_cost = int(item_template['upgrade_cost_multiplier'] * 1500 * current_level)

                    if user_profile['coins'] >= evolution_cost:
                        user_profile['coins'] -= evolution_cost
                        
                        user_profile['inventory'][evolved_item_id] = {"level": 1}
                        
                        del user_profile['inventory'][item_id_lower]

                        if user_profile.get('equipped_weapon') == item_id_lower:
                            user_profile['equipped_weapon'] = evolved_item_id
                        elif user_profile.get('equipped_armor') == item_id_lower:
                            user_profile['equipped_armor'] = evolved_item_id

                        update_user_data(user_id, user_profile)
                        await ctx.send(f"🎉 **{item_template['name']}** 已進化成 **{evolved_item_template['name']}** 它重新變回了等級1")
                    else:
                        await ctx.send(f"💰 你需要 {evolution_cost} 羽毛才可以進化 **{item_template['name']}** 成 **{evolved_item_template['name']}**.")
                else:
                    await ctx.send(f"❌ **{item_template['name']}** 已升級至最高等級 ({max_level}) 且無法再進化")
            else:
                await ctx.send(f"❌ **{item_template['name']}** 已升級至最高等級 ({max_level}) 且無法再進化")
            return

        upgrade_cost = int(item_template['upgrade_cost_multiplier'] * 500 * current_level)

        if user_profile['coins'] >= upgrade_cost:
            print(f"DEBUG: User {user_id} upgrading {item_id_lower}. Coins BEFORE: {user_profile['coins']}, Cost: {upgrade_cost}")
            user_profile['coins'] -= upgrade_cost
            item_data['level'] += 1
            user_profile['inventory'][item_id_lower] = item_data
            print(f"DEBUG: User {user_id} coins AFTER deduction: {user_profile['coins']}")

            update_user_data(user_id, user_profile)

            new_stats = self._calculate_item_stats(item_id_lower, item_data['level'])
            stats_display = ", ".join([f"{s.capitalize()}: {v}" for s, v in new_stats.items()])

            await ctx.send(f"✅ 成功升級 **{item_template['name']}** 至等級 {item_data['level']}")
        else:
            await ctx.send(f"💰 你需要 {upgrade_cost} 羽毛才可以升級 **{item_template['name']}** 至等級 {current_level + 1}.")

    @commands.command(name='tune', help='分配屬性點 用法:  owl tune [stat_name] [amount]')
    async def distribute_points(self, ctx, stat_name: str, amount: int):
        user_id = ctx.author.id
        user_profile = get_user_data(user_id)

        if amount <= 0:
            await ctx.send("❌ 數量須為正數")
            return

        available_points = user_profile.get('stat_points', 0)
        if available_points < amount:
            await ctx.send(f"❌ 你只有 {available_points} 屬性點可以使用")
            return

        stat_name_lower = stat_name.lower()
        if stat_name_lower not in user_profile['stats']:
            await ctx.send(f"❌ 無法分配屬性點 請從: `hp`, `strength`, `defense`, `intelligence`, `faith` 之中選擇")
            return
        
        if stat_name_lower == 'hp':
            user_profile['stats']['hp'] = user_profile['stats'].get('hp', 0) + (amount * 2)
        else:
            user_profile['stats'][stat_name_lower] = user_profile['stats'].get(stat_name_lower, 0) + amount
        
        user_profile['stat_points'] -= amount
        update_user_data(user_id, user_profile)

        await ctx.send(f"✅ 成功分配 {amount} 屬性點 至 **{stat_name_lower.capitalize()}**! 你現有 {user_profile['stats'][stat_name_lower]} {stat_name_lower.capitalize()} 和 {user_profile['stat_points']} 屬性點剩餘")

    @commands.command(name='reset_sp', help='重置你的屬性點，花費你10%的羽毛。用法: owl reset_sp')
    async def reset_sp(self, ctx):
        user_id = ctx.author.id
        user_profile = get_user_data(user_id)

        cost = int(user_profile['coins'] * 0.10)
        min_cost = 1000
        cost = max(cost, min_cost)

        if user_profile['coins'] < cost:
            await ctx.send(f"❌ 重置屬性點需要 {cost} 羽毛，但你只有 {user_profile['coins']} 羽毛。")
            return

        user_profile['coins'] -= cost

        user_profile['stats']['hp'] = INITIAL_PLAYER_PROFILE['stats']['hp']
        user_profile['stats']['strength'] = INITIAL_PLAYER_PROFILE['stats']['strength']
        user_profile['stats']['defense'] = INITIAL_PLAYER_PROFILE['stats']['defense']
        user_profile['stats']['intelligence'] = INITIAL_PLAYER_PROFILE['stats']['intelligence']
        user_profile['stats']['faith'] = INITIAL_PLAYER_PROFILE['stats']['faith']

        user_profile['stat_points'] = max(0, user_profile['level'] - 1)

        update_user_data(user_id, user_profile)

        await ctx.send(
            f"✅ 你的屬性點已成功重置！你花費了 {cost} 羽毛。\n"
            f"所有屬性已重置為基礎值，你現在有 **{user_profile['stat_points']} 屬性點** 可以重新分配。\n"
            f"使用 `owl tune [屬性名稱] [數量]` 重新分配你的點數。"
        )

async def setup(bot):
    await bot.add_cog(RPG(bot))
