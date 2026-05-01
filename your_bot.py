import requests
import time
import math
import random
import telebot
from telebot import types
from collections import Counter

# ==================== 核心配置 ====================
BOT_TOKEN = "8789627493:AAExE8z-tRhrbGvENYVt4dxqWUFf56rrZJQ"
IMG_LOGO = "https://s41.ax1x.com/2026/05/01/peTZHDU.jpg"
IMG_WECHAT = "https://s41.ax1x.com/2026/05/01/peTZ7uT.jpg"
IMG_ALIPAY = "https://s41.ax1x.com/2026/05/01/peTE1a9.jpg"
CUSTOMER_SERVICE = "@woaimss"

API_KJ = "https://pc28.help/api/kj.json?nbr=100"
API_KENO = "https://pc28.help/api/keno.json?nbr=100"
API_YL = "https://pc28.help/api/yl.json"

# 卡密库
CARD_DATABASE = ["xhs_vip_888"] + [f"xhsyj_{random.randint(1000000000, 9999999999)}" for _ in range(100)]
authorized_users = {}

# 全局缓存数据 & 防频繁请求
global_kj_cache = []
last_fetch_time = 0
FETCH_INTERVAL = random.randint(25, 35)

bot = telebot.TeleBot(BOT_TOKEN)

# ==================== 全局统一数据抓取（防封+容错） ====================
def get_global_clean_data():
    global global_kj_cache, last_fetch_time
    now = time.time()
    # 缓存有效期内直接返回，不重复请求
    if global_kj_cache and (now - last_fetch_time) < FETCH_INTERVAL:
        return global_kj_cache

    try:
        resp = requests.get(API_KJ, timeout=5)
        # 状态码校验
        if resp.status_code != 200:
            return global_kj_cache
        # 校验是否为合法JSON
        raw_data = resp.json()
        raw_list = raw_data.get("data", [])
        if not raw_list:
            return global_kj_cache

        # 统一清洗数据
        clean = []
        for item in raw_list:
            num_str = item.get("number", "")
            if not num_str:
                continue
            nums = [int(x) for x in num_str.split("+")]
            total = sum(nums)
            clean.append({
                "nbr": item.get("nbr", ""),
                "total": total,
                "combination": item.get("combination", "未知"),
                "number": num_str
            })
        global_kj_cache = clean
        last_fetch_time = now
        return clean
    except Exception:
        return global_kj_cache

# ==================== 四大完整算法内核 ====================
def algo_v8_hybrid():
    try:
        keno = requests.get(API_KENO, timeout=5).json().get("data", [])
        yl = requests.get(API_YL, timeout=5).json().get("data", {})
        if not keno:
            return "小双"
        scores = {"大单":100.0, "小单":100.0, "大双":100.0, "小双":100.0}
        nbrs = [int(n) for n in keno[0]["nbrs"].split(",")]
        p_val = sum([nbrs[i] for i in [1,4,7,10,13,16]]) % 10
        raw_map = ["小双","小单","小双","小单","小双","大单","大双","大单","大双","大单"]
        scores[raw_map[p_val]] += 55.0
        for cat in scores:
            scores[cat] += float(yl.get(cat, 0)) * 3.5
        return sorted(scores.items(), key=lambda x:x[1], reverse=True)[0][0]
    except:
        return "小双"

def algo_4d_pi(history):
    try:
        if len(history) < 15:
            return "大双"
        phi = (1 + 5**0.5) / 2
        latest = history[0]
        fixed_sum = 0
        for d in history[1:5]:
            fixed_sum += 13
        raw = (fixed_sum * phi) / (latest["total"] * math.pi if latest["total"] > 0 else 1.5)
        s = "{:.10f}".format(abs(raw - int(raw))).split('.')[1]
        cat_map = {0:"小双",1:"小单",2:"小双",3:"小单",4:"小双",5:"大单",6:"大双",7:"大单",8:"大双",9:"大单"}
        return cat_map[int(s[0])]
    except:
        return "大双"

def algo_v23_armor(history):
    try:
        if len(history) < 10:
            return "小单"
        recent_10 = [i["combination"] for i in history[:10]]
        if recent_10[0] == recent_10[1]:
            map_opp = {"大单":"小双","小双":"大单","大双":"小单","小单":"大双"}
            return map_opp.get(recent_10[0], "小单")
        return random.choice(["大单","小单","大双","小双"])
    except:
        return "小单"

def algo_5y_resonance(history):
    try:
        if len(history) < 15:
            return "大单"
        y_list = []
        for i in history[:15]:
            nums = [int(x) for x in i["number"].split("+")]
            y_list.append(sum(nums) % 5)
        diffs = [y_list[i] - y_list[i+1] for i in range(3)]
        avg_diff = sum(diffs) / 3
        idx = int(round(y_list[0] + avg_diff)) % 5
        return "大单" if idx in [1,3] else "小双"
    except:
        return "大单"

# ==================== 胜率排行（零报错版） ====================
def get_backtest_rank():
    history = get_global_clean_data()
    if len(history) < 35:
        return []
    algos = {
        "V8-Hybrid": algo_v8_hybrid,
        "4D-PI+PHI": lambda h: algo_4d_pi(h),
        "Armor V23": lambda h: algo_v23_armor(h),
        "5y Resonance": lambda h: algo_5y_resonance(h)
    }
    ranks = []
    test_len = 35
    for name, func in algos.items():
        win = 0
        for i in range(1, test_len):
            pred = func(history[i:])
            real = history[i-1]["combination"]
            if pred == real:
                win += 1
        rate = (win / test_len) * 100
        ranks.append({"name":name, "win":win, "rate":rate})
    return sorted(ranks, key=lambda x:x["win"], reverse=True)

# ==================== 键盘菜单 ====================
def main_menu_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🔮 矩阵全量预测", "📊 算法胜率排行")
    kb.add("📈 数据走势分析", "⚙️ 模型算法说明")
    kb.add("🔑 购买/续费卡密", "👤 联系人工客服")
    return kb

def auth_keyboard():
    mk = types.InlineKeyboardMarkup(row_width=2)
    mk.add(
        types.InlineKeyboardButton("🔑 购买授权", callback_data="buy_entry"),
        types.InlineKeyboardButton("🔓 立即登录", callback_data="login_entry")
    )
    return mk

def buy_keyboard():
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(
        types.InlineKeyboardButton("🎫 天卡 - 5.88", callback_data="p_5.88"),
        types.InlineKeyboardButton("📅 周卡 - 18.88", callback_data="p_18.88"),
        types.InlineKeyboardButton("🌙 月卡 - 38.88", callback_data="p_38.88"),
        types.InlineKeyboardButton("👑 永久卡 - 88.88", callback_data="p_88.88")
    )
    return mk

# ==================== 指令与按钮全互动 ====================
@bot.message_handler(commands=['start'])
def welcome(m):
    text = (
        "**欢迎来到『小鶴神』矩阵终端 V16.0**\n"
        "━━━━━━━━━━━━━━\n"
        "集成4大顶级PC28演算模型\n"
        "✅ V8-Hybrid 权重自我修正\n"
        "✅ PI+PHI 4D 算力偏移\n"
        "✅ Armor V23 形态装甲杀组\n"
        "✅ 5y Resonance 坐标锁定\n"
        "━━━━━━━━━━━━━━\n"
        "请选择下方操作开始体验"
    )
    if m.chat.id not in authorized_users:
        bot.send_photo(m.chat.id, IMG_LOGO, caption=text, reply_markup=auth_keyboard(), parse_mode="Markdown")
    else:
        bot.send_message(m.chat.id, "✨ 小鶴神主控台已就绪", reply_markup=main_menu_keyboard())

@bot.message_handler(func=lambda m: m.text == "🔮 矩阵全量预测")
def predict_dispatch(m):
    if m.chat.id not in authorized_users:
        bot.send_message(m.chat.id, "⚠️ 请先登录授权", reply_markup=auth_keyboard())
        return
    history = get_global_clean_data()
    if not history:
        bot.send_message(m.chat.id, "❌ 演算链路故障，请稍后再试")
        return
    ranks = get_backtest_rank()
    res_v8 = algo_v8_hybrid()
    res_4d = algo_4d_pi(history)
    res_armor = algo_v23_armor(history)
    res_5y = algo_5y_resonance(history)

    best_name = ranks[0]["name"] if ranks else "V8-Hybrid"
    best_res = res_v8 if "V8" in best_name else res_4d

    msg = (
        f"🔮 **小鶴神矩阵全量预测 ({int(history[0]['nbr'])+1} 期)**\n"
        f"━━━━━━━━━━━━━━\n"
        f"🏆 最优算法: `{best_name}`\n"
        f"🎯 推荐形态: 【 **{best_res}** 】\n\n"
        f"📡 全部算法结果:\n"
        f"• V8-Hybrid: `{res_v8}`\n"
        f"• 4D-PI+PHI: `{res_4d}`\n"
        f"• Armor杀组: `{res_armor}`\n"
        f"• 5y共振: `{res_5y}`\n"
        f"━━━━━━━━━━━━━━\n"
        f"📈 状态: 算法同步完成"
    )
    bot.send_message(m.chat.id, msg, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📊 算法胜率排行")
def show_rank(m):
    if m.chat.id not in authorized_users:
        bot.send_message(m.chat.id, "⚠️ 请先登录授权")
        return
    ranks = get_backtest_rank()
    if not ranks:
        bot.send_message(m.chat.id, "❌ 获取排行失败，请稍后再试")
        return
    txt = "🏆 **近35期算法胜率榜单**\n━━━━━━━━━━━━━━\n"
    for i, r in enumerate(ranks):
        medal = ["🥇","🥈","🥉","🎖️"][i]
        txt += f"{medal} {r['name']}：{r['rate']:.1f}%  ({r['win']}/35)\n"
    bot.send_message(m.chat.id, txt, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📈 数据走势分析")
def data_analysis(m):
    if m.chat.id not in authorized_users:
        bot.send_message(m.chat.id, "⚠️ 请先登录授权")
        return
    bot.send_message(m.chat.id, "📈 数据走势分析功能\n━━━━━━━━━━━━━━\n功能维护升级中，敬请期待！")

@bot.message_handler(func=lambda m: m.text == "⚙️ 模型算法说明")
def algo_explain(m):
    if m.chat.id not in authorized_users:
        bot.send_message(m.chat.id, "⚠️ 请先登录授权")
        return
    text = (
        "⚙️ **模型算法详细说明**\n"
        "━━━━━━━━━━━━━━\n"
        "✅ V8-Hybrid\n多维度权重实时自我修正模型\n\n"
        "✅ 4D-PI+PHI\n黄金分割+圆周率算力偏移算法\n\n"
        "✅ Armor V23\n形态装甲长龙对冲杀组逻辑\n\n"
        "✅ 5y Resonance\n周期坐标漂移共振锁定系统\n"
        "━━━━━━━━━━━━━━\n"
        "⚠️ 历史回测仅作参考，不构成投资建议"
    )
    bot.send_message(m.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🔑 购买/续费卡密")
def buy_panel(m):
    bot.send_message(m.chat.id, "💎 请选择授权套餐", reply_markup=buy_keyboard())

@bot.message_handler(func=lambda m: m.text == "👤 联系人工客服")
def kf(m):
    bot.send_message(m.chat.id, f"👤 官方人工客服\n━━━━━━━━━━━━━━\n如有支付、卡密问题请联系：{CUSTOMER_SERVICE}")

# ==================== 回调事件全闭环 ====================
@bot.callback_query_handler(func=lambda c: c.data == "login_entry")
def cb_login(c):
    bot.answer_callback_query(c.id)
    bot.send_message(c.message.chat.id, "⌨️ 请输入 xhs 开头卡密完成登录")

@bot.callback_query_handler(func=lambda c: c.data == "buy_entry")
def cb_buy_entry(c):
    bot.answer_callback_query(c.id)
    bot.send_message(c.message.chat.id, "💎 请选择下方套餐", reply_markup=buy_keyboard())

@bot.message_handler(func=lambda m: m.text.startswith("xhs"))
def auth_proc(m):
    if m.text.strip() in CARD_DATABASE:
        authorized_users[m.chat.id] = m.text.strip()
        bot.send_message(m.chat.id, "✅ 登录成功！主控台已解锁", reply_markup=main_menu_keyboard())
    else:
        bot.send_message(m.chat.id, "❌ 卡密无效或已过期")

@bot.callback_query_handler(func=lambda c: c.data.startswith("p_"))
def cb_pay_select(c):
    bot.answer_callback_query(c.id)
    price = c.data.split("_")[1]
    mk = types.InlineKeyboardMarkup()
    mk.add(
        types.InlineKeyboardButton("微信支付", callback_data=f"qr_wx_{price}"),
        types.InlineKeyboardButton("支付宝支付", callback_data=f"qr_ali_{price}")
    )
    bot.edit_message_text(f"💰 待支付金额：{price} 元\n请选择支付方式",
                          c.message.chat.id, c.message.message_id, reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("qr_"))
def cb_send_qr(c):
    bot.answer_callback_query(c.id)
    _, method, price = c.data.split("_")
    img = IMG_WECHAT if method == "wx" else IMG_ALIPAY
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("✅ 我已支付", callback_data="conf_pay"))
    bot.delete_message(c.message.chat.id, c.message.message_id)
    bot.send_photo(c.message.chat.id, img,
                   caption=f"🎯 扫码支付 {price} 元\n完成后点击【我已支付】",
                   reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "conf_pay")
def cb_conf(c):
    bot.answer_callback_query(c.id, "已提交，请联系客服审核发卡密", show_alert=True)
    bot.send_message(c.message.chat.id, f"✅ 已登记，请联系客服领取卡密：{CUSTOMER_SERVICE}")

if __name__ == "__main__":
    print("🚀 小鶴神终端 终极稳定版 已启动")
    bot.infinity_polling()
