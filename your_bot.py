import requests
import time
import math
import random
from datetime import datetime
from collections import Counter
import telebot
from telebot import types

# ==================== [1] 核心锁定配置 ====================
BOT_TOKEN = "8789627493:AAExE8z-tRhrbGvENYVt4dxqWUFf56rrZJQ"
IMG_WECHAT = "https://s1.ax1x.com/2023/10/31/peTEuKU.png" 
IMG_ALIPAY = "https://s41.ax1x.com/2026/05/01/peTE1a9.jpg"
CUSTOMER_SERVICE = "@woaimss"

# API 地址
API_KJ = "https://pc28.help/api/kj.json?nbr=100"
API_KENO = "https://pc28.help/api/keno.json?nbr=100"
API_YL = "https://pc28.help/api/yl.json"

# 5y 映射表
five_y_table = {
    "5y0": [20, 15, 25, 5, 10], "5y1": [1, 11, 21, 6, 16, 26],
    "5y2": [2, 12, 22, 7, 17, 27], "5y3": [13, 23, 3, 8, 18],
    "5y4": [14, 24, 4, 19, 9]
}

# 卡密库
CARD_DATABASE = [f"xhs_day_{i:02d}" for i in range(1, 21)] + ["xhs_forever_vip_888"]
authorized_users = {}

bot = telebot.TeleBot(BOT_TOKEN)

# ==================== [2] 四大算法核心 (严禁精简) ====================

# 算法 1: V8-Hybrid 逻辑跳跃 (权重自我修正)
def algo_v8_hybrid():
    try:
        keno = requests.get(API_KENO, timeout=5).json().get("data", [])
        yl = requests.get(API_YL, timeout=5).json().get("data", {})
        scores = {"大单": 100.0, "小单": 100.0, "大双": 100.0, "小双": 100.0}
        nbrs = [int(n) for n in keno[0]["nbrs"].split(",")]
        p_val = sum([nbrs[i] for i in [1, 4, 7, 10, 13, 16]]) % 10
        raw_map = ["小双", "小单", "小双", "小单", "小双", "大单", "大双", "大单", "大双", "大单"]
        scores[raw_map[p_val]] += 55.0 # Keno 物理权重
        for cat in scores: scores[cat] += float(yl.get(cat, 0)) * 3.5 # 遗漏权重
        res = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return f"{res[0][0]} + {res[1][0]}"
    except: return "V8数据溢出"

# 算法 2: 4D-PI+PHI (算力偏移模型)
def algo_4d_pi(history):
    try:
        phi = (1 + 5**0.5) / 2
        latest = history[0]
        # 使用你要求的 13 固定权重逻辑
        fixed_sum = sum(13 for _ in history[1:5]) 
        raw = (fixed_sum * phi) / (latest["total"] * math.pi if latest["total"] > 0 else 1.5)
        s = "{:.10f}".format(abs(raw - int(raw))).split('.')[1]
        cat_map = {0:"小双", 1:"小单", 2:"小双", 3:"小单", 4:"小双", 5:"大单", 6:"大双", 7:"大单", 8:"大双", 9:"大单"}
        return f"{cat_map[int(s[0])]} + {cat_map[int(s[1])]}"
    except: return "4D算力载入中"

# 算法 3: V23-ARMOR (形态装甲必杀)
def algo_v23_armor(history):
    try:
        recent_10 = [i["combination"] for i in history[:10]]
        forms = ["大单", "小单", "大双", "小双"]
        if recent_10[0] == recent_10[1]:
            opposites = {"大单":"小双", "小双":"大单", "大双":"小单", "小单":"大双"}
            return f"杀【{opposites[recent_10[0]]}】"
        else:
            return f"杀【{random.choice(forms)}】" # 震荡拦截
    except: return "Armor部署中"

# 算法 4: V18.1-RESONANCE (5y 坐标锁定)
def algo_5y_resonance(history):
    try:
        y_list = [int(sum(int(x) for x in i["number"].split("+")) % 5) for i in history[:15]]
        diffs = [y_list[i] - y_list[i+1] for i in range(3)]
        pred_y_idx = int(round(y_list[0] + (sum(diffs)/3))) % 5
        return f"坐标 5y{pred_y_idx}"
    except: return "5y对齐失败"

# ==================== [3] 登录与权限 ====================
@bot.message_handler(commands=['start'])
def start(m):
    if m.chat.id not in authorized_users:
        mk = types.InlineKeyboardMarkup()
        mk.add(types.InlineKeyboardButton("🔑 购买授权卡密", callback_data="buy_entry"))
        bot.send_message(m.chat.id, "🛡️ **矩阵终端 V15.0 已锁定**\n请输入 `xhs` 开头的授权码解锁功能。", reply_markup=mk)
    else:
        main_menu(m.chat.id)

@bot.message_handler(func=lambda m: m.text.startswith("xhs"))
def auth(m):
    if m.text in CARD_DATABASE:
        authorized_users[m.chat.id] = m.text
        bot.send_message(m.chat.id, "✅ **身份验证通过**")
        main_menu(m.chat.id)
    else:
        bot.send_message(m.chat.id, "❌ **无效卡密**")

def main_menu(chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🔮 获取矩阵预测", "📊 胜率排行榜", "🔑 获取卡密", "⚙️ 模型说明")
    bot.send_message(chat_id, "💎 **主控台就绪，算法矩阵全量加载。**", reply_markup=kb)

# ==================== [4] 支付与客服逻辑 ====================
@bot.message_handler(func=lambda m: m.text == "🔑 获取卡密")
def buy_info(m):
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(
        types.InlineKeyboardButton("🎫 天卡 (xhs-Day) - 5.88", callback_data="p_5.88"),
        types.InlineKeyboardButton("👑 永久卡 (xhs-VIP) - 168.88", callback_data="p_168.88")
    )
    bot.send_message(m.chat.id, "💎 **请选择授权卡种：**", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("p_"))
def pay_type(c):
    price = c.data.split("_")[1]
    mk = types.InlineKeyboardMarkup()
    mk.add(
        types.InlineKeyboardButton("微信支付", callback_data=f"qr_wx_{price}"),
        types.InlineKeyboardButton("支付宝支付", callback_data=f"qr_ali_{price}")
    )
    bot.edit_message_text(f"💰 金额：`{price} 元` \n请选择支付通道：", c.message.chat.id, c.message.message_id, reply_markup=mk, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("qr_"))
def send_qr(c):
    _, method, price = c.data.split("_")
    qr = IMG_WECHAT if method == "wx" else IMG_ALIPAY
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("✅ 确认支付", callback_data="conf_pay"))
    bot.delete_message(c.message.chat.id, c.message.message_id)
    bot.send_photo(c.message.chat.id, qr, caption=f"🎯 **扫码支付: {price} 元**\n完成后请点击下方按钮核实。", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "conf_pay")
def conf_action(c):
    bot.send_message(c.message.chat.id, f"👤 **请联系客服核实发卡**\n\n发送支付截图至：{CUSTOMER_SERVICE}\n核实后发放以 `xhs` 开头的授权码。")

# ==================== [5] 预测输出 ====================
@bot.message_handler(func=lambda m: m.text == "🔮 获取矩阵预测")
def get_all_preds(m):
    if m.chat.id not in authorized_users:
        bot.send_message(m.chat.id, "⚠️ 请先登录卡密！")
        return
    try:
        raw_kj = requests.get(API_KJ).json().get("data", [])
        for i in raw_kj: i["total"] = sum(int(x) for x in i["number"].split("+"))
        
        v8 = algo_v8_hybrid()
        pi4d = algo_4d_pi(raw_kj)
        armor = algo_v23_armor(raw_kj)
        res5y = algo_5y_resonance(raw_kj)
        
        msg = (f"🔮 **PC28 矩阵全量预测**\n━━━━━━━━━━━━━━\n"
               f"📡 期号：`{int(raw_kj[0]['nbr'])+1}`\n\n"
               f"⚡ **V8-Hybrid:** `{v8}`\n"
               f"🌀 **PI+PHI 4D:** `{pi4d}`\n"
               f"🛡️ **Armor 杀组:** `{armor}`\n"
               f"🧭 **5y 共振:** `{res5y}`\n"
               f"━━━━━━━━━━━━━━\n"
               f"📈 当前状态：`算法同步中`")
        bot.send_message(m.chat.id, msg, parse_mode="Markdown")
    except:
        bot.send_message(m.chat.id, "❌ API 连接失败")

if __name__ == "__main__":
    bot.infinity_polling()
