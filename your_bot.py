import telebot
from telebot import types
import requests
import math
import random
import time
from datetime import datetime
from collections import Counter

# ==================== 核心配置 ====================
BOT_TOKEN = "8789627493:AAExE8z-tRhrbGvENYVt4dxqWUFf56rrZJQ"
API_KJ = "https://pc28.help/api/kj.json?nbr=100"
API_KENO = "https://pc28.help/api/keno.json?nbr=100"
API_YL = "https://pc28.help/api/yl.json"

bot = telebot.TeleBot(BOT_TOKEN)

# 5y 完整静态映射表
five_y_table = {
    "5y0": [20, 15, 25, 5, 10],
    "5y1": [1, 11, 21, 6, 16, 26],
    "5y2": [2, 12, 22, 7, 17, 27],
    "5y3": [13, 23, 3, 8, 18],
    "5y4": [14, 24, 4, 19, 9]
}

def get_comb_attr(n):
    return ("大" if n >= 14 else "小") + ("单" if n % 2 != 0 else "双")

FIVE_Y_PROPERTIES = {k: Counter([get_comb_attr(n) for n in nums]) for k, nums in five_y_table.items()}

# 全局状态存储
state = {
    "current_model": "V8-Hybrid",
    "broadcast_on": False,
    "last_issue": None
}

# ==================== 核心引擎 1: V8-Hybrid ====================
def engine_v8_hybrid(data):
    try:
        yl_data = requests.get(API_YL, timeout=5).json().get("data", {})
        keno_data = requests.get(API_KENO, timeout=5).json().get("data", [])
        scores = {"大单": 100.0, "小单": 100.0, "大双": 100.0, "小双": 100.0}
        # 物理加权
        nbrs = [int(n) for n in keno_data[0]["nbrs"].split(",")]
        p_val = sum([nbrs[i] for i in [1, 4, 7, 10, 13, 16]]) % 10
        raw_map = ["小双", "小单", "小双", "小单", "小双", "大单", "大双", "大单", "大双", "大单"]
        scores[raw_map[p_val]] += 55.0
        # 遗漏加权
        for cat in scores: scores[cat] += float(yl_data.get(cat, 0)) * 3.5
        sorted_res = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return f"{sorted_res[0][0]} + {sorted_res[1][0]}"
    except: return "计算失败"

# ==================== 核心引擎 2: 4D PI+PHI ====================
def engine_4d_pi(history):
    if len(history) < 10: return "数据不足"
    phi = (1 + 5**0.5) / 2
    fixed_sum = sum([13, 12, 14, 15]) # 模拟最优参数
    raw = (fixed_sum * phi) / (history[0]["total"] * math.pi if history[0]["total"] > 0 else 1.5)
    s = "{:.10f}".format(abs(raw - int(raw))).split('.')[1]
    cat_map = {0:"小双", 1:"小单", 2:"小双", 3:"小单", 4:"小双", 5:"大单", 6:"大双", 7:"大单", 8:"大双", 9:"大单"}
    c1 = cat_map[int(s[0])]
    c2 = cat_map[int(s[1])]
    return f"{c1} + {c2}" if c1 != c2 else f"{c1} + 对冲"

# ==================== 核心引擎 3: V23-Armor 杀手 ====================
def engine_v23_armor(history):
    recent = [i["combination"] for i in history[:10]]
    if recent[0] == recent[1]:
        opposites = {"大单":"小双", "小双":"大单", "大双":"小单", "小单":"大双"}
        return f"杀【{opposites[recent[0]]}】"
    return f"杀【{sorted(Counter([i['combination'] for i in history[:40]]).items(), key=lambda x: x[1])[0][0]}】"

# ==================== 核心引擎 4: V18.1-5y共振 ====================
def engine_5y_resonance(history):
    y_list = [int(sum(int(x) for x in i["number"].split("+")) % 5) for i in history[:15]]
    diffs = [y_list[i] - y_list[i+1] for i in range(len(y_list)-1)]
    pred_y_idx = int(round(y_list[0] + (sum(diffs[:3])/3))) % 5
    pred_y_key = f"5y{pred_y_idx}"
    recent_global = Counter([i["combination"] for i in history[:20]])
    group_combs = FIVE_Y_PROPERTIES[pred_y_key]
    scores = {c: group_combs[c] * (recent_global[c] + 2) for c in ["大单", "小单", "大双", "小双"]}
    top = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return f"坐标{pred_y_key}: {top[0][0]} + {top[1][0]}"

# ==================== 机器人交互逻辑 ====================
def get_data_all():
    try:
        res = requests.get(API_KJ, timeout=10).json().get("data", [])
        for item in res:
            item["total"] = sum([int(n) for n in item["number"].split("+")])
        return res
    except: return []

@bot.message_handler(commands=['start'])
def start(m):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🔮 获取预测", "⚙️ 模型切换", "📢 频道播报开关")
    bot.send_message(m.chat.id, "⚡ **全量算法矩阵 V8.0 已就绪**\n包含：V8混合、4D-PI、V23杀手、V18-5y。", parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda m: True)
def handle_msg(m):
    data = get_data_all()
    if not data: return

    if m.text == "🔮 获取预测":
        if state["current_model"] == "V8-Hybrid": res = engine_v8_hybrid(data)
        elif state["current_model"] == "4D-PI": res = engine_4d_pi(data)
        elif state["current_model"] == "V23-Armor": res = engine_v23_armor(data)
        else: res = engine_5y_resonance(data)
        
        msg = (f"🧬 **模型: {state['current_model']}**\n"
               f"━━━━━━━━━━━━━━\n"
               f"📡 最新: `{data[0]['nbr']}` → **{data[0]['combination']}**\n"
               f"🎯 预测: `{int(data[0]['nbr'])+1}` 期\n"
               f"🔥 推荐: **{res}**\n"
               f"━━━━━━━━━━━━━━")
        bot.send_message(m.chat.id, msg, parse_mode="Markdown")

    elif m.text == "⚙️ 模型切换":
        mk = types.InlineKeyboardMarkup()
        mk.add(types.InlineKeyboardButton("V8-Hybrid", callback_data="m_v8"),
               types.InlineKeyboardButton("4D-PI+PHI", callback_data="m_4d"))
        mk.add(types.InlineKeyboardButton("V23-Armor杀手", callback_data="m_v23"),
               types.InlineKeyboardButton("V18.1-5y共振", callback_data="m_5y"))
        bot.send_message(m.chat.id, "请选择需要激活的核心引擎:", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("m_"))
def set_model(c):
    map_m = {"m_v8": "V8-Hybrid", "m_4d": "4D-PI", "m_v23": "V23-Armor", "m_5y": "5y-Resonance"}
    state["current_model"] = map_m[c.data]
    bot.answer_callback_query(c.id, f"已切换至 {state['current_model']}")
    bot.edit_message_text(f"✅ **引擎切换成功**: `{state['current_model']}`", c.message.chat.id, c.message.message_id, parse_mode="Markdown")

if __name__ == "__main__":
    print("🚀 完整矩阵引擎启动...")
    bot.infinity_polling()
