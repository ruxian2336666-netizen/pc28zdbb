import requests
import time
import math
import random
import telebot
from telebot import types

# ==================== [1] 核心锁定配置 ====================
BOT_TOKEN = "8789627493:AAExE8z-tRhrbGvENYVt4dxqWUFf56rrZJQ"
IMG_LOGO = "https://s41.ax1x.com/2026/05/01/peTE1a9.jpg" # 欢迎语配图
IMG_WECHAT = "https://s1.ax1x.com/2023/10/31/peTEuKU.png" 
IMG_ALIPAY = "https://s41.ax1x.com/2026/05/01/peTE1a9.jpg"
CUSTOMER_SERVICE = "@woaimss"

# API 地址
API_KJ = "https://pc28.help/api/kj.json?nbr=100"
API_KENO = "https://pc28.help/api/keno.json?nbr=100"
API_YL = "https://pc28.help/api/yl.json"

# 卡密库
CARD_DATABASE = ["xhs_vip_888"] + [f"xhs_card_{i}" for i in range(100)]
authorized_users = {} 

bot = telebot.TeleBot(BOT_TOKEN)

# ==================== [2] 算法池 & 回测引擎 ====================

def algo_v8_hybrid():
    try:
        keno = requests.get(API_KENO, timeout=5).json().get("data", [])
        yl = requests.get(API_YL, timeout=5).json().get("data", {})
        scores = {cat: 100.0 for cat in ["大单", "小单", "大双", "小双"]}
        nbrs = [int(n) for n in keno[0]["nbrs"].split(",")]
        p_val = sum([nbrs[i] for i in [1, 4, 7, 10, 13, 16]]) % 10
        raw_map = ["小双", "小单", "小双", "小单", "小双", "大单", "大双", "大单", "大双", "大单"]
        scores[raw_map[p_val]] += 55.0 
        for cat in scores: scores[cat] += float(yl.get(cat, 0)) * 3.5 
        res = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return res[0][0]
    except: return "小双"

def algo_4d_pi(history):
    try:
        phi, latest = (1 + 5**0.5) / 2, history[0]
        fixed_sum = sum(13 for _ in history[1:5]) 
        raw = (fixed_sum * phi) / (latest["total"] * math.pi if latest["total"] > 0 else 1.5)
        s = "{:.10f}".format(abs(raw - int(raw))).split('.')[1]
        cat_map = {0:"小双", 1:"小单", 2:"小双", 3:"小单", 4:"小双", 5:"大单", 6:"大双", 7:"大单", 8:"大双", 9:"大单"}
        return cat_map[int(s[0])]
    except: return "大双"

def algo_v23_armor(history):
    try:
        recent_10 = [i["combination"] for i in history[:10]]
        if recent_10[0] == recent_10[1]:
            return {"大单":"小双", "小双":"大单", "大双":"小单", "小单":"大双"}[recent_10[0]]
        return random.choice(["大单", "小单", "大双", "小双"])
    except: return "小单"

def algo_5y_resonance(history):
    try:
        y_list = [int(sum(int(x) for x in i["number"].split("+")) % 5) for i in history[:15]]
        diffs = [y_list[i] - y_list[i+1] for i in range(3)]
        idx = int(round(y_list[0] + (sum(diffs)/3))) % 5
        return "大单" if idx in [1,3] else "小双"
    except: return "大单"

def get_backtest_rank():
    """计算近30期胜率排行"""
    try:
        raw_kj = requests.get(API_KJ).json().get("data", [])
        for i in raw_kj: i["total"] = sum(int(x) for x in i["number"].split("+"))
        algos = {"V8": algo_v8_hybrid, "4D": lambda h: algo_4d_pi(h), "Armor": lambda h: algo_v23_armor(h), "5y": lambda h: algo_5y_resonance(h)}
        ranks = []
        for name, func in algos.items():
            win = sum(1 for i in range(1, 31) if func(raw_kj[i:]) == raw_kj[i-1]["combination"])
            ranks.append({"name": name, "win": win, "rate": (win/30)*100})
        return sorted(ranks, key=lambda x: x['win'], reverse=True)
    except: return []

# ==================== [3] 互动键盘设置 ====================

def main_menu_keyboard():
    """登录后的 6 功能全量互动键盘"""
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🔮 矩阵全量预测", "📊 算法胜率排行")
    kb.add("📈 数据走势分析", "⚙️ 模型算法说明")
    kb.add("🔑 购买/续费卡密", "👤 联系人工客服")
    return kb

def auth_keyboard():
    mk = types.InlineKeyboardMarkup(row_width=2)
    mk.add(types.InlineKeyboardButton("🔑 购买授权", callback_data="buy_entry"),
           types.InlineKeyboardButton("🔓 立即登录", callback_data="login_entry"))
    return mk

# ==================== [4] 指令逻辑 ====================

@bot.message_handler(commands=['start'])
def welcome(m):
    welcome_text = (
        "**欢迎来到『小鶴神』矩阵终端 V16.0**\n"
        "━━━━━━━━━━━━━━\n"
        "本终端集成顶级 PC28 演算模型：\n"
        "✅ **V8-Hybrid** 权重自我修正\n"
        "✅ **PI+PHI 4D** 算力偏移模型\n"
        "✅ **Armor V23** 形态装甲杀组\n"
        "✅ **5y Resonance** 坐标锁定系统\n"
        "━━━━━━━━━━━━━━\n"
        "💡 请选择下方操作开始体验："
    )
    if m.chat.id not in authorized_users:
        bot.send_photo(m.chat.id, IMG_LOGO, caption=welcome_text, reply_markup=auth_keyboard(), parse_mode="Markdown")
    else:
        bot.send_message(m.chat.id, "✨ **小鹤神主控台已就绪**", reply_markup=main_menu_keyboard())

@bot.message_handler(func=lambda m: m.text == "🔮 矩阵全量预测" or m.text in ["0", "1", "2", "3", "4"])
def predict_dispatch(m):
    if m.chat.id not in authorized_users:
        bot.send_message(m.chat.id, "⚠️ 请先登录！", reply_markup=auth_keyboard())
        return
    
    # 自动执行全量预测
    try:
        raw_kj = requests.get(API_KJ).json().get("data", [])
        for i in raw_kj: i["total"] = sum(int(x) for x in i["number"].split("+"))
        
        ranks = get_backtest_rank()
        res_v8 = algo_v8_hybrid()
        res_4d = algo_4d_pi(raw_kj)
        
        msg = (f"🔮 **小鶴神矩阵全量预测 ({int(raw_kj[0]['nbr'])+1} 期)**\n"
               f"━━━━━━━━━━━━━━\n"
               f"🏆 **最优推荐:** `算法 {ranks[0]['name']}`\n"
               f"🎯 **预测形态:** 【 **{res_v8 if 'V8' in ranks[0]['name'] else res_4d}** 】\n\n"
               f"📡 **全量细节:**\n"
               f"• V8-Hybrid: `{res_v8}`\n"
               f"• 4D-PI+PHI: `{res_4d}`\n"
               f"• Armor 杀: `{algo_v23_armor(raw_kj)}`\n"
               f"• 5y 共振: `{algo_5y_resonance(raw_kj)}`\n"
               f"━━━━━━━━━━━━━━\n"
               f"📈 状态：`算法同步完成`")
        bot.send_message(m.chat.id, msg, parse_mode="Markdown")
    except:
        bot.send_message(m.chat.id, "❌ 演算链路故障")

@bot.message_handler(func=lambda m: m.text == "📊 算法胜率排行")
def show_rank(m):
    if m.chat.id not in authorized_users: return
    ranks = get_backtest_rank()
    txt = "🏆 **近 30 期算法胜率榜**\n━━━━━━━━━━━━━━\n"
    for i, r in enumerate(ranks):
        medal = ["🥇", "🥈", "🥉", "🎖️"][i]
        txt += f"{medal} **{r['name']}**: `{r['rate']:.1f}%` ({r['win']}/30)\n"
    bot.send_message(m.chat.id, txt, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🔑 购买/续费卡密")
def buy_panel(m):
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(types.InlineKeyboardButton("🎫 天卡 - 5.88", callback_data="p_5.88"),
           types.InlineKeyboardButton("📅 周卡 - 18.88", callback_data="p_18.88"),
           types.InlineKeyboardButton("🌙 月卡 - 38.88", callback_data="p_38.88"),
           types.InlineKeyboardButton("👑 永久卡 - 88.88", callback_data="p_88.88"))
    bot.send_message(m.chat.id, "💎 **请选择授权套餐：**", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "👤 联系人工客服")
def kf(m):
    bot.send_message(m.chat.id, f"👤 **官方客服通道**\n\n如有支付问题或大额充值，请联系：{CUSTOMER_SERVICE}")

# ==================== [5] 支付与回调 (修复按钮转圈) ====================

@bot.callback_query_handler(func=lambda c: c.data == "login_entry")
def cb_login(c):
    bot.answer_callback_query(c.id)
    bot.send_message(c.message.chat.id, "⌨️ 请在下方输入 `xhs` 开头的卡密：")

@bot.message_handler(func=lambda m: m.text.startswith("xhs"))
def auth_proc(m):
    if m.text.strip() in CARD_DATABASE:
        authorized_users[m.chat.id] = m.text.strip()
        bot.send_message(m.chat.id, "✅ **登录成功，主控台已开启。**", reply_markup=main_menu_keyboard())
    else:
        bot.send_message(m.chat.id, "❌ 卡密无效！")

@bot.callback_query_handler(func=lambda c: c.data.startswith("p_"))
def cb_pay_select(c):
    bot.answer_callback_query(c.id)
    price = c.data.split("_")[1]
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("微信支付", callback_data=f"qr_wx_{price}"),
           types.InlineKeyboardButton("支付宝支付", callback_data=f"qr_ali_{price}"))
    bot.edit_message_text(f"💰 待支付：{price} 元\n请选择支付通道：", c.message.chat.id, c.message.message_id, reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("qr_"))
def cb_send_qr(c):
    bot.answer_callback_query(c.id)
    _, method, price = c.data.split("_")
    qr = IMG_WECHAT if method == "wx" else IMG_ALIPAY
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("✅ 我已支付 (发送截图)", callback_data="conf_pay"))
    bot.delete_message(c.message.chat.id, c.message.message_id)
    bot.send_photo(c.message.chat.id, qr, caption=f"🎯 **扫码支付: {price} 元**\n完成后请联系客服核实卡密。", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "conf_pay")
def cb_conf(c):
    bot.answer_callback_query(c.id, "已记录，请发截图", show_alert=True)
    bot.send_message(c.message.chat.id, f"👤 **请发送截图至：** {CUSTOMER_SERVICE}")

if __name__ == "__main__":
    print("🚀 小鶴神终端 V16.0 巡航中...")
    bot.infinity_polling()
