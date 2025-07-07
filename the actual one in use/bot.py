import discord
import json
import random
import datetime
from datetime import datetime, timedelta, date, timezone
from discord.ext import commands, tasks
from discord.ext.commands import MissingRequiredArgument
import asyncio

try:
    with open("config.json", "r") as config_file:
        config = json.load(config_file)
except FileNotFoundError:
    print("config.json not found")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.reactions = True
intents.members = True

custom_prefixes = ["owl ", "Owl ", "mumei ", "Mumei "]
bot = commands.Bot(command_prefix=custom_prefixes, intents=intents, case_insensitive=True)
temporary_text_channels = {}
PRIVATE_CHANNEL_EMOJI = '👍'
REQUIRED_REACTIONS_FOR_PRIVATE_CHANNEL = 3
private_channel_requests = {}
user_data = {}
try:
    with open("userdata.json", "r") as f:
        user_data = json.load(f)
except FileNotFoundError:
    pass

INITIAL_PLAYER_PROFILE = {
    "coins": 0,
    "stats": {
        'hp': 100,
        'strength': 10,
        'defense': 10,
        'intelligence': 10,
        'faith': 10,
        'xp': 0
    },
    "level": 1,
    "stat_points": 0,
    "equipped_weapon": "sword",
    "equipped_armor": "leather_armor",
    "equipped_accessory": None,
    "inventory": {
        "sword": {"level": 1},
        "staff": {"level": 1},
        "leather_armor": {"level": 1},
    },
    "physical_damage_tracker": 0
}

XP_TO_NEXT_LEVEL = {
    1: 100, 2: 150, 3: 200, 4: 250, 5: 300,
    6: 350, 7: 400, 8: 450, 9: 500, 10: 550,
}
#levels 11 to 20: Use the formula 50 * i + 100 for a steeper curve
for i in range(11, 21):
    XP_TO_NEXT_LEVEL[i] = 50 * i + 100

for i in range(21, 31):
    XP_TO_NEXT_LEVEL[i] = 50 * i + 150

for i in range(31, 101):
    XP_TO_NEXT_LEVEL[i] = 50 * i + 20000#coming soon

MAX_PLAYER_LEVEL = 100

UPGRADE_STAT_PER_LEVEL = {
    "strength": 1,
    "defense": 1,
    "intelligence": 1,
    "faith": 1,
    "hp": 2
}

WEAPON_TEMPLATES = {
    "sword": {
        "name": "長鋏 🗡️",
        "type": "weapon",
        "base_effect": {"strength": 5},
        "upgrade_cost_multiplier": 1.2,
        "max_level": 5
    },
    "staff": {
        "name": "髡枝 🪄",
        "type": "weapon",
        "base_effect": {"intelligence": 1},
        "upgrade_cost_multiplier": 1.2,
        "max_level": 5
    },
    "kronii": {
        "name": "時分",
        "type": "weapon",
        "base_effect": {"strength": 10},
        "upgrade_cost_multiplier": 1.6,
        "max_level": 5,
        "round_based_damage": {
            "physical_only_rounds": 11,
            "physical_multiplier_normal": 1.0,
            "mixed_hit": {
                "strength_multiplier": 1.0,
                "intelligence_multiplier": 2.0
            }
        }
    },
    "fauna": {
        "name": "淬靈金果",
        "type": "weapon",
        "base_effect": {"faith": 8},
        "upgrade_cost_multiplier": 1.6,
        "max_level": 5,
        "healing_multiplier": 0.5
    },
    "moom": {
        "name": "文明的進程",
        "type": "weapon",
        "base_effect": {"strength": 2},
        "upgrade_cost_multiplier": 1.6,
        "max_level": 5,
        "multi_hit_chance": 0.3,
        "max_extra_hits": 6
    },
    "bae": {
        "name": "子骰",
        "type": "weapon",
        "base_effect": {"strength": 5},
        "upgrade_cost_multiplier": 1.6,
        "max_level": 5,
        "random_action_chance": {"physical_damage": 1.0, "magical_damage": 1.2, "healing": 0.2}
    },
    "irys": {
        "name": "拿非利水晶",
        "type": "weapon",
        "base_effect": {"intelligence": 1, "faith": 4},
        "upgrade_cost_multiplier": 1.6,
        "max_level": 5,
        "healing_multiplier": 0.5
    },
    "sana": {
        "name": "星球力場",
        "type": "weapon",
        "base_effect": {"hp": 20},
        "upgrade_cost_multiplier": 1.6,
        "max_level": 5,
        "deduced_hp_damage_multiplier": 0.5
    }

}

ARMOR_TEMPLATES = {
    "leather_armor": {
        "name": "Leather Armor 🦺",
        "type": "armor",
        "base_effect": {"defense": 3, "hp": 10},
        "upgrade_cost_multiplier": 1.1,
        "max_level": 10
    },
    "iron_armor": {
        "name": "Iron Armor 🛡️",
        "type": "armor",
        "base_effect": {"defense": 15, "hp": 30},
        "upgrade_cost_multiplier": 1.1,
        "max_level": 10
    },
    "gold_armor": {
        "name": "Gold Armor 🪙",
        "type": "armor",
        "base_effect": {"defense": 10, "hp": 20},
        "upgrade_cost_multiplier": 1.5,
        "max_level": 6,
        "evolves_to": "diamond_armor"
    },
    "chainmail_armor": {
        "name": "Chainmail Armor ⛓️",
        "type": "armor",
        "base_effect": {"defense": 20, "hp": 10},
        "upgrade_cost_multiplier": 1.5,
        "max_level": 6,
        "evolves_to": "diamond_armor"
    },
    "diamond_armor": {
        "name": "Diamond Armor 💎",
        "type": "armor",
        "base_effect": {"defense": 20, "hp": 30},
        "upgrade_cost_multiplier": 1.6,
        "max_level": 6,
        "evolves_to": "netherite_armor"
    },
    "netherite_armor": {
        "name": "Netherite Armor 🔥",
        "type": "armor",
        "base_effect": {"defense": 25, "hp": 50},
        "upgrade_cost_multiplier": 2.0,
        "max_level": 15
    }
}


ACCESSORY_TEMPLATES = {
    "latern": {
        "name": "自療提燈 💚✨",
        "type": "accessory",
        "special_skill": {
            "name": "Regeneration",
            "description": "Automatically restores a small amount of HP each combat round.",
            "effect": {"hp_restore": 10}
        }
    },
    "vein": {
        "name": "自療提燈 💚✨",
        "type": "accessory",
        "special_skill": {
            "name": "Overheal",
            "description": "Convert overheal amount into damage.",
            "effect": {"hp_restore": 10}#wip
        }
    },
}


ALL_ITEM_TEMPLATES = {**WEAPON_TEMPLATES, **ARMOR_TEMPLATES, **ACCESSORY_TEMPLATES}

SHOP_ITEMS = {
    "item_healing_potion": {
        "name": "治療藥水 (20 HP)",
        "description": "Restores 20 HP",
        "cost": 150,
        "effect": {'hp': 20}
    },
    "item_strength_amulet": {
        "name": "力量護符 💪(10 strength)",
        "description": "Increases your Strength by 10",
        "cost": 60,
        "effect": {'strength': 10}
    },
    "item_defense_gloves": {
        "name": "守護手套 🧤(3 defense)",
        "description": "Boosts your Defense by 3",
        "cost": 20,
        "effect": {'defense': 3}
    },
    "item_wisdom_scroll": {
        "name": "遠古捲軸 📜(3 intelligence)",
        "description": "Enhances your Intelligence by 3",
        "cost": 60,
        "effect": {'intelligence': 3}
    },
    "item_small_xp_boost": {
        "name": "小型經驗增幅 ✨(50 XP)",
        "description": "Gain 50 XP.",
        "cost": 100,
        "effect": {'xp': 50}
    },
    "item_greater_healing_potion": {
        "name": "強效治療藥水 🧪(50 HP)",
        "description": "Restores a substantial 50 HP",
        "cost": 200,
        "effect": {'hp': 50}
    },
    "item_tome_of_insight": {
        "name": "洞察之書 🧠(5 intelligence)",
        "description": "Increases your Intelligence by 5.",
        "cost": 80,
        "effect": {'intelligence': 5}
    },
    "item_iron_ore_chunk": {
        "name": "鐵礦石塊 🪨(5 defense)",
        "description": "Increases your Defense by 5.",
        "cost": 40,
        "effect": {'defense': 5}
    }
}

#constants for Boss Fight
BOSS_PHYSICAL_PHASE_ID = "abyssal_shadow_lord_p1"
BOSS_MAGICAL_PHASE_ID = "abyssal_shadow_lord_p2"
CRIMSON_BEHEMOTH_ENEMY_ID = "crimson_behemoth_physical"

GAME_EVENTS = {
    "start_adventure": {
        "text": "一團神秘的迷霧籠罩而來 你們發現自己身處遺址入口 你們要怎麼做?",
        "image_url": "https://placehold.co/600x300/4B0082/FFFFFF?text=Dungeon+Entrance",
        "options": {
            "1": {"text": "直接衝進去阿拉花瓜", "next_id": "random_event", "effect": {'strength': 10}},
            "2": {"text": "先探查敵人位置 再衝進去散播民主, 超級地球萬歲", "next_id": "random_event", "effect": {'intelligence': 5}}
        }
    },
    "forest_path": {
        "text": "你們在草叢中撿到一瓶奇怪的藥水 要喝嗎?",
        "image_url": "https://media.discordapp.net/attachments/649186763268423683/1387541089329746011/729.png?ex=685db7d6&is=685c6656&hm=4118d0234765c5b2c6fe74febd66f2d3b2f3d02b1f2d9833cccc327af50bd1ab&=&format=webp&quality=lossless&width=943&height=943",
        "options": {
            "1": {"text": "一口氣喝光", "next_id": "random_event", "effect": {'strength': 20}},
            "2": {"text": "灌隊友嘴裡", "next_id": "random_event", "effect": {'intelligence': 6}}
        }
    },
    "sunny_forest_path": {
        "text": "你們遇到了一位獨自販賣稀有商品的商人。你們要與他互動嗎?",
        "image_url": "https://media.discordapp.net/attachments/649186763268423683/1387541363255415015/730_20250626010354.png?ex=685db818&is=685c6698&hm=e3bb7906a57672b3e8ed559280823a19b78057d38cc8a7a9f1ec2bd45282c311&=&format=webp&quality=lossless&width=943&height=943",
        "options": {
            "1": {"text": "抱歉我社恐", "next_id": "random_event", "effect": {}},
            "2": {"text": "實體生物 能被砍死 四周沒別人", "next_id": "random_event", "effect": {'coins': 5}},
            "3": {"text": "shut up and take my money", "next_id": "shop_encounter", "effect": {}},
        }
    },
    "potion_effect": {
        "text": "一片漿果叢!!!!!!!",
        "image_url": "https://placehold.co/600x300/8A2BE2/FFFFFF?text=Potion+Effect",
        "options": {
            "1": {"text": "一口氣吃光", "next_id": "random_event", "effect": {'strength': 3, 'xp': 5}},
            "2": {"text": "摘點回家吃", "next_id": "random_event", "effect": {'intelligence': 1, 'xp': 5}}
        }
    },
    "goblin_ambush_physical": {
        "text": "一個咆哮的怪物從陰影中跳出，揮舞著生鏽的刀片！選擇你的攻擊方式!",
        "image_url": "https://placehold.co/600x300/6B8E23/FFFFFF?text=Goblin+Ambush",
        "combat_type": "physical",
        "enemy_attack_value": 35,
        "enemy_hp": 90,
        "enemy_defense": 5,
        "options": {
            "1": {"text": "石頭 🪨", "next_id": "outcome_combat_result", "effect": {}},
            "2": {"text": "布 📄", "next_id": "outcome_combat_result", "effect": {}},
            "3": {"text": "剪刀 ✂️", "next_id": "outcome_combat_result", "effect": {}}
        }
    },
    "goblin_ambush_physical2": {
        "text": "一個咆哮的怪物從陰影中跳出，揮舞著生鏽的刀片！選擇你的攻擊方式!",
        "image_url": "https://placehold.co/600x300/6B8E23/FFFFFF?text=Goblin+Ambush",
        "combat_type": "physical",
        "enemy_attack_value": 35,
        "enemy_hp": 90,
        "enemy_defense": 5,
        "options": {
            "1": {"text": "石頭 🪨", "next_id": "outcome_combat_result", "effect": {}},
            "2": {"text": "布 📄", "next_id": "outcome_combat_result", "effect": {}},
            "3": {"text": "剪刀 ✂️", "next_id": "outcome_combat_result", "effect": {}}
        }
    },
    "dark_mage_attack_magical": {
        "text": "一個穿著長袍的身影出現，低吟著咒語，並釋放出一道黑暗能量!",
        "image_url": "https://placehold.co/600x300/4B0082/FFFFFF?text=Dark+Mage",
        "combat_type": "magical",
        "enemy_attack_value": 10,
        "enemy_hp": 70,
        "enemy_defense": 0,
        "options": {
            "1": {"text": "石頭 🪨", "next_id": "outcome_combat_result", "effect": {}},
            "2": {"text": "布 📄", "next_id": "outcome_combat_result", "effect": {}},
            "3": {"text": "剪刀 ✂️", "next_id": "outcome_combat_result", "effect": {}}
        }
    },
    "dark_mage_attack_magical2": {
        "text": "一個穿著長袍的身影出現，低吟著咒語，並釋放出一道黑暗能量!",
        "image_url": "https://placehold.co/600x300/4B0082/FFFFFF?text=Dark+Mage",
        "combat_type": "magical",
        "enemy_attack_value": 10,
        "enemy_hp": 70,
        "enemy_defense": 0,
        "options": {
            "1": {"text": "石頭 🪨", "next_id": "outcome_combat_result", "effect": {}},
            "2": {"text": "布 📄", "next_id": "outcome_combat_result", "effect": {}},
            "3": {"text": "剪刀 ✂️", "next_id": "outcome_combat_result", "effect": {}}
        }
    },
    "merchant_interaction": {
        "text": "商人向你問好。他提供一個幸運符，要價100羽毛。你要買嗎？",
        "image_url": "https://zh.minecraft.wiki/images/Wandering_Trader_JE1_BE1.png?871a6",
        "options": {
            "1": {"text": "購買幸運符(-100 羽毛, +10 防禦)", "next_id": "random_event", "effect": {'coins': -100, 'defense': 10}},
            "2": {"text": "倒賣一個幸運符回去(+1 羽毛, -10 防禦)", "next_id": "random_event", "effect": {'coins': 1, 'defense': -10}}
        }
    },
    "stealth_attempt": {
        "text": "你試圖悄悄地繞過一個睡著了的敵人",
        "image_url": "https://media.discordapp.net/attachments/679390823355252759/1385026162295836824/image.png?ex=685491a1&is=68534021&hm=783611e99f2624a79f4a38aaf1349c08df1c712d5a77529d430d93e5e03f2af6&=&format=webp&quality=lossless&width=710&height=375",
        "options": {
            "1": {"text": "時運高 你睇我唔到", "next_id": "random_event", "effect": {'xp': 5}},
            "2": {"text": "敵不動 我亂動", "next_id": "CRIMSON_BEHEMOTH_ENEMY_ID", "effect": {}}
        }
    },
    "shop_encounter": {
        "text": "你偶然發現了一個隱藏的商店...",
        "image_url": "https://placehold.co/600x300/800080/FFFFFF?text=Mysterious+Shop",
        "options": {}
    },
    "ancient_ruins": {
        "text": "你們來到一片古老的廢墟。古老的石塊低語著: doo~ doo~ doo~ doo~，似乎在邀請你們深入探索。你們會怎麼做？",
        "image_url": "https://media.discordapp.net/attachments/649186763268423683/1384756672341344296/raw.png?ex=685396a6&is=68524526&hm=77feddb84e9dd098f7b02daff527628c368cac6b25df5d693273d0b45dbe9859&=&format=webp&quality=lossless&width=1240&height=826",
        "options": {
            "1": {"text": "深入廢墟尋找寶藏", "next_id": "puzzling_riddle2", "effect": {}},
            "2": {"text": "一起合唱 直到你媽喊你回家吃飯才離去", "next_id": "random_event", "effect": {'xp': 5}}
        }
    },
    "ruins_explore": {
        "text": "你們發現一個腐朽的寶箱！它可能裝滿了寶藏，也可能是一個陷阱。你們會打開它嗎？",
        "image_url": "https://media.discordapp.net/attachments/649186763268423683/1384631242745450676/image.png?ex=685321d5&is=6851d055&hm=4d40892965d2d309ce471827a567fea5814dce95334134fc0c5a382f229b3302&=&format=webp&quality=lossless&width=730&height=356",
        "options": {
            "1": {"text": "寶箱, 你成功引起了我的注意", "next_id": "random_event", "effect": {'xp': random.randint(30, 70), 'coins': random.randint(0, 10), 'strength': 10, 'intelligence': 5}},
            "2": {"text": "寶箱, 我想玩火", "next_id": "random_event", "effect": {}}
        }
    },
    "ruins_explore2": {
        "text": "你們發現一個腐朽的寶箱！它可能裝滿了寶藏，也可能是一個陷阱。你們會打開它嗎？",
        "image_url": "https://media.discordapp.net/attachments/649186763268423683/1384631320277418095/image.png?ex=685321e7&is=6851d067&hm=41cb4826a248cb2c92ca77e7dd6f25deeeb1f11ac3d548dce82fc10c18758621&=&format=webp&quality=lossless&width=690&height=396",
        "options": {
            "1": {"text": "寶箱, 你成功引起了我的注意", "next_id": "random_event", "effect": {'hp': -99}},
            "2": {"text": "寶箱, 我想玩火", "next_id": "random_event", "effect": {}}
        }
    },
    "mysterious_spring": {
        "text": "你們發現了一個閃閃發光的神秘泉水，它的水發出柔和的微光 你們會喝嗎？",
        "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRbJt4VD8SAm8ss5visUP3cd-2_XeqSiSu8odiTCMb8_CH2EloN&s",
        "options": {
            "1": {"text": "見字飲水 (可能恢復生命或有其他效果)", "next_id": "random_event", "effect": {'hp': random.randint(-10, 50), 'xp': 15}},
            "2": {"text": "我親愛的隊友 你渴了對吧", "next_id": "random_event", "effect": {'xp': 15}}
        }
    },
    #"puzzling_riddle": {
    #    "text": "你們遇到了一座古老的雕像，上面刻著一個謎題：\n「我總是在你前面，卻永遠無法觸及, 我是什麼？」\n你們會嘗試回答嗎？",
    #    "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQJAKPL8ZzgSfPdvI5SfIcbaSICEuIq7ezhsn3NBNcKrMx36lA&s",
    #    "options": {
    #        "1": {"text": "回答：「未來」", "next_id": "random_event", "effect": {'xp': 30}},
    #        "2": {"text": "回答：「86 的車尾燈」", "next_id": "random_event", "effect": {'xp': 30, 'hp': -1}},
    #        "3": {"text": "窩不知道", "next_id": "random_event", "effect": {'hp': -10}}
    #    }
    #},
    "puzzling_riddle2": {
        "text": "你們遇到了一座古老的雕像，上面刻著一個謎題：\n「f(x) = 3x^2 +5x -4」\n 「f'(x)是什麼？」\n你們會嘗試回答嗎？",
        "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQJAKPL8ZzgSfPdvI5SfIcbaSICEuIq7ezhsn3NBNcKrMx36lA&s",
        "options": {
            "1": {"text": "回答：「0」", "next_id": "puzzling_riddle3", "effect": {'hp': -1}},
            "2": {"text": "回答：「6x + 5」", "next_id": "puzzling_riddle3", "effect": {'xp': 30}},
            "3": {"text": "回答：「4x」", "next_id": "puzzling_riddle3", "effect": {'hp': -1}},
            "4": {"text": "回答：「是能吃的」", "next_id": "random_event", "effect": {'hp': -10}},
        }
    },
    "puzzling_riddle3": {
        "text": "你們遇到了一座古老的雕像，上面刻著一個謎題：\n「根據宇宙大爆炸理論，宇宙中含量最多的元素是什麼？」\n你們會嘗試回答嗎？",
        "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQJAKPL8ZzgSfPdvI5SfIcbaSICEuIq7ezhsn3NBNcKrMx36lA&s",
        "options": {
            "1": {"text": "回答：「氫H」", "next_id": "puzzling_riddle4", "effect": {'xp': 30}},
            "2": {"text": "回答：「氦He」", "next_id": "puzzling_riddle4", "effect": {'hp': -1}},
            "3": {"text": "回答：「碳C」", "next_id": "puzzling_riddle4", "effect": {'hp': -1}},
            "4": {"text": "回答：「氧O」", "next_id": "puzzling_riddle4", "effect": {'hp': -1}},
            "5": {"text": "回答：「不會」", "next_id": "random_event", "effect": {'hp': -10}}
        }
    },
    "puzzling_riddle4": {
        "text": "你們遇到了一座古老的雕像，上面刻著一個謎題：\n「系列中的下一個數字是：2、5、10、17、26...？」\n你們會嘗試回答嗎？",
        "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQJAKPL8ZzgSfPdvI5SfIcbaSICEuIq7ezhsn3NBNcKrMx36lA&s",
        "options": {
            "1": {"text": "回答：「32」", "next_id": "ruins_explore", "effect": {'hp': -1}},
            "2": {"text": "回答：「774」", "next_id": "ruins_explore", "effect": {'xp': 7}},
            "3": {"text": "回答：「37」", "next_id": "ruins_explore", "effect": {'xp': 30}},
            "4": {"text": "回答：「29」", "next_id": "ruins_explore", "effect": {'hp': -1}},
            "5": {"text": "回答：「不會」", "next_id": "random_event", "effect": {'hp': -10}}
        }
    },
    "puzzling_riddle5": {
        "text": "你們遇到了一座古老的雕像，上面刻著一個謎題：\n「以下何者為真實的文明記錄？」？",
        "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQJAKPL8ZzgSfPdvI5SfIcbaSICEuIq7ezhsn3NBNcKrMx36lA&s",
        "options": {
            "1": {"text": "回答：「一名假警察在I-4高速公路上截停真警察被捕」", "next_id": "random_event", "effect": {'xp': 10}},
            "2": {"text": "回答：「一名老人因為擔心冰毒對自己健康有影響而把冰毒帶去請教醫生」", "next_id": "random_event", "effect": {'xp': 10}},
            "3": {"text": "回答：「男子因駕駛割草機撞上一輛警車而被逮捕 並被指控酒後駕駛」", "next_id": "random_event", "effect": {'xp': 10}},
            "4": {"text": "回答：「男子在入室搶劫期間睡著被捕」", "next_id": "random_event", "effect": {'xp': 10}},
            "5": {"text": "回答：「以上皆是」", "next_id": "random_event", "effect": {'xp': 30}}
        }
    },
    #"uth_duna": {
    #    "text": "你們發現了一個廢棄的營地，篝火已熄滅，周圍散落著一些物品。你們會搜尋物資嗎？",
    #    "image_url": "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEiFy92_45nVM_5zq7ZnmDe7I3Rcy8sUh9m03pnFFhUS-tDKcBPTD8nbRZAJfB3oLAFPd2eCKEVHP9M_FvAMYpnFFKyOw0yik6SyFagklicTMLfPHoLyBFYwFYVJm2dqR0cPPeoq8x0pnWs/s800/camp_campfire.png",
    #    "options": {
    #        "1": {"text": "搜尋營地（可能找到物資，也可能觸發陷阱）", "next_id": "random_event", "effect": {'coins': random.randint(0, 5), 'hp': random.randint(-5, 0), 'xp': 10}},
    #        "2": {"text": "謹慎離開", "next_id": "random_event", "effect": {}}
    #    }
    #},
    "sign": {
        "text": "一個奇怪的虛影 擺著奇怪的動作 頭上冒出奇怪的句子",
        "image_url": "https://media.discordapp.net/attachments/649186763268423683/1384820324989931570/image.png?ex=6853d1ee&is=6852806e&hm=92aa76555b47db75fd5d60202e02eb4ba02ddb6470c6d5c6faf23a94d446b96d&=&format=webp&quality=lossless&width=820&height=100",
        "options": {
            "1": {"text": "翻滾", "next_id": "ruins_explore", "effect": {}},
            "2": {"text": "轉身離開 你有話說不出來", "next_id": "random_event", "effect": {}}
        }
    },
    "friend": {
        "text": "friend 給了你們一個盒子, 上面印著「りしれ供さ小」聽說是小禮物的意思",
        "image_url": "https://media.discordapp.net/attachments/883708922488315924/887947855711567872/fukuro.png?ex=685c3fa2&is=685aee22&hm=a5aec35fc48a36ceb67f7e436fe7cd6298f809c651c8a771fb64f0fcc8d18b56&=&format=webp&quality=lossless&width=453&height=453",
        "options": {
            "1": {"text": "收下", "next_id": "random_event", "effect": {'hp': random.randint(-10, 5),'strength': random.randint(-5, 5),'intelligence': random.randint(-5, 3)}},
            "2": {"text": "收下", "next_id": "random_event", "effect": {'hp': random.randint(-1, 50),'strength': random.randint(-10, 10),'intelligence': random.randint(-10, 3),}},
            "3": {"text": "還是收下", "next_id": "random_event", "effect": {'hp': random.randint(-10, 5),'defense': random.randint(-1, 5),'faith': random.randint(-1, 20),}}
        }
    },
    "friendly_traveler": {
        "text": "一位看起來友善的旅行者向你們走來。他提出可以用他的玩偶換取一些羽毛。你們會交易嗎？",
        "image_url": "https://media.discordapp.net/attachments/649186763268423683/1387457899504078878/thinking-about-yagoo-v0-5e0amvtqhgad1.jpg?ex=685d6a5c&is=685c18dc&hm=0ea033252b85351be21591760b7db668c6b01a0e0ab4aefa1a275db160b3e42d&=&format=webp&width=741&height=943",
        "options": {
            "1": {"text": "交換玩偶 (-150 羽毛, +2 智力)", "next_id": "random_event", "effect": {'coins': -150, 'intelligence': 2, 'xp': 15}},
            "2": {"text": "實體生物 能被砍死 四周沒別人(<:ch_Danger:882088640723955823>)", "next_id": "random_event", "effect": {'hp': -99999}}
        }
    },

    "CRIMSON_BEHEMOTH_ENEMY_ID": {
        "text": "一聲震耳欲聾的咆哮迴盪！一隻巨大的熔岩巨獸從沉睡中醒來，準備碾碎所有入侵者！畢竟擾人清夢如同殺人父母嘛。",
        "image_url": "https://static.wikia.nocookie.net/angrybirds/images/0/06/ABMovie_RedStanding.png/revision/latest?cb=20160524151739",
        "combat_type": "physical",
        "enemy_attack_value": 40,
        "enemy_hp": 1211,
        "enemy_defense": 20,
        "options": {
            "1": {"text": "石頭 🪨", "next_id": "outcome_combat_result", "effect": {}},
            "2": {"text": "剪刀 📄", "next_id": "outcome_combat_result", "effect": {}},
            "3": {"text": "布 ✂️", "next_id": "outcome_combat_result", "effect": {}}
        },
    },
    BOSS_PHYSICAL_PHASE_ID: {
        "text": "在你面前屹立著強大的深淵暗影領主，散發著巨大的物理力量！準備迎接它的猛攻!",
        "image_url": "https://placehold.co/600x300/1A0033/FFFFFF?text=Abyssal+Shadow+Lord",
        "combat_type": "physical",
        "enemy_attack_value": 35,
        "enemy_hp": 1500,
        "enemy_defense": 15,
        "enemy_intelligence_attack": 0,
        "options": {
            "1": {"text": "石頭 🪨", "next_id": "outcome_combat_result", "effect": {}},
            "2": {"text": "布 📄", "next_id": "outcome_combat_result", "effect": {}},
            "3": {"text": "剪刀 ✂️", "next_id": "outcome_combat_result", "effect": {}}
        },
        "boss_phase_name": "physical" 
    },
    BOSS_MAGICAL_PHASE_ID: {#dynamically
        "text": "深淵暗影領主的裝甲剝落，內部的黑魔法被完全解放!",
        "image_url": "https://placehold.co/600x300/330066/FFFFFF?text=Shadow+Lord+Magic",
        "combat_type": "magical",
        "enemy_attack_value": 35,
        "enemy_hp": 1500,
        "enemy_defense": 1,
        "enemy_intelligence_attack": 40,
        "options": {
            "1": {"text": "石頭 🪨", "next_id": "outcome_combat_result", "effect": {}},
            "2": {"text": "布 📄", "next_id": "outcome_combat_result", "effect": {}},
            "3": {"text": "剪刀 ✂️", "next_id": "outcome_combat_result", "effect": {}}
        },
        "boss_phase_name": "magical",
        "special_attack_chance": 0.4
    }
}

GAME_OUTCOMES = {
    "outcome_combat_result": "戰鬥的碰撞聲迴盪！詳情請見下方結果",
    "outcome_run_completed": "經歷了無數的考驗，你的隊伍決定從這次探險中返回!"
}

#list all event IDs that can be randomly chosen for continuation (excluding start, shop, and outcomes, and boss phases)
ALL_PLAYABLE_EVENT_IDS = [
    eid for eid in GAME_EVENTS if eid not in [
        "start_adventure", "shop_encounter", BOSS_PHYSICAL_PHASE_ID, BOSS_MAGICAL_PHASE_ID, "CRIMSON_BEHEMOTH_ENEMY_ID", "puzzling_riddle2", "puzzling_riddle3", "puzzling_riddle4"
    ] and not eid.startswith("outcome_")
]

SHOP_CHANCE = 0.1
ITEM_DROP_CHANCE = 0.25
RUN_EVENT_LIMIT = 20

GLOBAL_ITEM_POOL = list(WEAPON_TEMPLATES.keys()) + [
    armor_id for armor_id, data in ARMOR_TEMPLATES.items()
    if 'evolves_to' not in data and armor_id not in INITIAL_PLAYER_PROFILE['inventory'] and armor_id != "netherite_armor" and armor_id != "diamond_armor"
]

GAME_EMOJIS = {
    "1": "1️⃣",
    "2": "2️⃣",
    "3": "3️⃣",
    "4": "4️⃣",
    "5": "5️⃣",
    "X": "❌"
}

active_questionnaires = {}

@tasks.loop(minutes=1)
async def check_for_expired_channels():
    current_time = datetime.now(timezone.utc)
    channels_to_delete = []

    for channel_id, deletion_time in list(temporary_text_channels.items()):
        if current_time >= deletion_time:
            channels_to_delete.append(channel_id)

    for channel_id in channels_to_delete:
        channel = bot.get_channel(channel_id)
        if channel:
            try:
                #if a game is still active in a channel about to be deleted (shouldn't happen?
                #for RPG channels if logic is correct, but defensive check), send a final summary.
                if channel_id in active_questionnaires:
                    await _send_run_summary(channel, active_questionnaires[channel_id])
                    # _send_run_summary already deletes from active_questionnaires, no need here ig?
                    print(f"DEBUG: Sent summary for active game in expiring general temp channel: {channel.name}")

                await channel.delete()
                del temporary_text_channels[channel_id]
                print(f'Deleted expired temporary text channel: {channel.name} ({channel.id})')
            except discord.Forbidden as e:
                print(f'Bot does not have permissions to delete channel: {channel.name} ({channel.id}) - {e}')
            except discord.HTTPException as e:
                print(f'Failed to delete channel {channel.name}: {e}')
        else:
            del temporary_text_channels[channel_id]
            print(f'Removed tracking for non-existent channel ID: {channel_id}')

@bot.event
async def on_ready():
    """Event handler for when the bot successfully connects to Discord."""
    print(f'Logged in as {bot.user.name}')
    await reset_game()
    bot_balance = user_data.get("bot_donations", {"coins": 0}).get("coins", 0)
    await bot.change_presence(activity=discord.Game(name=f"{bot_balance} 根羽毛"))
    if not check_for_expired_channels.is_running():
        check_for_expired_channels.start()
        print('Started background task for general temporary channel deletion.')
    
    #start the daily reset task for the guess game
    if not daily_reset_task.is_running():
        daily_reset_task.start()
        print('Started daily_reset_task for guess game.')

@bot.event
async def on_disconnect():
    """Event handler for when the bot disconnects from Discord."""
    if check_for_expired_channels.is_running():
        check_for_expired_channels.cancel()
        print('Stopped background task for general temporary channel deletion.')
    if daily_reset_task.is_running():
        daily_reset_task.cancel()
        print('Stopped daily_reset_task for guess game.')

@bot.event
async def on_raw_reaction_add(payload):
    """
    Event handler for raw reaction additions.
    Handles private channel creation reactions and in-game event reactions.
    """
    if payload.user_id == bot.user.id:
        return

    #private channel creation reactions for RPG channels
    if payload.message_id in private_channel_requests:
        request_data = private_channel_requests[payload.message_id]
        if str(payload.emoji) == PRIVATE_CHANNEL_EMOJI:
            guild = bot.get_guild(payload.guild_id)
            if not guild: return
            member = guild.get_member(payload.user_id)
            if not member:
                try: #fetch if not in cache
                    member = await guild.fetch_member(payload.user_id)
                except (discord.NotFound, discord.Forbidden):
                    return

            if member.id not in request_data['users']:
                request_data['users'].add(member.id)
                current_reaction_count = len(request_data['users'])

                original_channel = bot.get_channel(payload.channel_id)
                if original_channel and current_reaction_count < REQUIRED_REACTIONS_FOR_PRIVATE_CHANNEL:
                    try:
                        embed = discord.Embed(
                            title="頻道創建中",
                            description=f"**{current_reaction_count}/{REQUIRED_REACTIONS_FOR_PRIVATE_CHANNEL}** 位玩家已響應以創建私人頻道 ({member.display_name} 已加入)",
                            color=discord.Color.orange()
                        )
                        await original_channel.send(embed=embed, delete_after=10) #progress message, delete after 10 seconds
                    except discord.Forbidden as e:
                        print(f"Bot lacks permissions to send progress message in {original_channel.name}: {e}")
                    except discord.HTTPException as e:
                        print(f"Bot failed to send progress message in {original_channel.name}: {e}")

                if current_reaction_count >= REQUIRED_REACTIONS_FOR_PRIVATE_CHANNEL and not request_data['creation_initiated']:
                    request_data['creation_initiated'] = True #prevent multiple channel creations from same message
                    original_message_channel = bot.get_channel(payload.channel_id)
                    if original_message_channel:
                        try:
                            original_message = await original_message_channel.fetch_message(payload.message_id)
                            await original_message.clear_reactions() #clear reactions once fulfilled
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
                        else: #fetch member if not in cache (e.g., if bot restarted)
                            try:
                                fetched_member = await guild.fetch_member(user_id)
                                reacted_members.append(fetched_member)
                            except (discord.NotFound, discord.Forbidden):
                                pass

                    organizer_id = request_data.get('organizer_id')
                    if organizer_id:
                        organizer_user_data = _get_user_data_db(organizer_id)
                        current_coins = organizer_user_data.get('coins', 0)
                        fee = 100 #int(current_coins * 0.01) # 1% fee

                        fee_message = ""
                        if fee > 0 and current_coins > 0:
                            actual_deduction = min(fee, current_coins)
                            organizer_user_data['coins'] = max(0, current_coins - actual_deduction)
                            update_user_data(organizer_id, organizer_user_data)
                            update_user_data_file()
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
                    await _create_rpg_channel( #call the dedicated RPG channel creation function
                        guild, reacted_members, request_data['name'], category
                    )
                    #clean up the request after channel creation
                    if payload.message_id in private_channel_requests:
                        del private_channel_requests[payload.message_id]
        return

    #for in-game event reactions
    if payload.channel_id in active_questionnaires:
        game_state = active_questionnaires[payload.channel_id]

        if payload.message_id == game_state['prompt_message_id']:
            guild = bot.get_guild(payload.guild_id)
            if not guild: return

            channel = bot.get_channel(payload.channel_id)
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
                        #show options for items currently available in the shop
                        for i, item_id in enumerate(game_state['shop_current_items']):
                            valid_emojis.append(GAME_EMOJIS[str(i + 1)])
                        valid_emojis.append(GAME_EMOJIS['X']) #exit option
                    else:
                        for option_key in current_event_data['options'].keys():
                            if option_key in GAME_EMOJIS:
                                valid_emojis.append(GAME_EMOJIS[option_key])
                
                #check if the reacted emoji is valid for the current event
                if str(payload.emoji) in valid_emojis:
                    async with game_state['lock']:
                        game_state['votes'][member.id] = str(payload.emoji)

                        if len(game_state['votes']) == len(game_state['participants']):
                            await process_event_results(payload.channel_id)
                else:
                    if channel:
                        try:
                            message = await channel.fetch_message(payload.message_id)
                            await message.remove_reaction(payload.emoji, member)
                        except (discord.Forbidden, discord.HTTPException):
                            pass #no permission to remove reactions, or message might be gone

async def _create_rpg_channel(guild: discord.Guild, members: list[discord.Member], name: str, category: discord.CategoryChannel = None):
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False), #deny access
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True) #allow bot full access
    }
    for member in members:
        if member:
            overwrites[member] = discord.PermissionOverwrite(read_messages=True, send_messages=True) #allow selected members access

    try:
        #create the new text channel
        new_channel = await guild.create_text_channel(
            name=name, category=category, overwrites=overwrites
        )

        #notify users about the new channel
        member_mentions = ", ".join([member.mention for member in members])
        embed = discord.Embed(
            title=f"歡迎來到 #{new_channel.name}!",
            description=f"{member_mentions}, 你的任務開始了! 進入遺址並找到成員的藏品吧 ",
                        #f"It will vanish after your adventure concludes!",
            color=discord.Color.blue()
        )
        await new_channel.send(embed=embed)
        await start_game_session(new_channel, members) #start the game session in the new channel

    except discord.Forbidden:
        embed = discord.Embed(
            title="Permission Error", description="I don't have permission to create private channels!", color=discord.Color.red()
        )
        print(f'Bot does not have permissions to create private channels.')
    except discord.HTTPException as e:
        embed = discord.Embed(
            title="Channel Creation Error", description=f"An error occurred while creating the channel: {e}", color=discord.Color.red()
        )
        print(f'Failed to create private channel in {guild.name}: {e}')

def _get_user_data_db(user_id: int) -> dict:
    """Retrieves a user's persistent data from the database, initializing if not found."""
    user_id_str = str(user_id)
    if user_id_str not in user_data:
        user_data[user_id_str] = json.loads(json.dumps(INITIAL_PLAYER_PROFILE))
        user_data[user_id_str]['stats'] = INITIAL_PLAYER_PROFILE['stats'].copy()
        user_data[user_id_str]['inventory'] = INITIAL_PLAYER_PROFILE['inventory'].copy()
        user_data[user_id_str]['physical_damage_tracker'] = INITIAL_PLAYER_PROFILE['physical_damage_tracker']
        update_user_data_file()
    return user_data[user_id_str]

def update_user_data(user_id: int, user_data_obj: dict):
    """Updates a user's persistent data in memory."""
    user_id_str = str(user_id)
    user_data[user_id_str] = user_data_obj

def _calculate_item_stats(item_id: str, item_level: int) -> dict:
    """Calculates the effective stats of an item based on its level."""
    template = ALL_ITEM_TEMPLATES.get(item_id)
    if not template: return {}

    calculated_stats = {}
    base_effect = template.get('base_effect', {})

    for stat, base_value in base_effect.items():
        scaled_value = base_value + (item_level - 1) * UPGRADE_STAT_PER_LEVEL.get(stat, 0)
        calculated_stats[stat] = scaled_value
    
    return calculated_stats

def _check_level_up(user_data_obj: dict) -> dict:
    """Checks if a user has enough XP to level up and updates their profile accordingly."""
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
        user_data_obj['stats']['xp'] = 0 #no more XP accumulation after max level
    
    return user_data_obj

async def start_game_session(channel: discord.TextChannel, participants: list[discord.Member]):
    """Initializes a new game session in a given channel with specified participants."""
    players_run_stats = {}
    for member in participants:
        user_data_obj = _get_user_data_db(member.id)
        
        #initialize run-specific stats based on persistent stats and equipped items
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

        #apply equipped weapon bonuses
        equipped_weapon_id = user_data_obj.get('equipped_weapon')
        if equipped_weapon_id and equipped_weapon_id in user_data_obj['inventory']:
            weapon_level = user_data_obj['inventory'][equipped_weapon_id]['level']
            weapon_bonuses = _calculate_item_stats(equipped_weapon_id, weapon_level)
            for stat, bonus in weapon_bonuses.items():
                run_stats[stat] = run_stats.get(stat, 0) + bonus
        
        #apply equipped armor bonuses
        equipped_armor_id = user_data_obj.get('equipped_armor')
        if equipped_armor_id and equipped_armor_id in user_data_obj['inventory']:
            armor_level = user_data_obj['inventory'][equipped_armor_id]['level']
            armor_bonuses = _calculate_item_stats(equipped_armor_id, armor_level) 
            for stat, bonus in armor_bonuses.items():
                run_stats[stat] = run_stats.get(stat, 0) + bonus

        #initialize equipped accessory for run stats (no direct stat buff, just ID for skill lookup)
        equipped_accessory_id = user_data_obj.get('equipped_accessory')
        if equipped_accessory_id and equipped_accessory_id in user_data_obj['inventory']:
            run_stats['equipped_accessory'] = equipped_accessory_id #store ID for runtime lookup of skill

        players_run_stats[member.id] = run_stats

    #store game state for the channel
    active_questionnaires[channel.id] = {
        'participants': {member.id for member in participants},
        'players': players_run_stats,
        'current_event_id': "start_adventure",
        'prompt_message_id': None,
        'votes': {},
        'lock': asyncio.Lock(), #to prevent concurrent processing of votes
        'events_completed': 0,#for display
        'enemy_current_hp': None,
        'enemy_data': None,
        'shop_current_items': [],
        'boss_phase_transitioned': False, #flag to ensure phase transition message only once
        'consecutive_tie_count': 0,
        'seen_events': set()
    }
    await send_next_event(channel)

def _get_player_stats_string(players_data: dict) -> str:
    """Generates a formatted string of current player stats for display."""
    stat_lines = []
    for user_id, stats in players_data.items():
        member = bot.get_user(user_id)
        name = member.display_name if member else f"User {user_id}" #get display name or fallback
        
        #display only in-game combat relevant stats for the party status
        stat_lines.append(
            f"**{name}**: HP: {stats['hp']}, Str: {stats['strength']}, Def: {stats['defense']}, Int: {stats['intelligence']}, Faith: {stats['faith']}"
        )
    return "\n".join(stat_lines)

async def send_next_event(channel: discord.TextChannel, force_current: bool = False):
    """Sends the next game event to the channel based on current game state."""
    if channel.id not in active_questionnaires: return

    game_state = active_questionnaires[channel.id]
    
    if all(player_stats['hp'] <= 0 for player_stats in game_state['players'].values()) and game_state['current_event_id'] not in [BOSS_PHYSICAL_PHASE_ID, BOSS_MAGICAL_PHASE_ID, "outcome_run_completed"]:
        game_state['current_event_id'] = "outcome_run_completed" #force run conclusion on total party defeat
        await _send_run_summary(channel, game_state)
        return
    
    next_event_to_send_id = None

    if force_current:
        next_event_to_send_id = game_state['current_event_id']
    elif game_state['events_completed'] == 0 and game_state['current_event_id'] == "start_adventure":
        next_event_to_send_id = "start_adventure" #always start with the initial event if it's the very first event
    elif game_state['enemy_current_hp'] is not None and game_state['enemy_current_hp'] > 0 and game_state['current_event_id'] in [BOSS_PHYSICAL_PHASE_ID, BOSS_MAGICAL_PHASE_ID]:
        #if currently in boss combat and boss is alive, continue the same combat event (potentially shifted phase)
        next_event_to_send_id = game_state['current_event_id']
    elif game_state['enemy_current_hp'] is not None and game_state['enemy_current_hp'] > 0 and game_state['current_event_id'] in GAME_EVENTS and 'combat_type' in GAME_EVENTS[game_state['current_event_id']]:
        #if currently in regular combat and enemy is alive, continue the same combat event
        next_event_to_send_id = game_state['current_event_id']
    elif game_state['events_completed'] >= RUN_EVENT_LIMIT and game_state['current_event_id'] not in [BOSS_PHYSICAL_PHASE_ID, BOSS_MAGICAL_PHASE_ID]:
        #if run limit reached and not already in boss fight, trigger main boss fight
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
        #print(f"DEBUG: Triggering boss fight: {next_event_to_send_id}, Boss HP: {game_state['enemy_current_hp']}")

    elif random.random() < SHOP_CHANCE and game_state['current_event_id'] != "shop_encounter" and game_state['enemy_current_hp'] is None:
        next_event_to_send_id = "shop_encounter"
    else:
        game_state['enemy_current_hp'] = None
        game_state['enemy_data'] = None

        #weighted random selection for next event (wip)
        potential_random_events = [
            eid for eid in ALL_PLAYABLE_EVENT_IDS
            if eid not in [BOSS_PHYSICAL_PHASE_ID, BOSS_MAGICAL_PHASE_ID, CRIMSON_BEHEMOTH_ENEMY_ID, "shop_encounter"]
        ]
        
        weights = []
        possible_choices = []

        for event_id_candidate in potential_random_events:
            if event_id_candidate in game_state['seen_events']:
                weights.append(0.2) #lower chance for seen events
            else:
                weights.append(1.0) #normal chance for unseen events
            possible_choices.append(event_id_candidate)
        
        if all(event_id_candidate in game_state['seen_events'] for event_id_candidate in potential_random_events):
            game_state['seen_events'].clear()
            weights = [1.0 for _ in potential_random_events]
            print(f"DEBUG: All playable random events seen, resetting seen_events for channel {channel.id}")

        #ensure there's at least one event to choose from, even if it's been seen.
        if not possible_choices: #fallback if for some reason list is empty (shouldn't happen with ALL_PLAYABLE_EVENT_IDS)
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
    
    current_party_stats = _get_player_stats_string(game_state['players'])

    embed = discord.Embed(
        #title=f"Quest Log: Encounter! (Event: '{event_data.get('title', next_event_to_send_id)}')",
        description=event_data["text"],
        color=discord.Color.blue()
    )

    #display enemy HP if in a combat event (regular or boss)
    if game_state['enemy_current_hp'] is not None and game_state['enemy_data'] is not None:
        enemy_name = "敵人"
        if next_event_to_send_id.startswith("abyssal_shadow_lord"):
            enemy_name = "深淵暗影領主"
        elif next_event_to_send_id == CRIMSON_BEHEMOTH_ENEMY_ID:
            enemy_name = "熔岩巨獸"
            # if game_state['enemy_data'].get('enraged'):
            #    embed.description += "\n🔥 **熔岩巨獸已發怒！它的攻擊更強了！** 🔥"
        embed.description += f"\n**{enemy_name} HP:** {game_state['enemy_current_hp']}/{game_state['enemy_data']['hp']}"

    if 'image_url' in event_data and event_data['image_url']:
        #a cache-busting timestamp to the URL
        cache_busted_url = f"{event_data['image_url']}?v={int(datetime.now().timestamp())}"
        embed.set_image(url=cache_busted_url)

    options_to_display = {}
    if next_event_to_send_id == "shop_encounter":
        embed.title = "神秘商人! 💰"
        embed.description = "神秘商人貪婪地看著你們身上的羽毛!\n\n"
        
        num_items_to_show = random.randint(3, min(5, len(SHOP_ITEMS)))
        #only select items that are not already in shop_current_items (if any were carried over from a re-display)
        available_shop_items = [item_id for item_id in SHOP_ITEMS.keys() if item_id not in game_state['shop_current_items']]
        
        #if there aren't enough new items, prioritize already shown items
        if len(available_shop_items) < num_items_to_show:
            selected_item_ids = random.sample(list(SHOP_ITEMS.keys()), num_items_to_show)
        else:
            selected_item_ids = random.sample(available_shop_items, num_items_to_show)
        
        game_state['shop_current_items'] = selected_item_ids #update current shop items

        for i, item_id in enumerate(selected_item_ids):
            item = SHOP_ITEMS[item_id]
            option_number_str = str(i + 1)
            options_to_display[option_number_str] = {
                "text": f"{item['name']} - Cost: {item['cost']} Coins. {item['description']}",
                "next_id": item_id, #next_id for shop items is the item_id itself
                "effect": item['effect'],
                "cost": item['cost']
            }
            embed.add_field(
                name=f"{GAME_EMOJIS.get(option_number_str, option_number_str)} {option_number_str}",
                value=f"{item['name']} (Cost: {item['cost']} Coins)",
                inline=False
            )
        
        #add "Leave shop" option
        options_to_display['X'] = {
            "text": "離開商店 👋",
            "next_id": "random_event_after_shop", #placeholder to trigger a random event after leaving
            "effect": {}
        }
        embed.add_field(name=f"{GAME_EMOJIS.get('X', 'X')} X", value="Leave the shop", inline=False)
        #GAME_EVENTS["shop_encounter"]["options"] is not updated here, as options are dynamic
    else:
        for option_key, option_details in event_data["options"].items():
            #effect_str = ""
            #if option_details.get('effect'):
            #    effects = []
            #    for stat, change in option_details['effect'].items():
            #        if stat == 'coins' or stat == 'xp':
            #            effects.append(f"{'+' if change >= 0 else ''}{change} {stat.upper()}")
            #        else:
            #            effects.append(f"{'+' if change >= 0 else ''}{change} {stat.capitalize()}")
            #    effect_str = f" ({', '.join(effects)})"
            embed.add_field(name=f"{GAME_EMOJIS.get(option_key, option_key)} {option_details['text']}", value="\u200B", inline=False) #use Zero-Width Space for value if not needed

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

        #add reactions based on the options
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


async def _process_combat_round(channel: discord.TextChannel, game_state: dict, chosen_option_key: str) -> tuple[str, bool]:
    result_description = ""
    combat_ended = False

    current_event_id = game_state['current_event_id']
    current_enemy_data = game_state['enemy_data']
    enemy_current_hp = game_state['enemy_current_hp']
    current_event_template = GAME_EVENTS[current_event_id]
    
    is_boss_fight = current_event_id.startswith("abyssal_shadow_lord")

    #determine the single RPS outcome multiplier for the entire party
    rps_moves = ["rock", "paper", "scissors"]
    enemy_move = random.choice(rps_moves)
    player_move_map = {"1": "rock", "2": "paper", "3": "scissors"}
    player_chosen_rps_move = player_move_map.get(chosen_option_key)

    rps_multiplier = 0.0 #default to no damage
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
    
    #updated display name
    enemy_display_name = "敵人"
    if current_event_id.startswith("abyssal_shadow_lord"):
        enemy_display_name = "深淵暗影領主"
    elif current_event_id == CRIMSON_BEHEMOTH_ENEMY_ID: #updated to ENEMY_ID
        enemy_display_name = "熔岩巨獸"

    result_description += f"{enemy_display_name} 以 **{enemy_move.capitalize()}**回擊!\n"
    result_description += f"你的隊伍選擇了 **{player_chosen_rps_move.capitalize()}**! {rps_outcome_text}\n\n"
    
    # --- BOSS PHASE TRANSITION CHECK (only for boss) ---
    if is_boss_fight and game_state['boss_current_phase'] == "physical" and not game_state['boss_phase_transitioned'] and enemy_current_hp <= (current_enemy_data['hp'] * 0.5):
        #transition to magical phase
        game_state['boss_current_phase'] = "magical"
        game_state['boss_phase_transitioned'] = True
        game_state['current_event_id'] = BOSS_MAGICAL_PHASE_ID #update current event ID for next round
        current_event_template = GAME_EVENTS[BOSS_MAGICAL_PHASE_ID] #get updated template for the new phase
        
        result_description += "\n**THE ABYSSAL SHADOW LORD SHIFTS!** 它的裝甲剝落，內部的黑魔法被完全解放!\n"
        #update enemy_data for the new phase (only the mutable parts that change with phase)
        current_enemy_data['attack_value'] = current_event_template['enemy_attack_value']
        current_enemy_data['defense'] = current_event_template['enemy_defense']
        current_enemy_data['intelligence_attack'] = current_event_template.get('enemy_intelligence_attack', 0)
        game_state['enemy_data'] = current_enemy_data #ensure changes are saved back to state
        #print(f"DEBUG: Boss transitioned to magical phase. New enemy data: {game_state['enemy_data']}")


    # --- ENEMY ATTACK ---
    damage_taken_summary = []
    
    enemy_damage_dealt_base = current_enemy_data['attack_value'] #use enemy's current phase attack value
    
    if current_event_template['combat_type'] == "physical":
        result_description += f"{enemy_display_name} 揮出了 **P = mv**!\n"
        for user_id_int in game_state['participants']:
            player_run_stats = game_state['players'][user_id_int]
            if player_run_stats['hp'] <= 0: continue
            
            damage_taken = max(1, enemy_damage_dealt_base - player_run_stats['defense'])
            player_run_stats['hp'] -= damage_taken
            player_run_stats['hp'] = max(0, player_run_stats['hp'])
            damage_taken_summary.append(f"{bot.get_user(user_id_int).display_name} 受到了 {damage_taken} 物理傷害 (HP: {player_run_stats['hp']})")
    elif current_event_template['combat_type'] == "magical":
        result_description += f"{enemy_display_name} 施放了 **V = IR**!\n"
        
        #chance for special AoE attack (Abyssal Blast) if it's the boss's magical phase
        if is_boss_fight and random.random() < current_event_template.get('special_attack_chance', 0):
            aoe_damage_base = current_event_template['enemy_intelligence_attack']
            aoe_damage_text = "N = N0 * 2^(t/T)"
            result_description += f"領主蓄力施放了 **{aoe_damage_text}**! 一道黑色的衝擊波衝向了隊伍!\n"
            for user_id_int in game_state['participants']:
                player_run_stats = game_state['players'][user_id_int]
                if player_run_stats['hp'] <= 0: continue
                
                #damage taken from AoE
                damage_taken = aoe_damage_base
                damage_taken = max(50, damage_taken) #ensure minimum 50 damage
                player_run_stats['hp'] -= damage_taken
                player_run_stats['hp'] = max(0, player_run_stats['hp'])
                damage_taken_summary.append(f"{bot.get_user(user_id_int).display_name} 受到了 {damage_taken} 魔法傷害 (HP: {player_run_stats['hp']})")
        else: #regular magical attack
            for user_id_int in game_state['participants']:
                player_run_stats = game_state['players'][user_id_int]
                if player_run_stats['hp'] <= 0: continue

                damage_taken = enemy_damage_dealt_base
                player_run_stats['hp'] -= damage_taken
                player_run_stats['hp'] = max(0, player_run_stats['hp'])
                damage_taken_summary.append(f"{bot.get_user(user_id_int).display_name} 受到了 {damage_taken} 魔法傷害 (HP: {player_run_stats['hp']})")

    result_description += "\n" + "\n".join(damage_taken_summary) + "\n\n"

    #check if all players are defeated after enemy attack
    if all(player_stats['hp'] <= 0 for player_stats in game_state['players'].values()):
        result_description += "\n**💀 你們的隊伍全滅! 艾路owl 會送你們回互助會 💀**\n"
        combat_ended = True
        return result_description, combat_ended
    
    # --- PLAYER COUNTER-ATTACK LOGIC ---
    total_damage_to_enemy_this_round = 0
    detailed_combat_log = []
    
    detailed_combat_log.append(f"本輪傷害類型: **{current_event_template['combat_type'].capitalize()}**.")
    detailed_combat_log.append(f"{enemy_display_name} 防禦: **{current_enemy_data['defense']}**.") # enemy_display_name
    detailed_combat_log.append(f"RPS 攻擊結果: **{rps_outcome_text}** (傷害判定: {rps_multiplier:.1f})")

    #iterate through each active participant to apply their weapon effects for damage/healing
    for user_id_int in game_state['participants']:
        player_run_stats = game_state['players'][user_id_int]
        if player_run_stats['hp'] <= 0: #skip defeated players for their offensive turn
            continue

        user_data_obj = _get_user_data_db(user_id_int)
        equipped_weapon_id = user_data_obj.get('equipped_weapon')
        wielder_name = bot.get_user(user_id_int).display_name if bot.get_user(user_id_int) else f"User {user_id_int}"

        weapon_template = ALL_ITEM_TEMPLATES.get(equipped_weapon_id)
        
        player_raw_physical_damage = 0
        player_raw_magical_damage = 0
        player_healed_for = 0
        
        detailed_combat_log.append(f"\n--- {wielder_name}的回合 (武器: {weapon_template['name'] if weapon_template else 'None'}) ---")

        equipped_accessory_id = user_data_obj.get('equipped_accessory')
        if equipped_accessory_id == "latern":
            healing_amount = ACCESSORY_TEMPLATES["latern"]["special_skill"]["effect"]["hp_restore"]
            target_max_hp = user_data_obj['stats']['hp']
            healed_for = min(target_max_hp - player_run_stats['hp'], healing_amount)
            if healed_for > 0:
                player_run_stats['hp'] = min(target_max_hp, player_run_stats['hp'] + healing_amount)
                detailed_combat_log.append(f"💚✨ **{wielder_name}的自療提燈** 發出了微弱的光亮, 恢復了{healed_for} HP! (Current HP: {player_run_stats['hp']}).")
            else:
                detailed_combat_log.append(f"💚✨ **{wielder_name}的自療提燈** 嘗試治療，但{wielder_name}生命值已滿")

        if equipped_weapon_id:
            if equipped_weapon_id == "sword":
                player_raw_physical_damage = player_run_stats['strength']
                detailed_combat_log.append(f"🗡️ **{wielder_name} 的長鋏** 揮出了斬擊!")
            elif equipped_weapon_id == "staff":
                player_raw_magical_damage = player_run_stats['intelligence']
                detailed_combat_log.append(f"🪄 **{wielder_name} 的髡枝** 施放了法術!")
            elif equipped_weapon_id == "kronii":
                kronii_template = WEAPON_TEMPLATES["kronii"]
                
                #increment the counter for this player for this run
                player_run_stats['kronii_attack_counter'] += 1

                # Check if it's the 12th hit
                if (player_run_stats['kronii_attack_counter'] % 12) == 0:
                    #this is the mixed damage round
                    mixed_hit_spec = kronii_template['round_based_damage']['mixed_hit']
                    player_raw_physical_damage = player_run_stats['strength'] * mixed_hit_spec['strength_multiplier']
                    player_raw_magical_damage = player_run_stats['intelligence'] * mixed_hit_spec['intelligence_multiplier']
                    detailed_combat_log.append(f"**{wielder_name} 的時分** 在第12次攻擊時釋放出強大的斬擊!")
                else:
                    #this is a physical-only round (first 11 attacks of the cycle)
                    physical_multiplier_normal = kronii_template['round_based_damage']['physical_multiplier_normal']
                    player_raw_physical_damage = player_run_stats['strength'] * physical_multiplier_normal
                    detailed_combat_log.append(f"**{wielder_name} 的時分** 斬出物理攻擊 (攻擊循環: {player_run_stats['kronii_attack_counter'] % 12} of 11).")
            elif equipped_weapon_id == "fauna":
                if rps_multiplier > 0:
                    healing_amount = int(player_run_stats['faith'] * WEAPON_TEMPLATES["fauna"]["healing_multiplier"] * rps_multiplier) 
                    
                    #apply healing to ALL participants in the game state
                    for member_id in game_state['participants']:
                        target_player_run_stats = game_state['players'][member_id]
                        if target_player_run_stats['hp'] > 0:
                            target_user_data_obj = _get_user_data_db(member_id)
                            target_max_hp = target_user_data_obj['stats']['hp']
                            healed_for_target = min(target_max_hp - target_player_run_stats['hp'], healing_amount)
                            if healed_for_target > 0:
                                target_player_run_stats['hp'] = min(target_max_hp, target_player_run_stats['hp'] + healing_amount)
                                #accumulate total healing for this player's log
                                player_healed_for += healed_for_target
                                target_member_name = bot.get_user(member_id).display_name if bot.get_user(member_id) else f"User {member_id}"
                                detailed_combat_log.append(f"**{target_member_name}** 被 **{wielder_name}的 淬靈金果** 治療了 {healed_for_target} 生命值 (總生命值: {target_player_run_stats['hp']})。")
                            else:
                                target_member_name = bot.get_user(member_id).display_name if bot.get_user(member_id) else f"User {member_id}"
                                detailed_combat_log.append(f"**{target_member_name}** 嘗試治療，但生命值已滿。")
                else:
                    detailed_combat_log.append(f"**{wielder_name} 的淬靈金果** 因RPS結果無法治療。")
            elif equipped_weapon_id == "moom":
                dagger_template = WEAPON_TEMPLATES["moom"]
                num_hits = 1 #base hit
                for _ in range(dagger_template.get("max_extra_hits", 0)):
                    if random.random() < dagger_template.get("multi_hit_chance", 0):
                        num_hits += 1
                player_raw_physical_damage = player_run_stats['strength'] * num_hits
                detailed_combat_log.append(f"**{wielder_name} 的文明的進程** 攻擊了 {num_hits} 次!")
            elif equipped_weapon_id == "bae":
                #randomly choose between physical damage, magical damage, or healing
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
                enemy_total_hp = current_enemy_data['hp'] #use current_enemy_data['hp']
                enemy_hp_lost_percent = ((enemy_total_hp - game_state['enemy_current_hp']) / enemy_total_hp) * 100
                bonus_damage_multiplier = enemy_hp_lost_percent * damage_multiplier_per_hp_lost_percent

                player_raw_physical_damage = player_run_stats['strength'] * (1 + bonus_damage_multiplier)
                player_raw_magical_damage = player_run_stats['intelligence'] * (1 + bonus_damage_multiplier)
                detailed_combat_log.append(f"**{wielder_name}'s Voidwalker's Edge** scales with enemy HP lost!")
        else: # No weapon equipped
            player_raw_physical_damage = player_run_stats['strength'] #default bare-hand physical attack
            player_raw_magical_damage = player_run_stats['intelligence'] #default simple magical attack
            detailed_combat_log.append(f"**{wielder_name}** 沒有裝備武器，依靠基本攻擊")

        #apply RPS multiplier to raw damage, then defense for physical
        final_physical_damage = max(0, int(player_raw_physical_damage * rps_multiplier) - current_enemy_data['defense']) #use current_enemy_data['defense']
        final_magical_damage = int(player_raw_magical_damage * rps_multiplier)

        player_contributed_damage_this_player = final_physical_damage + final_magical_damage
        total_damage_to_enemy_this_round += player_contributed_damage_this_player
        
        detailed_combat_log.append(f"**{wielder_name}** 造成了 **{player_contributed_damage_this_player}** 傷害 ({final_physical_damage} 物理, {final_magical_damage} 魔法) 以及治療了 {player_healed_for} HP.")

    #apply accumulated total damage to enemy
    game_state['enemy_current_hp'] = max(0, game_state['enemy_current_hp'] - total_damage_to_enemy_this_round)
    #print(f"DEBUG: Total damage this round: {total_damage_to_enemy_this_round}, Enemy HP remaining: {game_state['enemy_current_hp']}")

    if detailed_combat_log:
        result_description += "\n**Combat Log:**\n" + "\n".join(detailed_combat_log) + "\n"

    if game_state['enemy_current_hp'] <= 0:
        enemy_name_display = "深淵暗影領主" if is_boss_fight else "敵人"
        result_description += f"\n**🌟 {enemy_name_display} 已被擊敗! 🌟**\n"
        for user_id_int in game_state['participants']:
            player_run_stats = game_state['players'][user_id_int]
            #rewards for defeating the enemy
            if is_boss_fight:
                player_run_stats['coins'] += 100
                player_run_stats['xp'] += 100
                
                #guaranteed Auto Healing Amulet drop for everyone
                user_data_obj = _get_user_data_db(user_id_int)
                if "latern" not in user_data_obj['inventory']:
                    user_data_obj['inventory']["latern"] = {"level": 1}
                    update_user_data(user_id_int, user_data_obj)
                    result_description += f"**{bot.get_user(user_id_int).display_name}** 撿到了: **{ALL_ITEM_TEMPLATES['latern']['name']}**!\n"
                else:
                    player_run_stats['coins'] += 5
                    result_description += f"**{bot.get_user(user_id_int).display_name}** 已經擁有 **自療提燈**, (+7 羽毛)\n"
            else:
                player_run_stats['coins'] += random.randint(10, 30)
                player_run_stats['xp'] += random.randint(20, 50)
                if random.random() < ITEM_DROP_CHANCE and GLOBAL_ITEM_POOL:
                    dropped_item_id = random.choice(GLOBAL_ITEM_POOL)
                    dropped_item_template = ALL_ITEM_TEMPLATES[dropped_item_id]
                    user_data_obj = _get_user_data_db(user_id_int)
                    if dropped_item_id not in user_data_obj['inventory']:
                        user_data_obj['inventory'][dropped_item_id] = {"level": 1}
                        update_user_data(user_id_int, user_data_obj)
                        result_description += f"**{bot.get_user(user_id_int).display_name}** 撿到了: **{dropped_item_template['name']}**!\n"
                    else:
                        result_description += f"**{bot.get_user(user_id_int).display_name}** 撿到了: **{dropped_item_template['name']}**, 但他已經有了 (+1 羽毛)\n"
                        player_run_stats['coins'] += 10
        update_user_data_file()

        game_state['enemy_current_hp'] = None
        game_state['enemy_data'] = None
        game_state['shop_current_items'] = []
        game_state['events_completed'] += 1
        game_state['consecutive_tie_count'] = 0

        if is_boss_fight:
            combat_ended = True
            game_state['boss_current_phase'] = None #reset boss phase
            game_state['boss_phase_transitioned'] = False
        else:
            combat_ended = False #regular enemy defeat continues the run

    else: #combat continues if enemy is alive
        result_description += f"\n_{enemy_display_name} 剩餘 **{game_state['enemy_current_hp']} HP** 請自求多福!_\n"
        #combat is not ended, do not increment events_completed
        combat_ended = False

    return result_description, combat_ended


async def process_event_results(channel_id: int):
    if channel_id not in active_questionnaires: return

    channel = bot.get_channel(channel_id)
    game_state = active_questionnaires[channel.id]
    if not channel: return

    votes = game_state['votes']
    current_event_id = game_state['current_event_id']
    event_data = GAME_EVENTS.get(current_event_id)

    #clear reactions from the previous prompt message
    try:
        previous_message = await channel.fetch_message(game_state['prompt_message_id'])
        await previous_message.clear_reactions()
    except (discord.Forbidden, discord.HTTPException):
        pass #ignore errors if bot can't clear reactions or message is gone

    if not event_data:
        embed = discord.Embed(
            title="Game Error: Path Vanished", description="An internal error occurred with the adventure. Ending it prematurely.", color=discord.Color.red()
        )
        await channel.send(embed=embed)
        del active_questionnaires[channel.id]
        return

    #determine the winning emoji from votes
    vote_counts = {emoji_code: 0 for emoji_code in GAME_EMOJIS.values()}
    for user_id, emoji_reacted_with in votes.items():
        if emoji_reacted_with in vote_counts:
            vote_counts[emoji_reacted_with] += 1

    relevant_emojis = []
    if current_event_id == "shop_encounter":
        for i in range(len(game_state['shop_current_items'])): #use shop_current_items to determine valid emojis
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
    
    #process the chosen option or handle ties
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
                game_state['events_completed'] += 1 #count leaving shop as an event for display
                game_state['shop_current_items'] = [] #clear shop items for next encounter
                await channel.send(embed=discord.Embed(description=result_description, color=discord.Color.blue()))
                await send_next_event(channel)
                return
            else:
                try:
                    item_index = int(chosen_option_key) - 1
                    item_id = game_state['shop_current_items'][item_index]
                except (ValueError, IndexError):
                    item_id = None #invalid item selection

                item = SHOP_ITEMS.get(item_id)
                if item:
                    successful_purchasers = []
                    failed_purchasers = []
                    
                    for user_id_int in game_state['participants']:
                        member = bot.get_user(user_id_int)
                        member_name = member.display_name if member else f"User {user_id_int}"
                        
                        user_data_obj = _get_user_data_db(user_id_int)
                        player_run_stats = game_state['players'][user_id_int]

                        if user_data_obj['coins'] >= item['cost']: #check persistent coins
                            user_data_obj['coins'] -= item['cost']
                            
                            #apply effects
                            for stat, change in item['effect'].items():
                                if stat in ['hp', 'strength', 'defense', 'intelligence', 'faith']:
                                    player_run_stats[stat] = player_run_stats.get(stat, 0) + change
                                elif stat in ['coins', 'xp']: #Coins and XP are still persistent
                                    user_data_obj[stat] = user_data_obj.get(stat, 0) + change
                                    player_run_stats[stat] = player_run_stats.get(stat, 0) + change #update run stats for display

                            update_user_data(user_id_int, user_data_obj) #call unified update function
                            successful_purchasers.append(member_name)
                        else:
                            failed_purchasers.append(member_name)
                    
                    if successful_purchasers:
                        result_description += f"**{' and '.join(successful_purchasers)}** 已購入 **{item['name']}**!\n"
                        result_description += f"物品的臨時效果已被觸發\n"
                    if failed_purchasers:
                        result_description += f"**{' and '.join(failed_purchasers)}** 沒有足夠羽毛 (需要{item['cost']}) 而無法購買  **{item['name']}**\n"

                    #remove the purchased item from the current shop's inventory
                    if item_id in game_state['shop_current_items']:
                        game_state['shop_current_items'].remove(item_id)

                    update_user_data_file()
                    result_description += "\n To be continue..."
                    #after attempted purchase, re-display shop with updated items (or proceed if all items are gone)
                    await channel.send(embed=discord.Embed(description=result_description, color=discord.Color.blue()))
                    await send_next_event(channel) # Re-send the shop event
                    return
                else:
                    result_description += f"Invalid shop item selected"
                    await channel.send(embed=discord.Embed(description=result_description, color=discord.Color.red()))
                    await send_next_event(channel) #resend shop event
                    return
        #handle all combat types here
        elif 'combat_type' in event_data:
            round_description, combat_ended = await _process_combat_round(channel, game_state, chosen_option_key)
            result_description += round_description

            await channel.send(embed=discord.Embed(description=result_description, color=discord.Color.dark_red() if not combat_ended else discord.Color.gold()))

            if combat_ended:
                await _send_run_summary(channel, game_state)
            else:
                await send_next_event(channel) #continue combat
            return #exit after handling combat
        else: #non-combat, non-shop
            #add a default description to ensure the embed is never empty
            result_description += f"你選擇了'{event_data['options'][chosen_option_key]['text']}'. "
            
            if event_data['options'][chosen_option_key].get('effect'):
                effect_changes_display = []
                for user_id_int in game_state['participants']:
                    player_run_stats = game_state['players'][user_id_int]
                    if player_run_stats['hp'] > 0: #only apply effects to alive players
                        for stat, change in event_data['options'][chosen_option_key]['effect'].items():
                            #apply to persistent data for XP and Coins
                            if stat in ['coins', 'xp']:
                                #update persistent data for coins/xp
                                user_data_obj = _get_user_data_db(user_id_int)
                                user_data_obj[stat] = user_data_obj.get(stat, 0) + change
                                update_user_data(user_id_int, user_data_obj)
                                #update run stats for display during the current run
                                player_run_stats[stat] = player_run_stats.get(stat, 0) + change
                            else: #temporary buffs, applied only to run_stats
                                player_run_stats[stat] = player_run_stats.get(stat, 0) + change
                            effect_changes_display.append(f"{'+' if change >= 0 else ''}{change} {stat.capitalize()}")
                if effect_changes_display:
                    #remove duplicate entries for cleaner display
                    result_description += f"**效果:** {', '.join(sorted(list(set(effect_changes_display))))} (所有成員都可以享有效果)\n"
                else:
                    result_description += "無其他效果"
                update_user_data_file()
            
            game_state['events_completed'] += 1
            game_state['shop_current_items'] = []
            
            #if the chosen option leads to a specific next event, handle that
            if event_data['options'][chosen_option_key].get('next_id') and event_data['options'][chosen_option_key].get('next_id') != "random_event":
                game_state['current_event_id'] = event_data['options'][chosen_option_key].get('next_id')
                await channel.send(embed=discord.Embed(description=result_description, color=discord.Color.blue()))
                await send_next_event(channel, force_current=True) #go to the specific next event
            else:
                game_state['current_event_id'] = random.choice(ALL_PLAYABLE_EVENT_IDS) #default to random event
                await channel.send(embed=discord.Embed(description=result_description, color=discord.Color.blue()))
                await send_next_event(channel)
            return
    else: #tie in voting
        game_state['consecutive_tie_count'] += 1 #increment tie counter
        
        if game_state['consecutive_tie_count'] >= 2: #if 2 or more consecutive ties
            result_description += "隊伍因意見不合發生爭執 一番文明友善且和平的溝通後 全員陣亡 冒險結束！\n"
            await channel.send(embed=discord.Embed(description=result_description, color=discord.Color.dark_red()))
            await _send_run_summary(channel, game_state)
            return #end the game
        else:
            remaining_ties = 2 - game_state['consecutive_tie_count']
            result_description += f"**平局！** 隊伍陷入選擇困難! 或者有人手賤按錯!\n 隨便啦 反正你們還有{remaining_ties}次機會\n"
            
            if current_event_id == "shop_encounter":
                result_description += "請重新投票或選擇離開商店。"
            elif 'combat_type' in event_data: #if combat event and tie
                result_description += f"_{'深淵暗影領主' if current_event_id.startswith('abyssal_shadow_lord') else '敵人'} 仍有 **{game_state['enemy_current_hp']} 生命值** 剩餘。請自求多福！_\n"
            else:#shop
                result_description += "事件將重新開始，請再次投票！\n"
            
            #don't increment events_completed, stay on the same event
            await channel.send(embed=discord.Embed(description=result_description, color=discord.Color.dark_grey()))
            await send_next_event(channel, force_current=True)
            return

    await _send_run_summary(channel, game_state) # end to prevent infinite loop

async def _send_run_summary(channel: discord.TextChannel, game_state: dict):
    summary_description = f"**冒險總結!**\n\n"
    
    for user_id_int, player_run_stats in game_state['players'].items():
        user_id_str = str(user_id_int)
        member = bot.get_user(user_id_int)
        name = member.display_name if member else f"User {user_id_int}"

        user_data_obj = _get_user_data_db(user_id_int) 
        user_data_obj['stats']['xp'] = user_data_obj['stats'].get('xp', 0) + player_run_stats.get('xp', 0)
        user_data_obj['coins'] = player_run_stats['coins']
        user_data_obj = _check_level_up(user_data_obj)
        user_data_obj['physical_damage_tracker'] = 0
        update_user_data(user_id_int, user_data_obj) #call unified update function

        summary_description += f"**{name}**: 獲得了 **{player_run_stats.get('xp', 0)}** XP\n"
        summary_description += f"   *現時等級*: Level: {user_data_obj['level']}\n"
    update_user_data_file()
        
    summary_embed = discord.Embed(
        title="冒險結束",
        description=summary_description,
        color=discord.Color.gold()
    )
    summary_embed.set_footer(text=f"你的進程已被儲存 此頻道將在30秒後刪除")
    await channel.send(embed=summary_embed)
    
    #remove the game state as the run has concluded
    if channel.id in active_questionnaires:
        del active_questionnaires[channel.id] 

    #wait for 30 seconds before delete
    await asyncio.sleep(30)
    try:
        if channel.id in temporary_text_channels: #defensive check
            del temporary_text_channels[channel.id]
        await channel.delete()
        print(f"Deleted RPG channel: {channel.name} ({channel.id}) after game conclusion.")
    except discord.Forbidden:
        print(f"Bot lacks permissions to delete RPG channel: {channel.name} ({channel.id}).")
    except discord.HTTPException as e:
        print(f"Failed to delete RPG channel {channel.name} ({channel.id}): {e}")

@bot.command(name='pg', help='RPG, 建立冒險小隊 用法: owl pg')
async def rpg(ctx, name: str = "rpg-adventure", category_id: int = None):

    if ctx.channel.id != config["default_channel_id"]:
        return

    if not ctx.guild:
        await ctx.send("This command can only be used in a server.")
        return

    #resolve category
    category = None
    if category_id:
        category = bot.get_channel(category_id)
        if not isinstance(category, discord.CategoryChannel):
            await ctx.send(f"❌ Category ID `{category_id}` is not a valid category. Please provide a valid category ID or omit it.")
            return
    elif ctx.channel.category:
        category = ctx.channel.category
    elif ctx.guild.categories:
        category = ctx.guild.categories[0]

    #check if the bot has permissions to manage channels in the target category
    target_parent = category if category else ctx.guild
    if not target_parent.permissions_for(ctx.guild.me).manage_channels:
        await ctx.send("I need 'Manage Channels' permission to create private channels in that category Please grant me this permission. @st!!!")
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

    #store the request details including the message ID and the initial organizer
    private_channel_requests[request_message.id] = {
        'organizer_id': ctx.author.id,
        'name': name,
        'category_id': category.id if category else None,
        'users': {ctx.author.id},
        'creation_initiated': False
    }

@bot.command(name='profile', help='View your profile and stats.')
async def profile(ctx):
    user_id = ctx.author.id
    user_profile = _get_user_data_db(user_id)

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
            calculated_stats = _calculate_item_stats(equipped_weapon_id, weapon_level)
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
            calculated_stats = _calculate_item_stats(equipped_armor_id, armor_level)
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

@bot.command(name='inv', help='你的背包~背到現在還沒爛~ 用法: owl inv')
async def inventory(ctx):
    user_id = ctx.author.id
    user_profile = _get_user_data_db(user_id)
    
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
                status.append("EQUIPPED WEAPON")#check for equip
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
    #embed.set_footer(text="Use owl equip [item_id] to equip an item or owl upgrade [item_id] to upgrade it.")
    await ctx.send(embed=embed)

@bot.command(name='equip', help='裝備物品 用法: !equip [item_id]')
async def equip(ctx, item_id: str):
    user_id = ctx.author.id
    user_profile = _get_user_data_db(user_id)

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

    update_user_data(user_id, user_profile) #call unified update function
    update_user_data_file() #save changes to file
    item_name = item_template['name']
    await ctx.send(f"✅ 你已裝備 **{item_name}**! (替換了 {old_equipped_item_name}).")

@bot.command(name='unequip', help='解除裝備 用法: owl unequip [type: weapon/armor/accessory]')
async def unequip(ctx, item_type: str):
    user_id = ctx.author.id
    user_profile = _get_user_data_db(user_id)
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
    update_user_data_file()


@bot.command(name='upgrade', help='裝備升級/進化 用法: owl upgrade [item_id]')
async def upgrade(ctx, item_id: str):
    """Upgrades a specified item in the user's inventory."""
    user_id = ctx.author.id
    user_profile = _get_user_data_db(user_id)

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
    max_level = item_template.get('max_level', 5) #default max level
    
    if current_level >= max_level:
        #check for evolution
        if "evolves_to" in item_template:
            evolved_item_id = item_template['evolves_to']
            evolved_item_template = ALL_ITEM_TEMPLATES.get(evolved_item_id)
            if evolved_item_template:
                evolution_cost = int(item_template['upgrade_cost_multiplier'] * 1500 * current_level) #higher cost for evolution

                if user_profile['coins'] >= evolution_cost:
                    user_profile['coins'] -= evolution_cost
                    
                    #add evolved item to inventory at level 1
                    user_profile['inventory'][evolved_item_id] = {"level": 1}
                    
                    #remove the old item
                    del user_profile['inventory'][item_id_lower]

                    #if the old item was equipped, equip the new evolved item
                    if user_profile.get('equipped_weapon') == item_id_lower:
                        user_profile['equipped_weapon'] = evolved_item_id
                    elif user_profile.get('equipped_armor') == item_id_lower:
                        user_profile['equipped_armor'] = evolved_item_id

                    update_user_data(user_id, user_profile) #update and save
                    update_user_data_file()
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
        user_profile['coins'] -= upgrade_cost
        item_data['level'] += 1
        user_profile['inventory'][item_id_lower] = item_data
        update_user_data(user_id, user_profile)
        update_user_data_file()

        new_stats = _calculate_item_stats(item_id_lower, item_data['level'])
        stats_display = ", ".join([f"{s.capitalize()}: {v}" for s, v in new_stats.items()])

        await ctx.send(f"✅ 成功升級 **{item_template['name']}** 至等級 {item_data['level']}")
    else:
        await ctx.send(f"💰 你需要 {upgrade_cost} 羽毛才可以升級 **{item_template['name']}** 至等級 {current_level + 1}.")

@bot.command(name='tune', help='分配屬性點 用法:  owl tune [stat_name] [amount]')
async def distribute_points(ctx, stat_name: str, amount: int):
    """
    Distributes stat points gained from leveling up to a specified stat.
    """
    user_id = ctx.author.id
    user_profile = _get_user_data_db(user_id)

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
    
    #1 stat point gives 2 HP
    if stat_name_lower == 'hp':
        user_profile['stats']['hp'] = user_profile['stats'].get('hp', 0) + (amount * 2)
    else:
        user_profile['stats'][stat_name_lower] = user_profile['stats'].get(stat_name_lower, 0) + amount
    
    user_profile['stat_points'] -= amount
    update_user_data(user_id, user_profile)
    update_user_data_file()

    await ctx.send(f"✅ 成功分配 {amount} 屬性點 至 **{stat_name_lower.capitalize()}**! 你現有 {user_profile['stats'][stat_name_lower]} {stat_name_lower.capitalize()} 和 {user_profile['stat_points']} 屬性點剩餘")


@bot.command(name='reset_sp', help='重置你的屬性點，花費你10%的羽毛。用法: owl reset_sp')
async def reset_sp(ctx):
    """
    Resets a player's spent stat points, returning them all and resetting stats to base level 1 values.
    Costs 10% of the player's current coins.
    """
    user_id = ctx.author.id
    user_profile = _get_user_data_db(user_id)

    cost = int(user_profile['coins'] * 0.10) # 10% of current coins
    
    min_cost = 1000 
    cost = max(cost, min_cost)

    if user_profile['coins'] < cost:
        await ctx.send(f"❌ 重置屬性點需要 {cost} 羽毛，但你只有 {user_profile['coins']} 羽毛。")
        return

    #deduct the cost
    user_profile['coins'] -= cost

    user_profile['stats']['hp'] = INITIAL_PLAYER_PROFILE['stats']['hp']
    user_profile['stats']['strength'] = INITIAL_PLAYER_PROFILE['stats']['strength']
    user_profile['stats']['defense'] = INITIAL_PLAYER_PROFILE['stats']['defense']
    user_profile['stats']['intelligence'] = INITIAL_PLAYER_PROFILE['stats']['intelligence']
    user_profile['stats']['faith'] = INITIAL_PLAYER_PROFILE['stats']['faith']

    # refund all stat points earned from leveling up
    #(N-1) stat points.
    user_profile['stat_points'] = max(0, user_profile['level'] - 1)

    update_user_data(user_id, user_profile)
    update_user_data_file()

    await ctx.send(
        f"✅ 你的屬性點已成功重置！你花費了 {cost} 羽毛。\n"
        f"所有屬性已重置為基礎值，你現在有 **{user_profile['stat_points']} 屬性點** 可以重新分配。\n"
        f"使用 `owl tune [屬性名稱] [數量]` 重新分配你的點數。"
    )

def get_user_avatar(user):
    return user.avatar.url if user.avatar else user.default_avatar.url


@bot.command(name="pray", help = "貓頭鷹抽籤")
@commands.cooldown(1, 7200, commands.BucketType.user)
async def pray(ctx):
    if ctx.channel.id != config["pray_channel_id"]:
        return

    result = random.randint(1, 7)

    fortunes = {
        1: ("大凶", 10, "大凶？！勸你還是乖乖在家不要出門吧！", 10),
        2: ("凶", 20, "啊！凶嗎...不是有句話是：「人有旦夕禍...」後面我忘了...", 20),
        3: ("末吉", 30, "末吉？或許可以多做做善事累積點陰德與福氣呢！", 30),
        4: ("吉", 40, "介於中間的吉嗎？平平安安結束一天也是種福氣呢！", 40),
        5: ("小吉", 50, "穩定的小吉呢！今天應該會是個簡單平順的一天吧！", 50),
        6: ("中吉", 60, "中吉耶！今天的你說不定會有什麼小確幸哦！", 60),
        7: ("大吉", 70, "竟然是大吉嗎?!你或許是綜觀全人類中數一數二幸運的人呢！", 70)
    }

    message, coins, comment, feather_count = fortunes[result]

    lucky_number = random.randint(0, 9)

    lucky_colors = [
        "紅色", "藍色", "黃色", "綠色", "紫色", "粉色",
        "橘色", "青色", "金色", "銀色", "白色", "黑色"
    ]
    lucky_color = random.choice(lucky_colors)

    user_id = str(ctx.author.id)
    user_data[user_id] = user_data.get(user_id, {"coins": 0})
    user_data[user_id]["coins"] += coins
    
    update_user_data_file()

    color_map = {
    "紅色": discord.Color.from_rgb(255, 0, 0),
    "藍色": discord.Color.from_rgb(0, 102, 204),
    "黃色": discord.Color.from_rgb(255, 221, 0),
    "綠色": discord.Color.from_rgb(0, 204, 102),
    "紫色": discord.Color.from_rgb(153, 102, 255),
    "粉色": discord.Color.from_rgb(255, 153, 204),
    "橘色": discord.Color.from_rgb(255, 140, 0),
    "青色": discord.Color.from_rgb(0, 255, 255),
    "金色": discord.Color.from_rgb(255, 215, 0),
    "銀色": discord.Color.from_rgb(192, 192, 192),
    "白色": discord.Color.from_rgb(255, 255, 255),
    "黑色": discord.Color.from_rgb(20, 20, 20)
}

    lucky_color = random.choice(list(color_map.keys()))
    embed_color = color_map.get(lucky_color, discord.Color.default())

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

    image_map = {
    "大吉": "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEimpKtspceL47HWV8CIjCG83OLzaXss2VrjPQt65pfItad0LzQVB13lABAZ8zvViixYeemTkX9O3F2W9vfmDrv2u00nRzGmVD4OIj81oM6zOk84edl8Loj2BvpLIkT4TgWCiPJr4YMSzQZE/s1600/omikuji_daikichi.png",
    "中吉": "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEjDPy0X_GAJUV8pauG2Pwpn1dC5O7FfDAJdfDQNxcDB2JpPK85arrtw_qaLKdlvD1YQ9KqkHVrWe_Yfo1hJbYOQNwp8Zb-IZmaISp7_jFDX9pwXINlc7aJtIrlwEAMk6lCkQbweriNT9Lvx/s1600/omikuji_chuukichi.png",
    "小吉": "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEhhjqxIjcS2_4hGG8FLlhHSDe1pnMU-XeAXEGWUy10y8Nj-Ohhuchx2ZqxYmPcW2FexxQAdbPyVbJvyCqnAbJ9_DGY7nN3WK0-P0Rz8UlfeouDwdfqgjlx0cBtwXWrTLe7zY8JUGciZcia8/s1600/omikuji_syoukichi.png",
    "吉": "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEgablBON0p3T-N_SO2UoPe8MSmCLzGEUlntQIbe1CNzzzapUDo8bky9O4MQqvj_B0wygWh0mgFVlH6WTM-ovapykZUPabAHWT73KfAnViUAaUSBMdEveRAzJRVaAiMbA8ZxyoKCujlj9iqx/s800/omikuji_kichi.png",
    "末吉": "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEglx-IJtiH6CUGvdXF6GAfm_Sh8mbWExuxTjGKhWZbbVk8oiJNWfkXNqSg8v8rreg7cdRN5v8RyMpVPPl_y4GAlCDx0YHia7rtMs5QfOE7qiX8_pdi3xv-9mYanwTjNBOg2WFrEgiIo8RcI/s1600/omikuji_suekichi.png",
    "凶": "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEjYwJAbs5msucqL3TQJEYwCuR7ehewBO-F9HuYH_ERwC9wgzSCHUG3EEUvwF9A281BjEG02Lp8tDY4bKdoTDvr1j-QA78qQXN-DKolTIfj97z2zvFDWC3gJBOHfrdW3hgrXPsMS5yli-Sqo/s1600/omikuji_kyou.png",
    "大凶": "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEiM7jD5fZAfHSZ6vk0KH99puqk6oQNcwCgmImN28pHYZey7VxVDIlSnF5ZKxrBx0GVVCyIJXlSRR46S3U3_xMex4LIVAHB_kYJHpJ3RVxjEQLZUEUl6R0B3QidHyZazb-rhwzJxRzI_d6xe/s1600/omikuji_daikyou.png"
    }

    image_url = image_map.get(message)
    if  image_url:
        embed.set_image(url = image_url)

    embed.set_footer(text = f"{ctx.author.display_name} 的幸運簽", icon_url = get_user_avatar(ctx.author))

    response_message = await ctx.send(embed=embed)
    await response_message.add_reaction("<:MumeiPray:878706690525134878>")



@bot.command(name = "slots", help = "拉霸(50羽毛一次)")
async def slots(ctx):
    if ctx.channel.id == config["slots_channel_id"]:
        user_id = str(ctx.author.id)
        user_info = user_data.get(user_id, {"coins": 0})

        if user_info["coins"] < 50:
            await ctx.send("你都Mei 錢了還賭哦<:0_AOA:897482887341965343>")
            return

        user_info["coins"] -= 50
        
        update_user_data_file()

        symbols = ["🪐", "🪶", "🌿", "⌛", "<:0_Berries:893198899995607110>", "🎲"]
        result = [random.choice(symbols) for _ in range(5)]
        await ctx.send(" ".join(result))

        counts = {symbol: result.count(symbol) for symbol in set(result)}
        best_symbol = max(counts, key=counts.get)
        match_count = counts[best_symbol]

        winning = {
            5: (5050, f"🌟 哇靠! 歐皇! {ctx.author.display_name} 贏了5000根羽毛!"),
            4: (550, f"🔥哇! 四個 {best_symbol} {ctx.author.display_name} 贏了500根羽毛!"),
            3: (100, f"✨三個 {best_symbol}! {ctx.author.display_name} 贏了50根羽毛!"),
            2: (25, f"一對 {best_symbol}, 不過還是輸了25根羽毛"),
        }

        if match_count in winning:
            win_amount, message = winning[match_count]
            user_info["coins"] += win_amount
            await ctx.send(f"{message}")
        else:
            await ctx.send("💔 Mei 了, 全Mei 了! 💔")

        update_user_data_file()



@bot.command(name="balance", help = "看看自己身上有多少羽毛")
async def balance(ctx):
    user_id = str(ctx.author.id)
    user_info = user_data.get(user_id, {"coins": 0})
    balance = user_info["coins"]

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

@bot.command(name="donate", help="投sc")
async def donate(ctx, amount: int):
    if amount <= 0:
        await ctx.send("請輸入一個正確的數量來捐贈。")
        return

    user_id = str(ctx.author.id)
    user_data[user_id] = user_data.get(user_id, {"coins": 0})

    if user_data[user_id]["coins"] < amount:
        await ctx.send(f"不! 能! 把! 房! 租! 錢! 用! 來! 投! SC! <:0_Angy:902486572895711242>")
        return

    user_data[user_id]["coins"] -= amount
    bot_id = str(bot.user.id)
    user_data[bot_id] = user_data.get(bot_id, {"coins": 0})
    user_data[bot_id]["coins"] += amount
    
    update_user_data_file()

    donation_total = user_data[bot_id]["coins"]
    await bot.change_presence(activity=discord.Game(name=f"{donation_total} 根羽毛"))

    embed = discord.Embed(
        description=(f"感謝你抖內了 {amount} 根羽毛！")
    )
    await ctx.send(embed=embed)


@bot.command(name="rank", help = "看看排名前十的佬有多富")
async def rank(ctx):
    sorted_user_data = sorted(user_data.items(), key = lambda x: x[1]["coins"], reverse = True)

    leaderboard_text = f"{'排名':<4} {'成員':<26} {'數量':>6}\n"
    leaderboard_text += "=" * 45 + "\n"

    for rank, (user_id, data) in enumerate(sorted_user_data[:10], start=1):
        user = bot.get_user(int(user_id))
        username = user.name if user else "N/A"
        balance = data["coins"]

        leaderboard_text += f"{rank:<4}  {username:<30}  {balance}\n"

    embed = discord.Embed(
        title="🪶貓頭鷹十傑🪶\n 伺服器中羽毛蒐集量前十名",
        description=f"```{leaderboard_text}```",
        color=discord.Color.from_str("#A0522D")

    )
    await ctx.send(embed=embed)


@bot.command(name = "hunt", help = "獵'人'")
@commands.cooldown(1, 600, commands.BucketType.user)
async def hunt(ctx):
    if ctx.channel.id != config["hunt_channel_id"]:
        return
    
    user_id = str(ctx.author.id)
    user_data[user_id] = user_data.get(user_id, {"coins": 0})
    
    result = random.randint(1, 24)

    hunting = {
        1: (" 你四處飛行，從高處尋找著目標\n 左看右看，上看下看，不放過任何一舉一動。 ", 0, "然而你沒有遇到任何目標，一天就這麼結束了...", 0),
        2: (" 在你尋找目標的時候，你遇到了Friend！\n 你們兩個決定一起行動，有了Friend的陪伴，你覺得很有安全感。", 0, "你沒有遇到任何目標，但你與Friend度過了愉快的一天。", 0),
        3: ("「竟然想要身為『議長』我的羽毛？真是不知天高地厚！不過拿咖啡和炸起司條跟我交換倒是可以考慮...」\n 你買了一杯咖啡和一包炸起司條給她，她看起來很開心，馬上拿羽毛跟你交換。", 15, " 你蒐集到了紅色的老鼠毛！", 15),
        4: ("「哈哈哈哈wwww，狩獵什麼的感覺好有趣wwww」\n ころね一邊笑著，一邊將羽毛分給了你，你走之後她看起來還是很開心。", 20, "你蒐集到了咖啡色狗毛！", 20),
        5: ("「ぽぽぽぽぽぽぽ～」ポルカ目前正在舞台上賣力表演。\n 看完了充滿活力的演出後，你在舞台上撿到了ポルカ的羽毛。", 25, "你蒐集到了淡黃色的耳廓狐毛！", 25),
        6: ("「ばくーん！你說什麼？狩獵？！やだやだやだやだ！」\n一聽到你是來狩獵的，沙花叉驚慌失措的跳到海裡，並且迅速的游走了。", 0, "你沒能成功蒐集到虎鯨的羽毛，虎鯨大概也沒羽毛吧...？", 0),
        7: ("「白上是狐狸，不是貓！Friend! Friend! Not Waifu!」\n フブキ貌似很在意你把她認成貓了，不過道歉之後她還是慷慨的分了你羽毛。", 20, "你蒐集到了白色貓...不對是狐狸毛！", 20),
        8: ("「想要余的羽毛？余可是沒有那種東西呦。」\n 雖然沒有羽毛，不過あやめ還是分給了你一點她的頭髮。", 25, "你蒐集到了白色的...余毛...？", 25),
        9: ("「わためは...可是沒有錯的哦～」\n 不知為何，你感覺到不管這隻可愛的羊做了什麼，她都不會有錯的。", 30, "你蒐集到了淡黃色的羊毛！", 30),
        10: ("「想要羽毛？真是貪婪的傢伙，但我並不討厭那樣的貪婪。」\n 「太帥了吧...」你一邊這麼認為，一邊接過她遞給你的羽毛。", 30, "你蒐集到了黑色狐狸毛！", 30),
        11: ("「You are king!」你聽見了Risu強而有力的歌聲，與平常的她截然不同。\n 聽完演唱後，你問她可不可以給你羽毛，她以為你是她的粉絲，很果斷地就給你了。", 20, "你蒐集到了咖啡色的松鼠毛！", 20),
        12: ("「ミオ呀，可不是獵物呦～」\n 說是這麼說，她還是分了你一點羽毛，不愧是麻麻。", 25, "你蒐集到了黑色狼毛！", 25),
        13: ("「こんルイルイ！怎麼了嗎？看你一臉沮喪的樣子，有什麼煩惱可以跟我ルイ說哦！」\n 在經過半天毫無收穫的鬱悶之際，你巧遇了ルイ。瞭解了你的遭遇後，她熱心的與你分享了有關狩獵的感想，並給了你一些羽毛。", 25, "你蒐集到了粉橘色的老鷹羽毛！", 25),
        14: ("「スバ！！スバル不是什麼鴨子啊！」\n 儘管她不斷的澄清，不過這隻可愛的鴨子還是分給你一點羽毛。", 20, "你蒐集到了白色的鴨毛！", 20),
        15: ("「恩？想要我的羽毛？可以呦！來，給你吧～」\n Reine 將她的羽毛拿給了你。她的言行舉止非常優雅，就如同是個大小姐一般。", 20, "你蒐集到了銀色的孔雀毛！", 20),
        16: (" 你來到了VR Chat的神奇空間，並遇到了穿著南瓜裝的Smol Ame！\n 她看起來很開心，你們伴隨著音樂舞動著身體，像是在開Party一樣。", 30, "過了一段時間，Party結束了，Ame塞了一點糖果給你當作紀念品，就這樣離開了。", 30),
        17: ("「KIKKERIKIIII～想要我不死鳳凰的羽毛？只要你來KFP幫忙的話我可以考慮哦～」\n 於是你去KFP打了一整天的工，工資是Kiara的羽毛。", 30, "你蒐集到了橘紅色的鳳凰毛！", 30),
        18: ("「放開我ぺこ！快點放開我ぺko！ぺkoら可不是什麼糧食啊ぺko！！」\n 跟她解釋沒有要吃掉之後，她發出了「ぺこぺkoぺko」的囂張聲音後給了你一點羽毛。", 35, "你蒐集到了白色的兔子毛！", 35),
        19: ("「不要這樣捏！みこ不是獵物捏！！」\n 伴隨著黑武士的《帝國進行曲》，みこ躲進了她的魔王城中。", 1, "你在地上撿到了...みこ的粉紅呆毛...?", 1),
        20: ("「嗯？想要我的羽毛嗎？可以喔～Poi(丟)」\n 她一邊講「Poi」，一邊將手上的手榴彈丟了出去，你覺得此地很危險，拿完羽毛後就離開了", 25, "你蒐集到了乳白色的獅毛！", 25),
        21: (" 你來到了一個神祕的實驗室...打開門碰到了身穿實驗袍的Ina！\n她手上拿著神祕的藥水，希望你幫她做個小實驗，於是她將藥水滴到你頭上。", 40, "沒想到你變成了Takodachi！她馬上把你變回原狀，並塞了一些羽毛給你當作補償。", 40),
        22: (" 在你飛在空中尋找目標的時候，你發現有一隻橘色的龍在你不遠處翱翔。\n 雖然體型、種族與你差異巨大，但你卻不會害怕，因為你知道那條龍是不會傷害你的。", 50, "你見到了傳說中的龍，心中充滿了尊敬。你也在不遠處的地面上找到了橘色龍鱗。", 50),
        23: ("「こんこよ～ 這麼晚了還在森林裡是迷路了嗎？ 嘿？羽毛嗎~可以哦，如果你願意當我的助手君的話(ㆆ▿ㆆ)」\n 雖然こより一臉在謀劃什麼的表情，你還是尾隨她進入了她的秘密實驗室。在經歷了一連串的藥物試驗與身體檢測後，你拖著疲憊不堪的身軀到早上才回家。", 54, "你蒐集到了粉紅色的郊狼毛！", 54),
        24: ("偷取中...", 74, "偷取中...", 74)
    }

    message, coins, comment, feather_count = hunting[result]


    feathers = feather_count

    if result == 24:
       eligible_targets = [
           uid for uid in user_data
           if uid != user_id and user_data[uid].get("coins", 0) > 74 #added .get(coins, 0) for safety
       ]
       if eligible_targets:
           target_id = random.choice(eligible_targets)
           user_data[target_id]["coins"] -= 74
           target_user = bot.get_user(int(target_id))
           target_name = target_user.name if target_user else "某個人"

           message = f"你在森林裡遇到了 {target_name},\n 一番文明且友好的交流後, 你拿到了一些羽毛"
           comment = f"你從 {target_name} 那裡蒐集到了一些羽毛！"
           feather_count = 74
       else:
           message = "你四處尋找可偷的人，但森林空無一人。沒有找到可以偷取羽毛的對象。"
           comment = "你想偷羽毛，但沒有人可以偷。"
           feather_count = 0

    user_data[user_id]["coins"] += feathers
    
    update_user_data_file()

    embed = discord.Embed(
        title="——狩獵結果——",
    )
    embed.add_field(name="▲事件", value=message, inline=False)
    embed.add_field(name="▲結果", value=comment, inline=False)
    embed.add_field(name="▲你得到了", value=f"{feathers} 根羽毛 🪶", inline=False)
    embed.set_thumbnail(url=get_user_avatar(ctx.author))

    image_map = {
    1: "https://cdn.discordapp.com/attachments/883708922488315924/887948965797048340/mumei.png?ex=6803436a&is=6801f1ea&hm=0b5fdf4fb35b33c0368e043bda2dfa155da09f01f1381077d95231257ba10587&",
    2: "https://cdn.discordapp.com/attachments/883708922488315924/887947855711567872/fukuro.png?ex=68034262&is=6801f0e2&hm=73f4c7b11fa4977dd27a131a14248760d1fb109bcd27fd5b60d79f2cc3f12643&",
    3: "https://cdn.discordapp.com/attachments/883708922488315924/887945499544543242/baelz.jpg?ex=68034030&is=6801eeb0&hm=0d5220f7fd84e3d9ffae5858a0e688117b5b8df7aeb8a098a4178734bb802377&",
    4: "https://cdn.discordapp.com/attachments/883708922488315924/887795059326611466/korone.jpg?ex=68035cd4&is=68020b54&hm=78c710d5a213603f336e50696ca04dbb98732bccc48f794baef52d5fd378a4aa&",
    5: "https://cdn.discordapp.com/attachments/883708922488315924/887905128542240768/polka.png?ex=6803c357&is=680271d7&hm=a50a771a83318093789dc1f4e7487318ab4637164e361ed0e652be2504a1c28d&",
    6: "https://i.imgur.com/s5poU0W.jpg",
    7: "https://media.discordapp.net/attachments/883708922488315924/887796641850089482/fubuki.jpg?ex=685dad0d&is=685c5b8d&hm=cb90c3fbdc4bfe01ceee0b8a8e3416c8728ee2d40da4304fd2e8ac8243635ff7&=&format=webp&width=500&height=500",
    8: "https://cdn.discordapp.com/attachments/883708922488315924/887800318375641129/ayame.jpg?ex=680361ba&is=6802103a&hm=f6e27e2c8297be89786f75085ddb41f9a30b0f422146ff2ec88872be61381c61&",
    9: "https://cdn.discordapp.com/attachments/883708922488315924/887898071671910410/watame.jpg?ex=6803bcc4&is=68026b44&hm=1efef0e20ce7872444cb6f04c9e4b284a81232aa8480a7328332c98b10520097&",
    10: "https://cdn.discordapp.com/attachments/883708922488315924/887798940257378394/kurokami.jpg?ex=68036071&is=68020ef1&hm=1619e4471e95a62a871e1f395a32f19255a5d39bbbf1580bf971e64c9a781867&",
    11: "https://cdn.discordapp.com/attachments/883708922488315924/887909885981896754/risu.jpg?ex=6803c7c5&is=68027645&hm=398cc9f648ee73f5e734f18bd7b9dff15ab4945d11eb17018fd1b66f07fbe77e&",
    12: "https://cdn.discordapp.com/attachments/883708922488315924/887786094844854292/mio.jpg?ex=6803547b&is=680202fb&hm=3c83007b5c8269e53b771076320ce182a98160288d36de7892a3bab00c936a05&",
    13: "https://cdn.discordapp.com/attachments/883708922488315924/942968920846008340/Lui.jpg?ex=6803b17e&is=68025ffe&hm=24607c514bbae1a2af306c7c4daac7427330b43ef75e4ea9b67a41d784c89c5c&",
    14: "https://cdn.discordapp.com/attachments/883708922488315924/887887363148238948/subaru.jpg?ex=6803b2cb&is=6802614b&hm=1bb158a82e9b5fd659393d889a1c6effdf49703720150210c39b9aa7c6f6ce62&",
    15: "https://cdn.discordapp.com/attachments/883708922488315924/887939229164916796/reine.jpg?ex=68033a59&is=6801e8d9&hm=5b9f0d655b0fab951b57f110422d8276037e0755b17d1dc478d353e0f5a26225&",
    16: "https://media.discordapp.net/attachments/883708922488315924/905128178320805918/unknown.png?ex=685d724e&is=685c20ce&hm=ad5fbbac7725c0e50212c4d73de32005598de547911e2b34d49e49966539dd4c&=&format=webp&quality=lossless&width=663&height=660",
    17: "https://cdn.discordapp.com/attachments/883708922488315924/887940296833388554/kiara.jpg?ex=68033b57&is=6801e9d7&hm=708637708484a1fbe58228501abc2297abe9089137d807cb61f62f92d99cc6df&",
    18: "https://cdn.discordapp.com/attachments/883708922488315924/887893489394810890/pekora.jpg?ex=6803b880&is=68026700&hm=8290ccca0ac3831d30a21085b99e557a1a04c2df3c4847d3654fd2200e20dff4&",
    19: "https://cdn.discordapp.com/attachments/883708922488315924/887786079405625414/miko.jpg?ex=68035477&is=680202f7&hm=e90292ea4f0e512739f74a0a7368d8d8358266dac66efa0194c192835b9cd645&",
    20: "https://cdn.discordapp.com/attachments/883708922488315924/887902384603422720/botan.jpg?ex=6803c0c8&is=68026f48&hm=bf1b216db8c9b6bdd970e79a0cbbf21d9a28b6b8f48bad40376bbb605629db1d&",
    21: "https://media.discordapp.net/attachments/883708922488315924/905147166367051886/unknown.png?ex=685d83fd&is=685c327d&hm=1a574053636de813a1fcbe5014bc5e63c58c4a1bc52500bd9057cbdded07ff95&=&format=webp&quality=lossless&width=674&height=670",
    22: "https://cdn.discordapp.com/attachments/883708922488315924/887895706755538944/coco.jpg?ex=6803ba90&is=68026910&hm=c356a2f50d0e31d885d6dfd6bdf75c95a88dd4469632742cacdfd412defa9690&",
    23: "https://cdn.discordapp.com/attachments/883708922488315924/942965733204328458/koyori.png?ex=6803ae86&is=68025d06&hm=8ce1a297c30580c4d32083685020944a7741a00ce5aff85e2f8b67a966a6bea9&",
    24: "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS8fT-qWKGEZpwYy4cGWb3dceRqxV6F82dvTQ&s"
    }

    image_url = image_map.get(result)
    if  image_url:
        embed.set_image(url = image_url)

    embed.set_footer(text = f"{ctx.author.display_name} 的狩獵結果", icon_url = get_user_avatar(ctx.author))
    response_message = await ctx.send(embed = embed)

@hunt.error
async def hunt_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        minutes = int(error.retry_after // 60)
        seconds = int(error.retry_after % 60)
        await ctx.send(f"要愛惜大自然!<:0_ThisIsFine:897482889061621760>，等 {minutes} 分 {seconds} 秒再回來吧。")

@pray.error
async def pray_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        minutes = int(error.retry_after // 60)
        seconds = int(error.retry_after % 60)
        await ctx.send(f"籤紙不夠用啦!<:0_Rainbow:897482889082593300>，等 {minutes} 分 {seconds} 秒再回來吧。")


@bot.command(name="trade", help="交易, 用法: trade @username 數量")
async def trade(ctx, member: discord.Member, amount: int):
    sender_id = str(ctx.author.id)
    receiver_id = str(member.id)

    user_data[sender_id] = user_data.get(sender_id, {"coins": 0})
    user_data[receiver_id] = user_data.get(receiver_id, {"coins": 0})
    
    if sender_id == receiver_id:
        await ctx.send("你不能跟自己交易！")
        return

    if amount <= 0:
        await ctx.send("請輸入正確的羽毛數量。")
        return
    
    if user_data[sender_id]["coins"] < amount:
        await ctx.send("你沒有足夠的羽毛進行交易。")
        return

    user_data[sender_id]["coins"] -= amount
    user_data[receiver_id]["coins"] += amount
    
    update_user_data_file()

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

guess_cooldowns = {}
participants = set()
answer = random.randint(1, 774)
game_active = True
reset_channel_id = 1368275795348295872
last_reset_day = date.today()

async def reset_game():
    global answer, game_active, guess_cooldowns, participants, last_reset_day
    answer = random.randint(1, 774)
    game_active = True
    guess_cooldowns = {}
    participants.clear()
    last_reset_day = date.today()

    channel = bot.get_channel(reset_channel_id)
    if channel:
        embed = discord.Embed(
            title="🔢 猜數字遊戲",
            description=("🎯 數字猜謎遊戲已重置！快來猜 1～774 的神秘數字吧！"),
            color=discord.Color.gold()
        )
        await channel.send(embed=embed)

@tasks.loop(minutes=1)
async def daily_reset_task():#wait for mo
    now = datetime.now()
    today = date.today()
    global last_reset_day
    if now.hour == 0 and last_reset_day != today:
        await reset_game()
        print(f"[{now}] Daily reset completed.")

@bot.command(name="guess", help="1 至 774, 猜一個數字")
async def guess(ctx, number: int):
    global game_active, answer

    if ctx.channel.id != config["guess_channel_id"]:
        return

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
    user_data[user_id] = user_data.get(user_id, {"coins": 0})

    if correct:
        total_reward = 774
        num_players = len(participants)
        if num_players == 0:
            num_players = 1
        share = total_reward // num_players

        for uid in participants:
            user_data[uid] = user_data.get(uid, {"coins": 0})
            user_data[uid]["coins"] += share

        update_user_data_file()
        game_active = False
        message = (
            f"🎯 {ctx.author.display_name} 猜中了！答案是 {answer}！\n"
            f"💰 {num_players} 名Hooman 平分了 {total_reward} 根羽毛，每人獲得 {share} 根 🪶！"
        )
        participants.clear()

    else:
        diff = abs(number - answer) #use abs for difference
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
    embed.set_footer(text=ctx.author.display_name, icon_url=getattr(ctx.author.avatar, "url", None))
    await ctx.send(embed=embed)

@guess.error
async def guess_error(ctx, error):
    if isinstance(error, MissingRequiredArgument):
        await ctx.send("❗ 你忘了輸入數字！請輸入一個 1 到 774 的整數")

def update_user_data_file():
    with open("userdata.json", "w") as user_data_file:
        json.dump(user_data, user_data_file, indent=4)


AUTHORIZED_USER_ID = hidden
@bot.command(name="take", help="讓管理員從某位使用者身上扣除羽毛")
async def take(ctx, member: discord.Member, amount: int):
    if ctx.author.id != AUTHORIZED_USER_ID:
        await ctx.send("你沒有權限使用此指令")
        return

    if amount <= 0:
        await ctx.send("請輸入有效的金額。")
        return

    user_id = str(member.id)
    user_data[user_id] = user_data.get(user_id, {"coins": 0})

    if user_data[user_id]["coins"] < amount:
        await ctx.send(f"{member.display_name} 沒有足夠的羽毛可供扣除。")
        return

    user_data[user_id]["coins"] -= amount
    update_user_data_file()

    await ctx.send(f" {amount} 根羽毛已從 {member.display_name} 身上扣除。")


@bot.command(name="give", help="讓管理員給予某位使用者羽毛")
async def give(ctx, member: discord.Member, amount: int):
    if ctx.author.id != AUTHORIZED_USER_ID:
        await ctx.send("你沒有權限使用此指令")
        return

    if amount <= 0:
        await ctx.send("請輸入有效的金額。")
        return

    user_id = str(member.id)
    user_data[user_id] = user_data.get(user_id, {"coins": 0})

    user_data[user_id]["coins"] += amount
    update_user_data_file()

    await ctx.send(f"管理員給予了 {member.display_name} {amount} 根羽毛。")


@bot.command(name="guess_reset", help="對大部分人而言沒用")
async def guess_reset(ctx: commands.Context) -> None:
    if ctx.author.id != AUTHORIZED_USER_ID:
        await ctx.send("你沒有權限使用此指令")
        return

    await reset_game()

win_streaks = {}

@bot.command(name="<", help="賭小, 30 一局, 輸的時候結算")
async def guess_zero(ctx):
    await play_bet(ctx, 0)

@bot.command(name=">", help="賭大, 30 一局, 輸的時候結算")
async def guess_one(ctx):
    await play_bet(ctx, 1)

async def play_bet(ctx, guess: int):
    user_id = str(ctx.author.id)
    user_data[user_id] = user_data.get(user_id, {"coins": 0})
    streak = win_streaks.get(user_id, 0)

    guess_text = "小" if guess == 0 else "大"
    
    embed = discord.Embed(title="🎲 買大小結果", color=discord.Color.green())
    embed.set_author(name=ctx.author.display_name, icon_url=getattr(ctx.author.avatar, "url", None))

    if streak == 0:
        if user_data[user_id]["coins"] < 30:
            embed.description = "❗你都Mei 錢了還賭哦<:0_AOA:897482887341965343> (需要 30 根羽毛)"
            await ctx.send(embed=embed)
            return
        user_data[user_id]["coins"] -= 30
        update_user_data_file()

    result = random.randint(0, 1)
    result_text = "小" if result == 0 else "大"

    if result == guess:
        win_streaks[user_id] = streak + 10
        embed.add_field(name="✅ 結果", value=f"你猜的是 {guess_text}，抽出的結果是 {result_text}，你猜對了！", inline=False)
        embed.add_field(name="🔥 連勝獲得", value=f"{win_streaks[user_id]} 根羽毛", inline=False)
    else:
        reward = streak
        win_streaks[user_id] = 0
        user_data[user_id]["coins"] += reward
        update_user_data_file()
        embed.color = discord.Color.red()
        embed.add_field(name="❌ 結果", value=f"你猜的是 {guess_text}，抽出的結果是 {result_text}，你猜錯了！", inline=False)
        embed.add_field(name="🎁 獎勵", value=f"你獲得了 {reward} 根羽毛 🪶，遊戲結束。", inline=False)

    await ctx.send(embed=embed)



emotes = {
    "<:0_Friend:985377444741664789>": 90.0,
    "<:0_Happy:891962347374133269>": 8.9,
    "<:Hootsie_dondon:1094150618807009350>": 1.0,
    "<:0_Nightmare:902486571918430258>": 0.1
}
@bot.command(name="draw", help="從四個emote 裏面抽出十個結果")
async def draw(ctx):
    draws = []
    choices = list(emotes.keys())
    weights = list(emotes.values())

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

@bot.command(name="shop", help="貓頭鷹寵物店：寵物列表")
async def shop(ctx):
    embed = discord.Embed(
    title="──貓頭鷹寵物店──",
    description=(
        "**編號1**\n"
        "`@🦉貓頭鷹`\n"
        "25000根羽毛 🪶\n"
        "一隻超級可愛的貓頭鷹。\n\n"

        "**編號2**\n"
        "`@🐰兔子`\n"
        "15000根羽毛 🪶\n"
        "一隻很囂張的兔子ぺこ。\n\n"

        "**編號3**\n"
        "`@🐶狗狗`\n"
        "15000根羽毛 🪶\n"
        "一隻很快樂的狗狗。\n\n"

        "**編號4**\n"
        "`@🦁獅子`\n"
        "15000根羽毛 🪶\n"
        "一隻笑聲很屑的獅子。\n\n"

        "**編號5**\n"
        "`@🦈鯊魚`\n"
        "15000根羽毛 🪶\n"
        "一條很小隻的鯊魚。\n\n"

        "**編號6**\n"
        "`@🦃火雞`\n"
        "10000根羽毛 🪶\n"
        "一隻會德語的火雞。\n\n"

        "**編號7**\n"
        "`@🐭老鼠`\n"
        "10000根羽毛 🪶\n"
        "一隻很渾沌的老鼠。\n\n"

        "**編號8**\n"
        "`@🐑羊羊`\n"
        "5000根羽毛 🪶\n"
        "一隻愛玩猜拳的羊。\n\n"

        "**編號9**\n"
        "`@🐙章魚`\n"
        "10000根羽毛 🪶\n"
        "一隻喜歡雙關語的章魚。"
    ),
    color=discord.Color.from_str("#A0522D")
)
    await ctx.send(embed=embed)

bot.run(config["token"])
