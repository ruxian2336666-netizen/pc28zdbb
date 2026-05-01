import requests
import time
import math
import random
import telebot
from telebot import types
from collections import Counter
from datetime import datetime

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

# 全局缓存
global_kj_cache = []
global_keno_cache = []
global_yl_cache = {}
last_fetch_time = 0
FETCH_INTERVAL = random.randint(25, 35)

bot = telebot.TeleBot(BOT_TOKEN)

# ==================== 数据获取 ====================
def get_global_clean_data():
    global global_kj_cache, global_keno_cache, global_yl_cache, last_fetch_time
    now = time.time()
    if global_kj_cache and global_keno_cache and (now - last_fetch_time) < FETCH_INTERVAL:
        return global_kj_cache, global_keno_cache, global_yl_cache

    clean = []
    keno_data = []
    yl_data = {}

    try:
        resp = requests.get(API_KJ, timeout=8)
        if resp.status_code == 200:
            raw_list = resp.json().get("data", [])
            for item in raw_list:
                num_str = item.get("number", "")
                if not num_str:
                    continue
                try:
                    nums = [int(x) for x in num_str.split("+")]
                    total = sum(nums)
                    clean.append({
                        "nbr": item.get("nbr", ""),
                        "total": total,
                        "combination": item.get("combination", "未知"),
                        "number": num_str,
                        "nums": nums
                    })
                except:
                    continue
        if clean:
            global_kj_cache = clean

        resp2 = requests.get(API_KENO, timeout=8)
        if resp2.status_code == 200:
            keno_data = resp2.json().get("data", [])
            if keno_data:
                global_keno_cache = keno_data

        resp3 = requests.get(API_YL, timeout=8)
        if resp3.status_code == 200:
            yl_data = resp3.json().get("data", {})
            if yl_data:
                global_yl_cache = yl_data

        last_fetch_time = now
        return global_kj_cache, global_keno_cache, global_yl_cache
    except:
        return global_kj_cache, global_keno_cache, global_yl_cache


# ==================== 算法1：V8-Hybrid ====================
def algo_v8_hybrid(history, keno_data, yl_data):
    try:
        if not keno_data or len(keno_data) < 15:
            return "小双", 0

        best_w = {"keno": 55, "yl": 3.5}
        max_hits = -1

        for k_w in [35, 55, 75]:
            for y_w in [1.5, 3.5, 5.5]:
                hits = 0
                test_range = min(10, len(keno_data) - 1, len(history))
                for i in range(1, test_range + 1):
                    try:
                        nbrs = [int(n) for n in keno_data[i]["nbrs"].split(",")]
                        p_val = sum([nbrs[j] for j in [1, 4, 7, 10, 13, 16]]) % 10
                        raw_map = ["小双", "小单", "小双", "小单", "小双", "大单", "大双", "大单", "大双", "大单"]
                        keno_pred = raw_map[p_val]

                        scores = {"大单": 100.0, "小单": 100.0, "大双": 100.0, "小双": 100.0}
                        scores[keno_pred] += k_w
                        for cat in scores:
                            scores[cat] += float(yl_data.get(cat, 0)) * y_w

                        final_pred = sorted(scores.items(), key=lambda x: x[1], reverse=True)[0][0]
                        if history[i - 1]["combination"] == final_pred:
                            hits += 1
                    except:
                        continue
                if hits > max_hits:
                    max_hits = hits
                    best_w = {"keno": k_w, "yl": y_w}

        nbrs = [int(n) for n in keno_data[0]["nbrs"].split(",")]
        p_val = sum([nbrs[i] for i in [1, 4, 7, 10, 13, 16]]) % 10
        raw_map = ["小双", "小单", "小双", "小单", "小双", "大单", "大双", "大单", "大双", "大单"]

        scores = {"大单": 100.0, "小单": 100.0, "大双": 100.0, "小双": 100.0}
        scores[raw_map[p_val]] += best_w["keno"]
        for cat in scores:
            scores[cat] += float(yl_data.get(cat, 0)) * best_w["yl"]

        result = sorted(scores.items(), key=lambda x: x[1], reverse=True)[0][0]
        return result, max_hits
    except:
        return "小双", 0


# ==================== 算法2：4D-PI+PHI ====================
def algo_4d_pi(history):
    try:
        if len(history) < 15:
            return "大双"
        phi = (1 + 5 ** 0.5) / 2
        latest = history[0]
        fixed_sum = sum(h["total"] for h in history[1:5]) if len(history) >= 5 else 52
        raw = (fixed_sum * phi) / (latest["total"] * math.pi if latest["total"] > 0 else 1.5)
        s = "{:.10f}".format(abs(raw - int(raw))).split('.')[1]
        idx = (int(s[0]) + int(s[2]) if len(s) > 2 else int(s[0])) % 10
        cat_map = {0: "小双", 1: "小单", 2: "小双", 3: "小单", 4: "小双", 5: "大单", 6: "大双", 7: "大单", 8: "大双", 9: "大单"}
        return cat_map[idx]
    except:
        return "大双"


# ==================== 算法3：Armor V23 ====================
def algo_v23_armor(history):
    try:
        if len(history) < 15:
            return "小单"

        recent_10 = [i["combination"] for i in history[:10]]
        recent_40 = [i["combination"] for i in history[:min(40, len(history))]]
        counts_40 = Counter(recent_40)
        curr_form = recent_10[0]
        prev_form = recent_10[1]

        opposites = {"大单": "小双", "小双": "大单", "大双": "小单", "小单": "大双"}
        all_forms = ["大单", "小单", "大双", "小双"]

        if curr_form == prev_form:
            return opposites.get(curr_form, "小单")

        if len(set(recent_10[:5])) >= 3:
            return sorted(all_forms, key=lambda x: abs(counts_40.get(x, 10) - 10))[0]

        return sorted(all_forms, key=lambda x: counts_40.get(x, 0))[0]
    except:
        return "小单"


# ==================== 算法4：5y Resonance ====================
def algo_5y_resonance(history):
    try:
        if len(history) < 15:
            return "大单"

        five_y_table = {
            0: [20, 15, 25, 5, 10],
            1: [1, 11, 21, 6, 16, 26],
            2: [2, 12, 22, 7, 17, 27],
            3: [13, 23, 3, 8, 18],
            4: [14, 24, 4, 19, 9]
        }

        def get_comb(n):
            size = "大" if n >= 14 else "小"
            oe = "单" if n % 2 != 0 else "双"
            return size + oe

        five_y_props = {}
        for k, nums in five_y_table.items():
            five_y_props[k] = Counter([get_comb(n) for n in nums])

        y_list = []
        for i in history[:15]:
            nums = i.get("nums", [int(x) for x in i["number"].split("+")])
            y_list.append(sum(nums) % 5)

        diffs = [y_list[i] - y_list[i + 1] for i in range(min(3, len(y_list) - 1))]
        avg_diff = sum(diffs) / len(diffs) if diffs else 0
        pred_y_idx = int(round(y_list[0] + avg_diff)) % 5

        recent_combs = Counter([i["combination"] for i in history[:20]])
        group_combs = five_y_props.get(pred_y_idx, Counter())

        scores = {}
        for comb in ["大单", "小单", "大双", "小双"]:
            scores[comb] = group_combs.get(comb, 0) * (recent_combs.get(comb, 0) + 2)

        return sorted(scores.items(), key=lambda x: x[1], reverse=True)[0][0]
    except:
        return "大单"


# ==================== 胜率排行 ====================
def get_backtest_rank():
    history, keno, yl = get_global_clean_data()
    if len(history) < 25:
        return []

    test_len = min(25, len(history) - 1)

    algos = {
        "V8-Hybrid": lambda h: algo_v8_hybrid(h, keno, yl)[0],
        "4D-PI+PHI": algo_4d_pi,
        "Armor V23": algo_v23_armor,
        "5y Resonance": algo_5y_resonance
    }

    ranks = []
    for name, func in algos.items():
        win = 0
        total = 0
        for i in range(1, test_len + 1):
            try:
                pred = func(history[i:])
                real = history[i - 1]["combination"]
                if pred == real:
                    win += 1
                total += 1
            except:
                continue
        if total > 0:
            rate = (win / total) * 100
            ranks.append({"name": name, "win": win, "total": total, "rate": rate})

    return sorted(ranks, key=lambda x: x["win"], reverse=True)


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


# ==================== 指令处理 ====================
@bot.message_handler(commands=['start'])
def welcome(m):
    text = (
        "**欢迎来到『小鶴神』矩阵终端 V17.0**\n"
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

    history, keno, yl = get_global_clean_data()
    if not history or len(history) < 10:
        bot.send_message(m.chat.id, "❌ 数据不足，请稍后再试（需至少10期数据）")
        return

    ranks = get_backtest_rank()

    res_v8, v8_hits = algo_v8_hybrid(history, keno, yl)
    res_4d = algo_4d_pi(history)
    res_armor = algo_v23_armor(history)
    res_5y = algo_5y_resonance(history)

    best_map = {
        "V8-Hybrid": res_v8,
        "4D-PI+PHI": res_4d,
        "Armor V23": res_armor,
        "5y Resonance": res_5y
    }
    best_name = ranks[0]["name"] if ranks else "V8-Hybrid"
    best_res = best_map.get(best_name, res_v8)

    try:
        next_issue = int(history[0]['nbr']) + 1
    except:
        next_issue = "?"

    msg = (
        f"🔮 **小鶴神矩阵全量预测 ({next_issue} 期)**\n"
        f"━━━━━━━━━━━━━━\n"
        f"🏆 最优算法: `{best_name}`\n"
        f"🎯 推荐形态: 【 **{best_res}** 】\n\n"
        f"📡 全部算法结果:\n"
        f"• V8-Hybrid: `{res_v8}` (近10中{v8_hits})\n"
        f"• 4D-PI+PHI: `{res_4d}`\n"
        f"• Armor杀组: `{res_armor}`\n"
        f"• 5y共振: `{res_5y}`\n"
        f"━━━━━━━━━━━━━━\n"
        f"📈 数据基于第{history[0]['nbr']}期"
    )
    bot.send_message(m.chat.id, msg, parse_mode="Markdown")


@bot.message_handler(func=lambda m: m.text == "📊 算法胜率排行")
def show_rank(m):
    if m.chat.id not in authorized_users:
        bot.send_message(m.chat.id, "⚠️ 请先登录授权")
        return
    ranks = get_backtest_rank()
    if not ranks:
        bot.send_message(m.chat.id, "❌ 数据不足，无法生成排行（需25期以上）")
        return
    txt = f"🏆 **近{ranks[0]['total']}期算法胜率榜单**\n━━━━━━━━━━━━━━\n"
    for i, r in enumerate(ranks):
        medal = ["🥇", "🥈", "🥉", "🎖️"][i] if i < 4 else "📊"
        txt += f"{medal} {r['name']}：{r['rate']:.1f}%  ({r['win']}/{r['total']})\n"
    txt += "━━━━━━━━━━━━━━\n⚠️ 历史数据仅作参考"
    bot.send_message(m.chat.id, txt, parse_mode="Markdown")


@bot.message_handler(func=lambda m: m.text == "📈 数据走势分析")
def data_analysis(m):
    if m.chat.id not in authorized_users:
        bot.send_message(m.chat.id, "⚠️ 请先登录授权")
        return

    history, _, _ = get_global_clean_data()
    if not history or len(history) < 20:
        bot.send_message(m.chat.id, "❌ 数据不足，需至少20期")
        return

    recent_20 = [h["combination"] for h in history[:20]]
    counter = Counter(recent_20)
    total = len(recent_20)

    max_streak = 1
    cur_streak = 1
    for i in range(1, len(recent_20)):
        if recent_20[i] == recent_20[i - 1]:
            cur_streak += 1
            max_streak = max(max_streak, cur_streak)
        else:
            cur_streak = 1

    all_nums = []
    for h in history[:20]:
        all_nums.extend(h.get("nums", [int(x) for x in h["number"].split("+")]))
    num_counter = Counter(all_nums)
    hot_nums = num_counter.most_common(5)
    cold_nums = num_counter.most_common()[:-6:-1]

    totals = [h["total"] for h in history[:20]]
    avg_total = sum(totals) / len(totals)

    txt = (
        f"📈 **近20期数据走势分析**\n"
        f"━━━━━━━━━━━━━━\n"
        f"📊 形态分布:\n"
        f"• 大单: {counter.get('大单',0)}次 ({counter.get('大单',0)/total*100:.1f}%)\n"
        f"• 小单: {counter.get('小单',0)}次 ({counter.get('小单',0)/total*100:.1f}%)\n"
        f"• 大双: {counter.get('大双',0)}次 ({counter.get('大双',0)/total*100:.1f}%)\n"
        f"• 小双: {counter.get('小双',0)}次 ({counter.get('小双',0)/total*100:.1f}%)\n\n"
        f"🔥 最大连号: {max_streak}期 ({recent_20[0]})\n"
        f"📌 当前形态: {recent_20[0]}\n"
        f"📊 平均和值: {avg_total:.1f}\n\n"
        f"🔴 热门数字: {', '.join([str(n[0]) for n in hot_nums])}\n"
        f"🔵 冷门数字: {', '.join([str(n[0]) for n in cold_nums])}\n"
        f"━━━━━━━━━━━━━━\n"
        f"⚠️ 历史数据仅作参考"
    )
    bot.send_message(m.chat.id, txt, parse_mode="Markdown")


@bot.message_handler(func=lambda m: m.text == "⚙️ 模型算法说明")
def algo_explain(m):
    if m.chat.id not in authorized_users:
        bot.send_message(m.chat.id, "⚠️ 请先登录授权")
        return
    text = (
        "⚙️ **模型算法详细说明**\n"
        "━━━━━━━━━━━━━━\n"
        "✅ V8-Hybrid\n多维度权重实时自我修正\n"
        "自动搜索最优keno权重(35-75)\n"
        "及遗漏回补权重(1.5-5.5)\n\n"
        "✅ 4D-PI+PHI\n黄金分割+圆周率算力偏移\n"
        "取小数点混合位增加变化\n\n"
        "✅ Armor V23\n三策略杀组：长龙杀对立\n"
        "震荡杀最稳 / 极冷拦截\n\n"
        "✅ 5y Resonance\n5y坐标漂移+属性共振锁定\n"
        "━━━━━━━━━━━━━━\n"
        "⚠️ 历史回测仅作参考"
    )
    bot.send_message(m.chat.id, text, parse_mode="Markdown")


@bot.message_handler(func=lambda m: m.text == "🔑 购买/续费卡密")
def buy_panel(m):
    bot.send_message(m.chat.id, "💎 请选择授权套餐", reply_markup=buy_keyboard())


@bot.message_handler(func=lambda m: m.text == "👤 联系人工客服")
def kf(m):
    bot.send_message(m.chat.id, f"👤 官方人工客服\n━━━━━━━━━━━━━━\n如有支付、卡密问题请联系：{CUSTOMER_SERVICE}")


# ==================== 回调事件 ====================
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
    print("🚀 小鶴神终端 已启动")
    bot.infinity_polling()
