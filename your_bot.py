import telebot
from telebot import types
import requests
import math
import os

# ==================== 配置区 ====================
BOT_TOKEN = "8789627493:AAExE8z-tRhrbGvENYVt4dxqWUFf56rrZJQ"
API_URL = "https://pc28.help/api/kj.json?nbr=100"
bot = telebot.TeleBot(BOT_TOKEN)

# 内存变量
CURRENT_MODEL = "1" 

# ==================== 核心算法矩阵 (全注入) ====================

def get_latest_data():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(API_URL, headers=headers, timeout=15).json()
        return resp.get("data", [])
    except: return []

# 1. 4D双组权重 (PI+PHI)
def algo_1(data):
    # 利用圆周率与黄金分割率进行非线性偏移推演
    totals = [sum(int(x) for x in i["number"].split("+")) for i in data[:5]]
    phi = 1.61803398
    seed = (totals[0] * math.pi) / (totals[1] * phi if totals[1] > 0 else 1)
    offset = float("0." + str(seed).split(".")[1][:6])
    res_map = ["小双", "小单", "大双", "大单"]
    return {"pred": f"推【{res_map[int(offset * 4) % 4]}】", "name": "4D双组权重"}

# 2. V23-ARMOR 杀形态
def algo_2(data):
    # 统计近10期组合分布,排除最高频形态 (Kill-Group策略)
    combs = [i["combination"] for i in data[:10]]
    most_common = max(set(combs), key=combs.count)
    kill_map = {"大双": "小单", "小单": "大双", "大单": "小双", "小双": "大单"}
    return {"pred": f"杀【{most_common}】 建议:{kill_map.get(most_common, '反向对冲')}", "name": "V23形态杀手"}

# 3. V18-5y共振矩阵
def algo_3(data):
    # 5y算法:根据上期总和对5取模,映射动态波动表
    last_total = sum(int(x) for x in data[0]["number"].split("+"))
    mod5 = last_total % 5
    five_y = {0: "大双", 1: "小单", 2: "大单", 3: "小双", 4: "极值对冲"}
    return {"pred": f"5y共振 -> 【{five_y[mod5]}】", "name": "V18-5y共振"}

# 4. 指数加权动态尾流 (Tail Flow)
def algo_4(data):
    # 提取末尾数字进行指数加权处理
    tails = [int(i["number"].split("+")[-1]) for i in data[:10]]
    weighted_tail = sum(t * (0.1 * (idx+1)) for idx, t in enumerate(reversed(tails)))
    res = "大" if weighted_tail >= 4.5 else "小"
    return {"pred": f"尾流导向 -> 【{res}】", "name": "动态尾流模型"}

# 5. 马尔可夫转移矩阵 (Markov)
def algo_5(data):
    # 基于状态转移概率预测下一期
    states = ["单" if sum(int(x) for x in i["number"].split("+")) % 2 != 0 else "双" for i in data[:20]]
    transitions = []
    for i in range(len(states)-1):
        if states[i+1] == states[0]: transitions.append(states[i])
    pred = max(set(transitions), key=transitions.count) if transitions else "未知"
    return {"pred": f"状态转移 -> 【{pred}】", "name": "马尔可夫链"}

# 6. 综合全能对冲
def algo_6(data):
    # 集合前五个算法的结果进行投票
    results = [algo_1(data)["pred"], algo_3(data)["pred"], algo_5(data)["pred"]]
    return {"pred": " + ".join(list(set(results))[:2]), "name": "全能对冲引擎"}

MODELS = {
    "1": {"func": algo_1, "name": "4D双组权重"},
    "2": {"func": algo_2, "name": "V23形态杀手"},
    "3": {"func": algo_3, "name": "V18-5y共振"},
    "4": {"func": algo_4, "name": "动态尾流模型"},
    "5": {"func": algo_5, "name": "马尔可夫链"},
    "6": {"func": algo_6, "name": "全能对冲引擎"}
}

# ==================== 菜单与逻辑 ====================

def main_reply_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🔮 获取预测", "⚙️ 切换模型", "🏆 榜单排行", "📊 最近战绩")
    return markup

@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "📊 **PC28 矩阵计算终端已连接**\n算法已同步至云端,手机关机不影响运行。", 
                     parse_mode="Markdown", reply_markup=main_reply_keyboard())

@bot.message_handler(func=lambda m: True)
def handle(m):
    global CURRENT_MODEL
    if m.text == "🔮 获取预测":
        data = get_latest_data()
        if not data: return
        res = MODELS[CURRENT_MODEL]["func"](data)
        msg = (f"💎 **{MODELS[CURRENT_MODEL]['name']}**\n"
               f"━━━━━━━━━━━━━━\n"
               f"📡 期号:`{data[0]['nbr']}`\n"
               f"🎯 推演:`{int(data[0]['nbr'])+1}` 期\n"
               f"🚫 方案:**{res['pred']}**\n"
               f"━━━━━━━━━━━━━━")
        bot.send_message(m.chat.id, msg, parse_mode="Markdown")
    
    elif m.text == "⚙️ 切换模型":
        markup = types.InlineKeyboardMarkup()
        for k, v in MODELS.items():
            markup.add(types.InlineKeyboardButton(v["name"], callback_data=f"set_{k}"))
        bot.send_message(m.chat.id, "请选择预测引擎:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_"))
def callback_set(call):
    global CURRENT_MODEL
    CURRENT_MODEL = call.data.split("_")[1]
    bot.edit_message_text(f"✅ 已切换至: {MODELS[CURRENT_MODEL]['name']}", call.message.chat.id, call.message.message_id)

if __name__ == "__main__":
    print("🚀 矩阵算法已全量装载,24H运行中...")
    bot.infinity_polling()
