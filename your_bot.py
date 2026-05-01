import requests
import time
import math
import random
from datetime import datetime
from collections import Counter
import telebot
from telebot import types

# ==================== [1] 核心配置 ====================
BOT_TOKEN = "8789627493:AAExE8z-tRhrbGvENYVt4dxqWUFf56rrZJQ"
IMG_WECHAT = "https://s1.ax1x.com/2023/10/31/peTEuKU.png"
IMG_ALIPAY = "https://s41.ax1x.com/2026/05/01/peTE1a9.jpg"
CUSTOMER_SERVICE = "@woaimss"

API_KJ = "https://pc28.help/api/kj.json?nbr=100"
API_KENO = "https://pc28.help/api/keno.json?nbr=100"
API_YL = "https://pc28.help/api/yl.json"

# 5y 映射表
five_y_table = {
    "5y0": [20, 15, 25, 5, 10], "5y1": [1, 11, 21, 6, 16, 26],
    "5y2": [2, 12, 22, 7, 17, 27], "5y3": [13, 23, 3, 8, 18],
    "5y4": [14, 24, 4, 19, 9]
}

CARD_DATABASE = ["xhs_vip_888"] + [f"xhs_card_{i}" for i in range(100)]
authorized_users = {} 

bot = telebot.TeleBot(BOT_TOKEN)

# ==================== [2] 四大完整算法 (严禁删减) ====================

def algo_v8_hybrid():
    """V8-HYBRID 权重自我修正"""
    try:
        keno = requests.get(API_KENO, timeout=5).json().get("data", [])
        yl = requests.get(API_YL, timeout=5).json().get("data", {})
        scores = {cat: 100.0 for cat in ["大单", "小单", "大双", "小双"]}
        nbrs = [int(n) for n in keno[0]["nbrs"].split(",")]
        # 严格执行 1,4,7,10,13,16 位取模逻辑
        p_val = sum([nbrs[i] for i in [1, 4, 7, 10, 13, 16]]) % 10
        raw_map = ["小双", "小单", "小双", "小单", "小双", "大单", "大双", "大单", "大双", "大单"]
        scores[raw_map[p_val]] += 55.0 
        for cat in scores: scores[cat] += float(yl.get(cat, 0)) * 3.5 
        res = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return f"{res[0][0]} + {res[1][0]}"
    except: return "V8数据溢出"

def algo_4d_pi(history):
    """4D-PI+PHI 算力偏移模型"""
    try:
        phi = (1 + 5**0.5) / 2
        latest = history[0]
        # 严格执行 13 固定权重与 4 期追溯
        fixed_sum = sum(13 for _ in history[1:5]) 
        raw = (fixed_sum * phi) / (latest["total"] * math.pi if latest["total"] > 0 else 1.5)
        s = "{:.10f}".format(abs(raw - int(raw))).split('.')[1]
        cat_map = {0:"小双", 1:"小单", 2:"小双", 3:"小单", 4:"小双", 5:"大单", 6:"大双", 7:"大单", 8:"大双", 9:"大单"}
        return f"{cat_map[int(s[0])]} + {cat_map[int(s[1])]}"
    except: return "4D算力载入中"

def algo_v23_armor(history):
    """V23-ARMOR 形态装甲必杀"""
    try:
        recent_10 = [i["combination"] for i in history[:10]]
        if recent_10[0] == recent_10[1]:
            # 龙位避让逻辑
            opposites = {"大单":"小双", "小双":"大单", "大双":"小单", "小单":"大双"}
            return f"🚫 杀: {opposites[recent_10[0]]}"
        return f"🚫 杀: {random.choice(['大单', '小单', '大双', '小双'])}"
    except: return "Armor部署中"

def algo_5y_resonance(history):
    """V18.1-RESONANCE 5y共振"""
    try:
        y_list = [int(sum(int(x) for x in i["number"].split("+")) % 5) for i in history[:15]]
        diffs = [y_list[i] - y_list[i+1] for i in range(3)]
        # 严格执行漂移修正与取模锁定
        pred_y_idx = int(round(y_list[0] + (sum(diffs)/3))) % 5
        return f"坐标 5y{pred_y_idx}"
    except: return "5y对齐失败"

# ==================== [3] 权限与入口 (严禁键盘越权) ====================

def get_auth_keyboard():
    """未登录状态下，输入框上方仅显示内联按钮"""
    mk = types.InlineKeyboardMarkup(row_width=2)
    mk.add(
        types.InlineKeyboardButton("🔑 购买授权", callback_data="buy_entry"),
        types.InlineKeyboardButton("🔓 立即登录", callback_data="login_entry")
    )
    return mk

def show_main_menu(chat_id):
    """登录成功后，推送常驻快捷键盘"""
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🔮 获取矩阵预测", "📊 历史胜率", "⚙️ 模型说明", "🔑 续费/购买")
    bot.send_message(chat_id, "💎 **主控台已解锁**\n\n所有算法已就绪。", reply_markup=kb)

@bot.message_handler(commands=['start'])
def start(m):
    if m.chat.id not in authorized_users:
        # 强制：未授权时不发送 ReplyKeyboardMarkup
        bot.send_message(m.chat.id, "🛡️ **矩阵终端 V15.4**\n请选择操作：", reply_markup=get_auth_keyboard())
    else:
        show_main_menu(m.chat.id)

@bot.callback_query_handler(func=lambda c: c.data == "login_entry")
def login_guide(c):
    bot.answer_callback_query(c.id)
    bot.send_message(c.message.chat.id, "⌨️ 请在下方直接输入 `xhs` 开头的卡密进行验证。")

@bot.message_handler(func=lambda m: m.text.startswith("xhs"))
def auth_process(m):
    if m.text.strip() in CARD_DATABASE:
        authorized_users[m.chat.id] = m.text.strip()
        bot.send_message(m.chat.id, "✅ **授权成功**")
        show_main_menu(m.chat.id)
    else:
        bot.send_message(m.chat.id, "❌ **卡密错误**")

# ==================== [4] 交易模块 (精确价格) ====================

@bot.message_handler(func=lambda m: m.text in ["🔑 续费/购买", "🔑 购买授权"])
def buy_info(m):
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(
        types.InlineKeyboardButton("🎫 天卡 - 5.88", callback_data="p_5.88"),
        types.InlineKeyboardButton("📅 周卡 - 18.88", callback_data="p_18.88"),
        types.InlineKeyboardButton("🌙 月卡 - 38.88", callback_data="p_38.88"),
        types.InlineKeyboardButton("👑 永久卡 - 88.88", callback_data="p_88.88")
    )
    bot.send_message(m.chat.id, "💎 **选择您的授权套餐：**", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("p_"))
def pay_select(c):
    bot.answer_callback_query(c.id)
    price = c.data.split("_")[1]
    mk = types.InlineKeyboardMarkup()
    mk.add(
        types.InlineKeyboardButton("微信支付", callback_data=f"qr_wx_{price}"),
        types.InlineKeyboardButton("支付宝支付", callback_data=f"qr_ali_{price}")
    )
    bot.edit_message_text(f"💰 待支付：`{price} 元`", c.message.chat.id, c.message.message_id, reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("qr_"))
def send_qr(c):
    bot.answer_callback_query(c.id)
    _, method, price = c.data.split("_")
    qr = IMG_WECHAT if method == "wx" else IMG_ALIPAY
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("✅ 我已支付 (核实截图)", callback_data="conf_pay"))
    bot.delete_message(c.message.chat.id, c.message.message_id)
    bot.send_photo(c.message.chat.id, qr, caption=f"🎯 **应付金额: {price} 元**", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "conf_pay")
def final_conf(c):
    bot.answer_callback_query(c.id, "正在核实", show_alert=True)
    bot.send_message(c.message.chat.id, f"👤 **请联系客服：{CUSTOMER_SERVICE}**")

# ==================== [5] 核心功能 (全量输出) ====================

@bot.message_handler(func=lambda m: m.text == "🔮 获取矩阵预测")
def handle_prediction(m):
    if m.chat.id not in authorized_users:
        bot.send_message(m.chat.id, "⚠️ 请先登录！", reply_markup=get_auth_keyboard())
        return
    try:
        raw_kj = requests.get(API_KJ).json().get("data", [])
        for i in raw_kj: i["total"] = sum(int(x) for x in i["number"].split("+"))
        
        # 调用全部完整算法
        v8 = algo_v8_hybrid()
        pi4d = algo_4d_pi(raw_kj)
        armor = algo_v23_armor(raw_kj)
        res5y = algo_5y_resonance(raw_kj)
        
        msg = (f"🔮 **矩阵全量预测 (第 {int(raw_kj[0]['nbr'])+1} 期)**\n"
               f"━━━━━━━━━━━━━━\n"
               f"⚡ **V8-Hybrid:** `{v8}`\n"
               f"🌀 **PI+PHI 4D:** `{pi4d}`\n"
               f"🛡️ **Armor 杀组:** `{armor}`\n"
               f"🧭 **5y 共振:** `{res5y}`\n"
               f"━━━━━━━━━━━━━━")
        bot.send_message(m.chat.id, msg, parse_mode="Markdown")
    except:
        bot.send_message(m.chat.id, "❌ 数据获取异常")

if __name__ == "__main__":
    bot.infinity_polling()
