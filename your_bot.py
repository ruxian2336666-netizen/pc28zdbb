import telebot
from telebot import types
import requests
import math
import random
import time
from collections import Counter

# ==================== 配置区 ====================
BOT_TOKEN = "8789627493:AAExE8z-tRhrbGvENYVt4dxqWUFf56rrZJQ"
API_URL = "https://pc28.help/api/kj.json?nbr=100"
bot = telebot.TeleBot(BOT_TOKEN)

CURRENT_MODEL = "1" 

# ==================== 算法矩阵 ====================
def get_latest_data():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(API_URL, headers=headers, timeout=15).json()
        return resp.get("data", [])
    except Exception as e:
        print(f"数据抓取错误: {e}")
        return []

def algo_1(data):
    totals = [sum(int(x) for x in i["number"].split("+")) for i in data[:5]]
    phi = 1.61803398
    seed = (totals[0] * math.pi) / (totals[1] * phi if totals[1] > 0 else 1)
    offset = float("0." + str(seed).split(".")[1][:6])
    res_map = ["小双", "小单", "大双", "大单"]
    return {"pred": f"推【{res_map[int(offset * 4) % 4]}】", "name": "4D双组权重"}

def algo_2(data):
    combs = [i["combination"] for i in data[:10]]
    most_common = max(set(combs), key=combs.count)
    return {"pred": f"杀【{most_common}】", "name": "V23形态杀手"}

def algo_3(data):
    last_total = sum(int(x) for x in data[0]["number"].split("+"))
    mod5 = last_total % 5
    five_y = {0: "大双", 1: "小单", 2: "大单", 3: "小双", 4: "极值对冲"}
    return {"pred": f"5y共振 -> 【{five_y[mod5]}】", "name": "V18-5y共振"}

MODELS = {
    "1": {"func": algo_1, "name": "4D双组权重"},
    "2": {"func": algo_2, "name": "V23形态杀手"},
    "3": {"func": algo_3, "name": "V18-5y共振"}
}

# ==================== 消息处理 ====================
def main_reply_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🔮 获取预测", "⚙️ 切换模型", "🏆 榜单排行")
    return markup

@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "📊 **矩阵计算终端已连接**", parse_mode="Markdown", reply_markup=main_reply_keyboard())

@bot.message_handler(func=lambda m: m.text == "🔮 获取预测")
def predict(m):
    data = get_latest_data()
    if not data:
        bot.reply_to(m, "数据源连接失败")
        return
    res = MODELS[CURRENT_MODEL]["func"](data)
    msg = (f"💎 **{MODELS[CURRENT_MODEL]['name']}**\n"
           f"━━━━━━━━━━━━━━\n"
           f"📡 期号：`{data[0]['nbr']}`\n"
           f"🚫 方案：**{res['pred']}**\n"
           f"━━━━━━━━━━━━━━")
    bot.send_message(m.chat.id, msg, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "⚙️ 切换模型")
def change_model(m):
    markup = types.InlineKeyboardMarkup()
    for k, v in MODELS.items():
        markup.add(types.InlineKeyboardButton(v["name"], callback_data=f"set_{k}"))
    bot.send_message(m.chat.id, "请选择预测引擎:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_"))
def callback_set(call):
    global CURRENT_MODEL
    CURRENT_MODEL = call.data.split("_")[1]
    bot.answer_callback_query(call.id)
    bot.edit_message_text(f"✅ 已切换至: {MODELS[CURRENT_MODEL]['name']}", call.message.chat.id, call.message.message_id)

# ==================== 启动区 ====================
if __name__ == "__main__":
    print("🚀 机器人正在启动...")
    try:
        # 使用更稳健的轮询方式
        bot.infinity_polling(timeout=20, long_polling_timeout=10)
    except Exception as e:
        print(f"❌ 严重错误: {e}")
