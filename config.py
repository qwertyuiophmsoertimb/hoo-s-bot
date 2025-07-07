import discord
import random
from datetime import datetime

# --- Bot Configuration ---
# You need to create a config.json file in the same directory as main.py
# with content like:
# {
#   "pray_channel_id": 123456789012345678,
#   "slots_channel_id": 123456789012345678,
#   "hunt_channel_id": 123456789012345678,
#   "bot_token": "YOUR_BOT_TOKEN_HERE"
# }
# Replace the placeholder IDs and token with your actual values.
CONFIG = {}
try:
    with open("config.json", "r") as config_file:
        CONFIG = json.load(config_file)
except FileNotFoundError:
    print("Error: config.json not found. Please create one with necessary channel IDs and bot token.")
    # Provide dummy config to allow bot to start, but functionality will be limited
    CONFIG = {
        "pray_channel_id": 0,
        "slots_channel_id": 0,
        "hunt_channel_id": 0,
        "bot_token": "YOUR_BOT_TOKEN_HERE"
    }
except json.JSONDecodeError:
    print("Error: config.json is malformed. Please check its syntax.")
    CONFIG = {
        "pray_channel_id": 0,
        "slots_channel_id": 0,
        "hunt_channel_id": 0,
        "bot_token": "YOUR_BOT_TOKEN_HERE"
    }

AUTHORIZED_USER_ID = 123456789 # Replace with the actual Discord User ID for your authorized user

# --- RPG Game Constants ---
PRIVATE_CHANNEL_EMOJI = '👍'
REQUIRED_REACTIONS_FOR_PRIVATE_CHANNEL = 1
RUN_EVENT_LIMIT = 20 # User requested 20 events before boss
SHOP_CHANCE = 0.1
ITEM_DROP_CHANCE = 0.2

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
for i in range(11, 21):
    XP_TO_NEXT_LEVEL[i] = 50 * i + 100
for i in range(21, 31):
    XP_TO_NEXT_LEVEL[i] = 50 * i + 150
for i in range(31, 101):
    XP_TO_NEXT_LEVEL[i] = 50 * i + 20000

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
                "strength_multiplier": 0.5,
                "intelligence_multiplier": 0.5
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
        "random_action_chance": {"physical_damage": 0.8, "magical_damage": 0.2, "healing": 0.2}
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
    },
    "voidwalkers_edge": {
        "name": "Voidwalker's Edge ",
        "type": "weapon",
        "base_effect": {"strength": 10, "intelligence": 10},
        "upgrade_cost_multiplier": 1.6,
        "max_level": 7,
        "special_attack": {"type": "hp_scaling_damage", "damage_multiplier_per_hp_lost_percent": 0.01}
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
    "auto_healing_amulet": {
        "name": "自療護符 💚✨",
        "type": "accessory",
        "special_skill": {
            "name": "Regeneration",
            "description": "Automatically restores a small amount of HP each combat round.",
            "effect": {"hp_restore": 10}
        }
    }
}

ALL_ITEM_TEMPLATES = {**WEAPON_TEMPLATES, **ARMOR_TEMPLATES, **ACCESSORY_TEMPLATES}

SHOP_ITEMS = {
    "item_healing_potion": {
        "name": "治療藥水 (20 HP)",
        "description": "Restores 20 HP. A trusty companion in dire times.",
        "cost": 150,
        "effect": {'hp': 20}
    },
    "item_strength_amulet": {
        "name": "力量護符 💪(10 strength)",
        "description": "Increases your Strength by 10. Feel the power!",
        "cost": 60,
        "effect": {'strength': 10}
    },
    "item_defense_gloves": {
        "name": "守護手套 🧤(3 defense)",
        "description": "Boosts your Defense by 3. For the resilient adventurer.",
        "cost": 20,
        "effect": {'defense': 3}
    },
    "item_wisdom_scroll": {
        "name": "遠古捲軸 📜(3 intelligence)",
        "description": "Enhances your Intelligence by 3. Unlocks new insights.",
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
        "description": "Restores a substantial 50 HP. For when things get really tough.",
        "cost": 200,
        "effect": {'hp': 50}
    },
    "item_tome_of_insight": {
        "name": "洞察之書 🧠(5 intelligence)",
        "description": "A forbidden tome that increases your Intelligence by 5.",
        "cost": 80,
        "effect": {'intelligence': 5}
    },
    "item_iron_ore_chunk": {
        "name": "鐵礦石塊 🪨(5 defense)",
        "description": "A solid chunk of iron ore that increases your Defense by 5.",
        "cost": 40,
        "effect": {'defense': 5}
    }
}

# Constants for Boss Fight
BOSS_PHYSICAL_PHASE_ID = "abyssal_shadow_lord_p1"
BOSS_MAGICAL_PHASE_ID = "abyssal_shadow_lord_p2"
CRIMSON_BEHEMOTH_ENEMY_ID = "crimson_behemoth_physical"

GAME_EVENTS = {
    "start_adventure": {
        "text": "一團神秘的迷霧籠罩而來 你們發現自己身處遺址入口 你們要怎麼做?",
        "image_url": "https://placehold.co/600x300/4B0082/FFFFFF?text=Dungeon+Entrance",
        "options": {
            "1": {"text": "直接衝進去阿拉花瓜", "next_id": "random_event", "effect": {'strength': 10}},
            "2": {"text": "先探查敵人位置 再衝進去當核平使者", "next_id": "random_event", "effect": {'intelligence': 5}}
        }
    },
    "forest_path": {
        "text": "你們在草叢中撿到一瓶奇怪的藥水 要喝嗎?",
        "image_url": "https://placehold.co/600x300/228B22/FFFFFF?text=Shimmering+Potion",
        "options": {
            "1": {"text": "一口氣喝光", "next_id": "random_event", "effect": {'strength': 20}},
            "2": {"text": "灌隊友嘴裡", "next_id": "random_event", "effect": {'intelligence': 6}}
        }
    },
    "sunny_forest_path": {
        "text": "你們遇到了一位獨自販賣稀有商品的商人。你們要與他互動嗎?",
        "image_url": "https://placehold.co/600x300/DAA520/000000?text=Forest+Merchant",
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
    "puzzling_riddle2": {
        "text": "你們遇到了一座古老的雕像，上面刻著一個謎題：\n「f(x) = 3x^2 +5x -4」\n 「f'(x)是什麼？」\n你們會嘗試回答嗎？",
        "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQJAKPL8ZzgSfPdvI5SfIcbaSICEuIq7ezsn3NBNcKrMx36lA&s",
        "options": {
            "1": {"text": "回答：「0」", "next_id": "puzzling_riddle3", "effect": {'hp': -1}},
            "2": {"text": "回答：「6x + 5」", "next_id": "puzzling_riddle3", "effect": {'xp': 30}},
            "3": {"text": "回答：「4x」", "next_id": "puzzling_riddle3", "effect": {'hp': -1}},
            "4": {"text": "回答：「是能吃的」", "next_id": "puzzling_riddle3", "effect": {'hp': -10}},
        }
    },
    "puzzling_riddle3": {
        "text": "你們遇到了一座古老的雕像，上面刻著一個謎題：\n「根據宇宙大爆炸理論，宇宙中含量最多的元素是什麼？」\n你們會嘗試回答嗎？",
        "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQJAKPL8ZzgSfPdvI5SfIcbaSICEuIq7ezsn3NBNcKrMx36lA&s",
        "options": {
            "1": {"text": "回答：「氫H」", "next_id": "puzzling_riddle4", "effect": {'xp': 30}},
            "2": {"text": "回答：「氦He」", "next_id": "puzzling_riddle4", "effect": {'hp': -1}},
            "3": {"text": "回答：「碳C」", "next_id": "puzzling_riddle4", "effect": {'hp': -1}},
            "4": {"text": "回答：「氧O」", "next_id": "puzzling_riddle4", "effect": {'hp': -1}},
            "5": {"text": "回答：「不會」", "next_id": "puzzling_riddle4", "effect": {'hp': -10}}
        }
    },
    "puzzling_riddle4": {
        "text": "你們遇到了一座古老的雕像，上面刻著一個謎題：\n「系列中的下一個數字是：2、5、10、17、26...？」\n你們會嘗試回答嗎？",
        "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQJAKPL8ZzgSfPdvI5SfIcbaSICEuIq7ezsn3NBNcKrMx36lA&s",
        "options": {
            "1": {"text": "回答：「32」", "next_id": "ruins_explore", "effect": {'hp': -1}},
            "2": {"text": "回答：「774」", "next_id": "ruins_explore", "effect": {'xp': 7}},
            "3": {"text": "回答：「37」", "next_id": "ruins_explore", "effect": {'xp': 30}},
            "4": {"text": "回答：「29」", "next_id": "ruins_explore", "effect": {'hp': -1}},
            "5": {"text": "回答：「不會」", "next_id": "ruins_explore", "effect": {'hp': -10}}
        }
    },
    "puzzling_riddle5": {
        "text": "你們遇到了一座古老的雕像，上面刻著一個謎題：\n「以下何者為真實的文明記錄？」？",
        "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQJAKPL8ZzgSfPdvI5SfIcbaSICEuIq7ezsn3NBNcKrMx36lA&s",
        "options": {
            "1": {"text": "回答：「一名假警察在I-4高速公路上截停真警察被捕」", "next_id": "random_event", "effect": {'xp': 10}},
            "2": {"text": "回答：「一名老人因為擔心冰毒對自己健康有影響而把冰毒帶去請教醫生」", "next_id": "random_event", "effect": {'xp': 10}},
            "3": {"text": "回答：「男子因駕駛割草機撞上一輛警車而被逮捕 並被指控酒後駕駛」", "next_id": "random_event", "effect": {'xp': 10}},
            "4": {"text": "回答：「男子在入室搶劫期間睡著被捕」", "next_id": "random_event", "effect": {'xp': 10}},
            "5": {"text": "回答：「以上皆是」", "next_id": "random_event", "effect": {'xp': 30}}
        }
    },
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
        "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTckRaYop6JC-_yPEySFaC93CTo4DNtRCQl9nDVtdE7edGMyO4ViBHYgsyC_0A6o88SAm8ss5visUP3cd-2_XeqSiSu8odiTCMb8_CH2EloN&s",
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
        "enemy_hp": 600,
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
        "enemy_hp": 500,
        "enemy_defense": 15,
        "enemy_intelligence_attack": 0,
        "options": {
            "1": {"text": "石頭 🪨", "next_id": "outcome_combat_result", "effect": {}},
            "2": {"text": "布 📄", "next_id": "outcome_combat_result", "effect": {}},
            "3": {"text": "剪刀 ✂️", "next_id": "outcome_combat_result", "effect": {}}
        },
        "boss_phase_name": "physical" 
    },
    BOSS_MAGICAL_PHASE_ID: {
        "text": "深淵暗影領主的裝甲剝落，內部的黑魔法被完全解放!",
        "image_url": "https://placehold.co/600x300/330066/FFFFFF?text=Shadow+Lord+Magic",
        "combat_type": "magical",
        "enemy_attack_value": 35,
        "enemy_hp": 500,
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
    "outcome_flee_success": "你巧妙地逃脫了遭遇！沒有受到傷害，但你感到潛在經驗值略有損失",
    "outcome_flee_fail": "你的逃跑嘗試失敗了！你被抓住了並受到了傷害",
    "outcome_lucky_trade": "The lucky charm shines brightly. You feel a bit more resilient now. Your coins are now adjusted.",
    "outcome_no_trade": "You decided not to trade. The merchant shrugs and disappears into the forest.",
    "outcome_successful_stealth": "You moved like shadows, completely avoiding detection. Well done!",
    "outcome_failed_stealth": "You tripped on a root! The merchant noticed you, but seemed to just stare. You feel a bit silly.",
    "outcome_run_completed": "經歷了無數的考驗，你的隊伍決定從這次探險中返回!"
}

ALL_PLAYABLE_EVENT_IDS = [
    eid for eid in GAME_EVENTS if eid not in [
        "start_adventure", "shop_encounter", BOSS_PHYSICAL_PHASE_ID, BOSS_MAGICAL_PHASE_ID, "CRIMSON_BEHEMOTH_ENEMY_ID", "puzzling_riddle2", "puzzling_riddle3", "puzzling_riddle4"
    ] and not eid.startswith("outcome_")
]

GLOBAL_ITEM_POOL = list(WEAPON_TEMPLATES.keys()) + [
    armor_id for armor_id, data in ARMOR_TEMPLATES.items()
    if 'evolves_to' not in data and armor_id not in INITIAL_PLAYER_PROFILE['inventory'] and armor_id != "voidwalkers_edge" and armor_id != "netherite_armor" and armor_id != "diamond_armor"
]

GAME_EMOJIS = {
    "1": "1️⃣",
    "2": "2️⃣",
    "3": "3️⃣",
    "4": "4️⃣",
    "5": "5️⃣",
    "X": "❌"
}

# --- Minigame Specifics ---
MINIGAME_RESET_CHANNEL_ID = 1368275795348295872 # Replace with your actual channel ID for guess game resets

FORTUNES = {
    1: ("大凶", 10, "大凶？！勸你還是乖乖在家不要出門吧！", 10),
    2: ("凶", 20, "啊！凶嗎...不是有句話是：「人有旦夕禍...」後面我忘了...", 20),
    3: ("末吉", 30, "末吉？或許可以多做做善事累積點陰德與福氣呢！", 30),
    4: ("吉", 40, "介於中間的吉嗎？平平安安結束一天也是種福氣呢！", 40),
    5: ("小吉", 50, "穩定的小吉呢！今天應該會是個簡單平順的一天吧！", 50),
    6: ("中吉", 60, "中吉耶！今天的你說不定會有什麼小確幸哦！", 60),
    7: ("大吉", 70, "竟然是大吉嗎?!你或許是綜觀全人類中數一數二幸運的人呢！", 70)
}

COLOR_MAP = {
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

PRAY_IMAGE_MAP = {
    "大吉": "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEimpKtspceL47HWV8CIcCG83OLzaXss2VrjPQt65pfItad0LzQVB13lABAZ8zvViixYeemTkX9O3F2W9vfmDrv2u00nRzGmVD4OIj81oM6zOk84edl8Loj2BvpLIkT4TgWCiPJr4YMSzQZE/s1600/omikuji_daikichi.png",
    "中吉": "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEjDPy0X_GAJUV8pauG2Pwpn1dC5O7FfDAJdfDQNxcDB2JpPK85arrtw_qaLKdlvD1YQ9KqkHVrWe_Yfo1hJbYOQNwp8Zb-IZmaISp7_jFDX9pwXINlc7aJtIrlwEAMk6lCkQbweriNT9Lvx/s1600/omikuji_chuukichi.png",
    "小吉": "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEhhjqxIjcS2_4hGG8FLlhHSDe1pnMU-XeAXEGWUy10y8Nj-Ohhuchx2ZqxYmPcW2FexxQAdbPyVbJvyCqnAbJ9_DGY7nN3WK0-P0Rz8UlfeouDwdfqgjlx0cBtwXWrTLe7zY8JUGciZcia8/s1600/omikuji_syoukichi.png",
    "吉": "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEgablBON0p3T-N_SO2UoPe8MSmCLzGEUlntQIbe1CNzzzapUDo8bky9O4MQqvj_B0wygWh0mgFVlH6WTM-ovapykZUPabAHWT73KfAnViUAaUSBMdEveRAjJRVaAiMbA8ZxyoKCujlj9iqx/s800/omikuji_kichi.png",
    "末吉": "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEglx-IJtiH6CUGvdXF6GAfm_Sh8mbWExuxTjGKhWZbbVk8oiJNWfkXNqSg8v8RyMpVPPl_y4GAlCDx0YHia7rtMs5QfOE7qiX8_pdi3xv-9mYanwTjNBOg2WFrEgiIo7RcI/s1600/omikuji_suekichi.png",
    "凶": "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEjYwJAbs5msucqL3TQJEYwCuR7ehewBO-F9HuYH_ERwC9wgzSCHUG3EEUvwF9A281BjEG02Lp8tDY4bKdoTDvr1j-QA78qQXN-DKolTIfj97z2zvFDWC3gJBOHfrdW3hgrXPsMS5yli-Sqo/s1600/omikuji_kyou.png",
    "大凶": "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEiM7jD5fZAfHSZ6vk0KH99puqk6oQNcwCgmImN28pHYZey7VxVDIlSnF5ZKxrBx0GVVCyIJXlSRR46S3U3_xMex4LIVAHB_kYJHpJ3RVxjEQLZUEUl6R0B3QidHyZazb-rhwzJxRzI_d6xe/s1600/omikuji_daikyou.png"
}

HUNTING_RESULTS = {
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
    15: ("「恩？想要我的羽毛？可以喔～Poi(丟)」\n 她一邊講「Poi」，一邊將手上的手榴彈丟了出去，你覺得此地很危險，拿完羽毛後就離開了", 25, "你蒐集到了乳白色的獅毛！", 25),
    16: (" 你來到了VR Chat的神奇空間，並遇到了穿著南瓜裝的Smol Ame！\n 她看起來很開心，你們伴隨著音樂舞動著身體，像是在開Party一樣。", 30, "過了一段時間，Party結束了，Ame塞了一點糖果給你當作紀念品，就這樣離開了。", 30),
    17: ("「KIKKERIKIIII～想要我不死鳳凰的羽毛？只要你來KFP幫忙的話我可以考慮哦～」\n 於是你去KFP打了一整天的工，工資是Kiara的羽毛。", 30, "你蒐集到了橘紅色的鳳凰毛！", 30),
    18: ("「放開我ぺこ！快點放開我ぺko！ぺkoら可不是什麼糧食啊ぺko！！」\n 跟她解釋沒有要吃掉之後，她發出了「ぺこぺこぺこ」的囂張聲音後給了你一點羽毛。", 35, "你蒐集到了白色的兔子毛！", 35),
    19: ("「不要這樣捏！みこ不是獵物捏！！」\n 伴隨著黑武士的《帝國進行曲》，みこ躲進了她的魔王城中。", 1, "你在地上撿到了...みこ的粉紅呆毛...?", 1),
    20: ("「嗯？想要我的羽毛嗎？可以喔～Poi(丟)」\n 她一邊講「Poi」，一邊將手上的手榴彈丟了出去，你覺得此地很危險，拿完羽毛後就離開了", 25, "你蒐集到了乳白色的獅毛！", 25),
    21: (" 你來到了一個神祕的實驗室...打開門碰到了身穿實驗袍的Ina！\n她手上拿著神祕的藥水，希望你幫她做個小實驗，於是她將藥水滴到你頭上。", 40, "沒想到你變成了Takodachi！她馬上把你變回原狀，並塞了一些羽毛給你當作補償。", 40),
    22: (" 在你飛在空中尋找目標的時候，你發現有一隻橘色的龍在你不遠處翱翔。\n 雖然體型、種族與你差異巨大，但你卻不會害怕，因為你知道那條龍是不會傷害你的。", 50, "你見到了傳說中的龍，心中充滿了尊敬。你也在不遠處的地面上找到了橘色龍鱗。", 50),
    23: ("「こんこよ～ 這麼晚了還在森林裡是迷路了嗎？ 嘿？羽毛嗎~可以哦，如果你願意當我的助手君的話(ㆆ▿ㆆ)」\n 雖然こより一臉在謀劃什麼的表情，你還是尾隨她進入了她的秘密實驗室。在經歷了一連串的藥物試驗與身體檢測後，你拖著疲憊不堪的身軀到早上才回家。", 54, "你蒐集到了粉紅色的郊狼毛！", 54),
    24: ("偷取中...", 74, "偷取中...", 74) # Special case for theft
}

HUNT_IMAGE_MAP = {
    1: "https://cdn.discordapp.com/attachments/883708922488315924/887948965797048340/mumei.png?ex=6803436a&is=6801f1ea&hm=0b5fdf4fb35b33c0368e043bda2dfa155da09f01f1381077d95231257ba10587&",
    2: "https://cdn.discordapp.com/attachments/883708922488315924/887947855711567872/fukuro.png?ex=68034262&is=6801f0e2&hm=73f4c7b11fa4977dd27a131a14248760d1fb109bcd27fd5b60d79f2cc3f12643&",
    3: "https://cdn.discordapp.com/attachments/883708922488315924/887945499544543242/baelz.jpg?ex=68034030&is=6801eeb0&hm=0d5220f7fd84e3d9ffae5858a0e688117b5b8df7aeb8a098a4178734bb802377&",
    4: "https://cdn.discordapp.com/attachments/883708922488315924/887795059326611466/korone.jpg?ex=68035cd4&is=68020b54&hm=78c710d5a213603f336e50696ca04dbb98732bccc48f794baef52d5fd378a4aa&",
    5: "https://cdn.discordapp.com/attachments/883708922488315924/887905128542240768/polka.png?ex=6803c357&is=680271d7&hm=a50a771a83318093789dc1f4e7487318ab4637164e361ed0e652be2504a1c28d&",
    6: "https://i.imgur.com/s5poU0W.jpg",
    7: "https://media.discordapp.com/attachments/883708922488315924/887796641850089482/fubuki.jpg?ex=680c98cd&is=680b474d&hm=0e963d53a96245bcc12467bcaa6c5a35df740172f5efdd5fd9af302131d11380&=&format=webp&width=500&height=500",
    8: "https://cdn.discordapp.com/attachments/883708922488315924/887800318375641129/ayame.jpg?ex=680361ba&is=6802103a&hm=f6e27e2c8297be89786f75085ddb41f9a30b0f422146ff2ec88872be61381c61&",
    9: "https://cdn.discordapp.com/attachments/883708922488315924/887898071671910410/watame.jpg?ex=6803bcc4&is=68026b44&hm=1efef0e20ce7872444cb6f04c9e4b284a81232aa8480a7328332c98b10520097&",
    10: "https://cdn.discordapp.com/attachments/883708922488315924/887798940257378394/kurokami.jpg?ex=68036071&is=68020ef1&hm=1619e4471e95a62a871e1f395a32f19255a5d39bbbf1580bf971e64c9a781867&",
    11: "https://cdn.discordapp.com/attachments/883708922488315924/887909885981896754/risu.jpg?ex=6803c7c5&is=68027645&hm=398cc9f648ee73f5e734f18bd7b9dff15ab4945d11eb17018fd1b66f07fbe77e&",
    12: "https://cdn.discordapp.com/attachments/883708922488315924/887786094844854292/mio.jpg?ex=6803547b&is=680202fb&hm=3c83007b5c8269e53b771076320ce182a98160288d36de7892a3bab00c936a05&",
    13: "https://cdn.discordapp.com/attachments/883708922488315924/942968920846008340/Lui.jpg?ex=6803b17e&is=68025ffe&hm=24607c514bbae1a2af306c7c4daac7427330b43ef75e4ea9b67a41d784c89c5c&",
    14: "https://cdn.discordapp.com/attachments/883708922488315924/887887363148238948/subaru.jpg?ex=6803b2cb&is=6802614b&hm=1bb158a82e9b5fd659393d889a1c6effdf49703720150210c39b9aa7c6f6ce62&",
    15: "https://cdn.discordapp.com/attachments/883708922488315924/887939229164916796/reine.jpg?ex=68033a59&is=6801e8d9&hm=5b9f0d655b0fab951b57f110422d8276037e0755b17d1dc478d353e0f5a26225&",
    16: "https://media.discordapp.com/attachments/883708922488315924/905128178320805918/unknown.png?ex=6803cc4e&is=68027ace&hm=196406245b3495fcfed75acb7a968089c959a41daa0d8366c9d5f4c0f4b70be7&",
    17: "https://cdn.discordapp.com/attachments/883708922488315924/887940296833388554/kiara.jpg?ex=68033b57&is=6801e9d7&hm=708637708484a1fbe58228501abc2297abe9089137d807cb61f62f92d99cc6df&",
    18: "https://cdn.discordapp.com/attachments/883708922488315924/887893489394810890/pekora.jpg?ex=6803b880&is=68026700&hm=8290ccca0ac3831d30a21085b99e557a1a04c2df3c4847d3654fd2200e20dff4&",
    19: "https://cdn.discordapp.com/attachments/883708922488315924/887786079405625414/miko.jpg?ex=68035477&is=680202f7&hm=e90292ea4f0e512739f74a0a7368d8d8358266dac66efa0194c192835b9cd645&",
    20: "https://cdn.discordapp.com/attachments/883708922488315924/887902384603422720/botan.jpg?ex=6803c0c8&is=68026f48&hm=bf1b216db8c9b6bdd970e79a0cbbf21d9a28b6b8f48bad40376bbb605629db1d&",
    21: "https://media.discordapp.com/attachments/883708922488315924/905147166367051886/unknown.png?ex=6803ddfd&is=68028c7d&hm=c3da733f57d8a66c712b9a70b7030ae4c8ccf05d129d6a3e85c1730303b450c6&",
    22: "https://cdn.discordapp.com/attachments/883708922488315924/887895706755538944/coco.jpg?ex=6803ba90&is=68026910&hm=c356a2f50d0e31d885d6dfd6bdf75c95a88dd4469632742cacdfd412defa9690&",
    23: "https://cdn.discordapp.com/attachments/883708922488315924/942965733204328458/koyori.png?ex=6803ae86&is=68025d06&hm=8ce1a297c30580c4d32083685020944a7741a00ce5aff85e2f8b67a966a6bea9&",
    24: "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS8fT-qWKGEZpwYy4cGWb3dceRqxV6F82dvTQ&s"
}

SLOTS_SYMBOLS = ["🪐", "🪶", "🌿", "⌛", "<:0_Berries:893198899995607110>", "🎲"]
SLOTS_WINNINGS = {
    5: (5050, "🌟 哇靠! 歐皇! {display_name} 贏了5000根羽毛!"),
    4: (550, "🔥哇! 四個 {best_symbol}! {display_name} 贏了500根羽毛!"),
    3: (100, "✨三個 {best_symbol}! {display_name} 贏了50根羽毛!"),
    2: (25, "一對 {best_symbol}, 不過還是輸了25根羽毛"),
}

DRAW_EMOTES = {
    "<:0_Friend:985377444741664789>": 90.0,
    "<:0_Happy:891962347374133269>": 8.9,
    "<:Hootsie_dondon:1094150618807009350>": 1.0,
    "<:0_Nightmare:902486571918430258>": 0.1
}

SHOP_PET_LIST = (
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
)
