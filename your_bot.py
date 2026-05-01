import requests
import time
import math
import random
import telebot
from telebot import types
from collections import Counter
from datetime import datetime

# ==================== 卡密通验证系统 ====================
KEYT_SERVER = "https://www.keyt.cn/kami/xianhe1314520/check.php"
KEYT_APP = "xianhxianhxianhexianhexianhe"
KEYT_SIGN_KEY = "xianhe1314"

def calc_sign(data):
    res = ""
    key_len = len(KEYT_SIGN_KEY)
    for i, ch in enumerate(data):
        ch_asc = ord(ch)
        kh_asc = ord(KEYT_SIGN_KEY[i % key_len])
        v = (ch_asc + kh_asc) % 256
        res += format(v, '02x')
    return res

def verify_response(raw):
    pos = raw.find("|sign=")
    if pos == -1:
        return None
    body = raw[:pos]
    sign = raw[pos + 6:]
    local_sign = calc_sign(body)
    if local_sign != sign:
        return None
    last_pipe = body.rfind("|")
    if last_pipe == -1:
        return None
    return body[:last_pipe]

def check_card_keyt(card, user_id):
    try:
        url = f"{KEYT_SERVER}?card={card}&mac={user_id}&app={KEYT_APP}&heart=1&t={int(time.time())}"
        resp = requests.get(url, timeout=10)
        raw = resp.text

        biz = verify_response(raw)
        if not biz:
            return False, "签名校验失败"

        parts = biz.split("|")

        if len(parts) >= 2 and parts[1] == "permanent":
            return True, "终身有效"

        if len(parts) >= 3 and parts[0] == "ok":
            days = parts[2]
            return True, f"验证通过，剩余{days}天"

        if len(parts) == 2 and parts[1] == "valid":
            return True, "验证通过"

        errors = {
            "invalid_card": "卡密无效",
            "expired": "卡密已过期",
            "banned": "卡密已被禁用",
            "device_mismatch": "设备不匹配",
            "missing_params": "参数不完整"
        }
        for key, msg in errors.items():
            if key in biz:
                return False, msg

        return False, biz

    except Exception as e:
        return False, f"验证异常: {e}"

# ==================== 核心配置 ====================
BOT_TOKEN = "8789627493:AAExE8z-tRhrbGvENYVt4dxqWUFf56rrZJQ"
IMG_LOGO = "https://s41.ax1x.com/2026/05/01/peTZHDU.jpg"
IMG_WECHAT = "https://s41.ax1x.com/2026/05/01/peTZ7uT.jpg"
IMG_ALIPAY = "https://s41.ax1x.com/2026/05/01/peTE1a9.jpg"
CUSTOMER_SERVICE = "@woaimss"

API_KJ = "https://pc28.help/api/kj.json?nbr=100"
API_KENO = "https://pc28.help/api/keno.json?nbr=100"
API_YL = "https://pc28.help/api/yl.json"

CARD_DATABASE = ["xhs_vip_888"] + [f"xhsyj_{random.randint(1000000000, 9999999999)}" for _ in range(100)]
authorized_users = {}

user_algo_choice = {}

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


# ==================== 算法1：V8-Hybrid 双组 ====================
def algo_v8_hybrid(history, keno_data, yl_data):
    try:
        if not keno_data or len(keno_data) < 15:
            return ["小双", "小单"], 0

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

                        sorted_res = sorted(scores.items(), key=lambda x: x[1], reverse=True)
                        dual = [sorted_res[0][0], sorted_res[1][0]]
                        if history[i - 1]["combination"] in dual:
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

        sorted_res = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [sorted_res[0][0], sorted_res[1][0]], max_hits
    except:
        return ["小双", "小单"], 0


# ==================== 算法2：4D-PI+PHI 双组 ====================
def algo_4d_pi(history):
    try:
        if len(history) < 5:
            return ["大双", "大单"]

        phi = (1 + 5 ** 0.5) / 2
        latest = history[0]
        fixed_sum = sum(h["total"] for h in history[1:5]) if len(history) >= 5 else 52
        raw = (fixed_sum * phi) / (latest["total"] * math.pi if latest["total"] > 0 else 1.5)
        s = "{:.10f}".format(abs(raw - int(raw))).split('.')[1]

        cat_map = {0: "小双", 1: "小单", 2: "小双", 3: "小单", 4: "小双", 5: "大单", 6: "大双", 7: "大单", 8: "大双", 9: "大单"}
        opp = {"大单": "小单", "大双": "小双", "小单": "大单", "小双": "大双"}

        c1 = cat_map[int(s[0])]
        c2 = cat_map[int(s[1])] if len(s) > 1 else cat_map[(int(s[0]) + 5) % 10]
        if c1 == c2:
            c2 = opp[c1]

        return [c1, c2]
    except:
        return ["大双", "大单"]


# ==================== 算法3：Armor V23 杀组 ====================
def algo_v23_armor(history):
    try:
        if len(history) < 15:
            return ["小单"], "数据不足"

        recent_10 = [i["combination"] for i in history[:10]]
        recent_40 = [i["combination"] for i in history[:min(40, len(history))]]
        counts_40 = Counter(recent_40)
        curr_form = recent_10[0]
        prev_form = recent_10[1]

        opposites = {"大单": "小双", "小双": "大单", "大双": "小单", "小单": "大双"}
        all_forms = ["大单", "小单", "大双", "小双"]

        if curr_form == prev_form:
            slay = opposites.get(curr_form, "小单")
            reason = f"【{curr_form}】长龙运行，阻断对立补位"
        elif len(set(recent_10[:5])) >= 3:
            slay = sorted(all_forms, key=lambda x: abs(counts_40.get(x, 10) - 10))[0]
            reason = "盘路震荡，杀掉平庸回归项"
        else:
            omissions = {}
            for f in all_forms:
                try:
                    omissions[f] = recent_40.index(f)
                except:
                    omissions[f] = 40
            slay = sorted(omissions, key=omissions.get, reverse=True)[0]
            reason = "形态深冷，判定无力回补"

        return [slay], reason
    except:
        return ["小单"], "数据异常"


# ==================== 算法4：5y Resonance 双组 ====================
def algo_5y_resonance(history):
    try:
        if len(history) < 15:
            return ["大单", "小双"]

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

        top_two = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:2]
        return [top_two[0][0], top_two[1][0]]
    except:
        return ["大单", "小双"]


# ==================== 胜率排行（上限200期 + 连中） ====================
def get_backtest_rank():
    history, keno, yl = get_global_clean_data()
    if len(history) < 25:
        return []

    MAX_BACKTEST = min(200, len(history) - 1)
    ranks = []

    # V8-Hybrid
    win = 0
    streak = 0
    max_streak = 0
    for i in range(1, MAX_BACKTEST + 1):
        try:
            dual, _ = algo_v8_hybrid(history[i:], keno, yl)
            if history[i - 1]["combination"] in dual:
                win += 1
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 0
        except:
            continue
    ranks.append({
        "name": "V8-Hybrid 双组",
        "win": win,
        "total": MAX_BACKTEST,
        "rate": (win / MAX_BACKTEST) * 100,
        "type": "双组",
        "streak": max_streak,
        "current_streak": streak
    })

    # 4D-PI+PHI
    win = 0
    streak = 0
    max_streak = 0
    for i in range(1, MAX_BACKTEST + 1):
        try:
            dual = algo_4d_pi(history[i:])
            if history[i - 1]["combination"] in dual:
                win += 1
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 0
        except:
            continue
    ranks.append({
        "name": "4D-PI+PHI 双组",
        "win": win,
        "total": MAX_BACKTEST,
        "rate": (win / MAX_BACKTEST) * 100,
        "type": "双组",
        "streak": max_streak,
        "current_streak": streak
    })

    # Armor V23 杀组
    win = 0
    streak = 0
    max_streak = 0
    for i in range(1, MAX_BACKTEST + 1):
        try:
            slay, _ = algo_v23_armor(history[i:])
            if history[i - 1]["combination"] != slay[0]:
                win += 1
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 0
        except:
            continue
    ranks.append({
        "name": "Armor V23 杀组",
        "win": win,
        "total": MAX_BACKTEST,
        "rate": (win / MAX_BACKTEST) * 100,
        "type": "杀组",
        "streak": max_streak,
        "current_streak": streak
    })

    # 5y Resonance
    win = 0
    streak = 0
    max_streak = 0
    for i in range(1, MAX_BACKTEST + 1):
        try:
            dual = algo_5y_resonance(history[i:])
            if history[i - 1]["combination"] in dual:
                win += 1
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 0
        except:
            continue
    ranks.append({
        "name": "5y Resonance 双组",
        "win": win,
        "total": MAX_BACKTEST,
        "rate": (win / MAX_BACKTEST) * 100,
        "type": "双组",
        "streak": max_streak,
        "current_streak": streak
    })

    return sorted(ranks, key=lambda x: x["win"], reverse=True)


# ==================== 键盘菜单 ====================
def main_menu_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🔮 选择算法预测", "📊 算法胜率排行")
    kb.add("📈 数据走势分析", "⚙️ 模型算法说明")
    kb.add("🔑 购买/续费卡密", "👤 联系人工客服")
    return kb


def algo_select_keyboard():
    mk = types.InlineKeyboardMarkup(row_width=2)
    mk.add(
        types.InlineKeyboardButton("1️⃣ V8-Hybrid 双组", callback_data="algo_1"),
        types.InlineKeyboardButton("2️⃣ 4D-PI+PHI 双组", callback_data="algo_2")
    )
    mk.add(
        types.InlineKeyboardButton("3️⃣ Armor V23 杀组", callback_data="algo_3"),
        types.InlineKeyboardButton("4️⃣ 5y Resonance 双组", callback_data="algo_4")
    )
    return mk


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


# ==================== 统一授权检查 ====================
def check_auth(chat_id):
    if chat_id not in authorized_users:
        return False
    return True


# ==================== 指令处理 ====================
@bot.message_handler(commands=['start'])
def welcome(m):
    text = (
        "**欢迎来到『小鶴神』矩阵终端 V18.0**\n"
        "━━━━━━━━━━━━━━\n"
        "集成4大顶级PC28演算模型\n"
        "1️⃣ V8-Hybrid 权重自我修正\n"
        "2️⃣ PI+PHI 4D 算力偏移\n"
        "3️⃣ Armor V23 形态装甲杀组\n"
        "4️⃣ 5y Resonance 坐标锁定\n"
        "━━━━━━━━━━━━━━\n"
        "点击【选择算法预测】开始"
    )
    if check_auth(m.chat.id):
        bot.send_message(m.chat.id, "✨ 小鶴神主控台已就绪", reply_markup=main_menu_keyboard())
    else:
        bot.send_photo(m.chat.id, IMG_LOGO, caption=text, reply_markup=auth_keyboard(), parse_mode="Markdown")


# ========== 所有功能入口统一拦截 ==========
@bot.message_handler(func=lambda m: m.text in ["🔮 选择算法预测", "📊 算法胜率排行", "📈 数据走势分析", "⚙️ 模型算法说明"])
def protected_features(m):
    if not check_auth(m.chat.id):
        bot.send_message(m.chat.id, "⚠️ 此功能需要登录授权", reply_markup=auth_keyboard())
        return

    if m.text == "🔮 选择算法预测":
        algo_select(m)
    elif m.text == "📊 算法胜率排行":
        show_rank(m)
    elif m.text == "📈 数据走势分析":
        data_analysis(m)
    elif m.text == "⚙️ 模型算法说明":
        algo_explain(m)


def algo_select(m):
    bot.send_message(
        m.chat.id,
        "🎯 **请选择预测算法**\n\n"
        "1️⃣ V8-Hybrid 双组预测\n"
        "2️⃣ 4D-PI+PHI 双组预测\n"
        "3️⃣ Armor V23 杀组预测\n"
        "4️⃣ 5y Resonance 双组预测",
        reply_markup=algo_select_keyboard(),
        parse_mode="Markdown"
    )


# ========== 回调按钮 ==========
@bot.callback_query_handler(func=lambda c: c.data.startswith("algo_"))
def cb_algo_select(c):
    if not check_auth(c.message.chat.id):
        bot.answer_callback_query(c.id, "⚠️ 请先登录授权", show_alert=True)
        return
    bot.answer_callback_query(c.id)
    algo_num = int(c.data.split("_")[1])
    algo_names = {1: "V8-Hybrid 双组", 2: "4D-PI+PHI 双组", 3: "Armor V23 杀组", 4: "5y Resonance 双组"}
    user_algo_choice[c.message.chat.id] = algo_num

    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("🚀 开始预测", callback_data="start_predict"))

    bot.edit_message_text(
        f"✅ 已选择: **{algo_names[algo_num]}**\n点击下方开始预测",
        c.message.chat.id,
        c.message.message_id,
        reply_markup=mk,
        parse_mode="Markdown"
    )


@bot.callback_query_handler(func=lambda c: c.data == "start_predict")
def cb_start_predict(c):
    chat_id = c.message.chat.id

    if not check_auth(chat_id):
        bot.answer_callback_query(c.id, "⚠️ 请先登录授权", show_alert=True)
        return

    bot.answer_callback_query(c.id)
    algo_num = user_algo_choice.get(chat_id, 1)

    history, keno, yl = get_global_clean_data()
    if not history or len(history) < 10:
        bot.send_message(chat_id, "❌ 数据不足，请稍后再试")
        return

    try:
        next_issue = int(history[0]['nbr']) + 1
    except:
        next_issue = "?"

    bot.delete_message(chat_id, c.message.message_id)

    test_len = min(200, len(history) - 1)

    if algo_num == 1:
        dual, hits = algo_v8_hybrid(history, keno, yl)
        win_count = 0
        current_streak = 0
        max_streak = 0
        streak = 0
        for i in range(1, test_len + 1):
            try:
                d, _ = algo_v8_hybrid(history[i:], keno, yl)
                if history[i - 1]["combination"] in d:
                    win_count += 1
                    streak += 1
                    max_streak = max(max_streak, streak)
                else:
                    streak = 0
            except:
                continue
        current_streak = streak
        msg = (
            f"⚡ **V8-Hybrid 双组预测**\n"
            f"━━━━━━━━━━━━━━\n"
            f"📡 上期: {history[0]['nbr']}期 → {history[0]['combination']}\n"
            f"🎯 预测: {next_issue}期\n\n"
            f"🔥 双组推荐: 【 **{dual[0]} + {dual[1]}** 】\n"
            f"🚦 近10期命中: {hits}次\n"
            f"🔥 当前连中: {current_streak}期 | 最大连中: {max_streak}期\n"
            f"📈 近{test_len}期胜率: {win_count}/{test_len} ({win_count/test_len*100:.1f}%)\n"
            f"🛠️ 模式: 权重自我修正\n"
            f"━━━━━━━━━━━━━━\n"
            f"💡 双组命中即算对"
        )

    elif algo_num == 2:
        dual = algo_4d_pi(history)
        win_count = 0
        current_streak = 0
        max_streak = 0
        streak = 0
        for i in range(1, test_len + 1):
            try:
                d = algo_4d_pi(history[i:])
                if history[i - 1]["combination"] in d:
                    win_count += 1
                    streak += 1
                    max_streak = max(max_streak, streak)
                else:
                    streak = 0
            except:
                continue
        current_streak = streak
        msg = (
            f"🔮 **4D-PI+PHI 双组预测**\n"
            f"━━━━━━━━━━━━━━\n"
            f"📡 上期: {history[0]['nbr']}期 → {history[0]['combination']}\n"
            f"🎯 预测: {next_issue}期\n\n"
            f"🔥 双组推荐: 【 **{dual[0]} + {dual[1]}** 】\n"
            f"🔥 当前连中: {current_streak}期 | 最大连中: {max_streak}期\n"
            f"📈 近{test_len}期胜率: {win_count}/{test_len} ({win_count/test_len*100:.1f}%)\n"
            f"🧠 逻辑: 黄金分割+圆周率算力偏移\n"
            f"━━━━━━━━━━━━━━\n"
            f"💡 双组命中即算对"
        )

    elif algo_num == 3:
        slay, reason = algo_v23_armor(history)
        win_count = 0
        current_streak = 0
        max_streak = 0
        streak = 0
        for i in range(1, test_len + 1):
            try:
                s, _ = algo_v23_armor(history[i:])
                if history[i - 1]["combination"] != s[0]:
                    win_count += 1
                    streak += 1
                    max_streak = max(max_streak, streak)
                else:
                    streak = 0
            except:
                continue
        current_streak = streak
        msg = (
            f"🛡️ **Armor V23 杀组预测**\n"
            f"━━━━━━━━━━━━━━\n"
            f"📡 上期: {history[0]['nbr']}期 → {history[0]['combination']}\n"
            f"🎯 预测: {next_issue}期\n\n"
            f"🚫 下期必杀: 【 **{slay[0]}** 】\n"
            f"📝 理由: {reason}\n"
            f"🔥 当前连中: {current_streak}期 | 最大连中: {max_streak}期\n"
            f"📈 近{test_len}期杀对率: {win_count}/{test_len} ({win_count/test_len*100:.1f}%)\n"
            f"━━━━━━━━━━━━━━\n"
            f"💡 排除该形态，剩下3选1"
        )

    elif algo_num == 4:
        dual = algo_5y_resonance(history)
        win_count = 0
        current_streak = 0
        max_streak = 0
        streak = 0
        for i in range(1, test_len + 1):
            try:
                d = algo_5y_resonance(history[i:])
                if history[i - 1]["combination"] in d:
                    win_count += 1
                    streak += 1
                    max_streak = max(max_streak, streak)
                else:
                    streak = 0
            except:
                continue
        current_streak = streak
        y_list = []
        for i in history[:15]:
            nums = i.get("nums", [int(x) for x in i["number"].split("+")])
            y_list.append(sum(nums) % 5)
        diffs = [y_list[i] - y_list[i + 1] for i in range(min(3, len(y_list) - 1))]
        pred_y_idx = int(round(y_list[0] + sum(diffs) / len(diffs))) % 5 if diffs else 0

        msg = (
            f"🌀 **5y Resonance 双组预测**\n"
            f"━━━━━━━━━━━━━━\n"
            f"📡 上期: {history[0]['nbr']}期 → {history[0]['combination']}\n"
            f"🎯 预测: {next_issue}期\n\n"
            f"🧭 5y坐标: 5y{pred_y_idx}\n"
            f"🔥 双组推荐: 【 **{dual[0]} + {dual[1]}** 】\n"
            f"🔥 当前连中: {current_streak}期 | 最大连中: {max_streak}期\n"
            f"📈 近{test_len}期胜率: {win_count}/{test_len} ({win_count/test_len*100:.1f}%)\n"
            f"🧠 逻辑: 漂移修正+属性共振\n"
            f"━━━━━━━━━━━━━━\n"
            f"💡 双组命中即算对"
        )

    bot.send_message(chat_id, msg, parse_mode="Markdown")
    bot.send_message(chat_id, "🔄 可继续选择算法或查看其他功能", reply_markup=main_menu_keyboard())


def show_rank(m):
    ranks = get_backtest_rank()
    if not ranks:
        bot.send_message(m.chat.id, "❌ 数据不足，无法生成排行（需25期以上）")
        return
    txt = f"🏆 **近{ranks[0]['total']}期算法胜率榜单**\n━━━━━━━━━━━━━━\n"
    for i, r in enumerate(ranks):
        medal = ["🥇", "🥈", "🥉", "🎖️"][i] if i < 4 else "📊"
        note = "(双组命中)" if r["type"] == "双组" else "(杀对立)"
        txt += f"{medal} {r['name']}：{r['rate']:.1f}% ({r['win']}/{r['total']}) {note}\n"
        txt += f"   🔥 最大连中: {r['streak']}期 | 当前连中: {r['current_streak']}期\n"
    bot.send_message(m.chat.id, txt, parse_mode="Markdown")


def data_analysis(m):
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
    )
    bot.send_message(m.chat.id, txt, parse_mode="Markdown")


def algo_explain(m):
    text = (
        "⚙️ **模型算法详细说明**\n"
        "━━━━━━━━━━━━━━\n"
        "1️⃣ V8-Hybrid 双组预测\n"
        "多维度权重实时自我修正\n"
        "自动搜索最优keno权重(35-75)\n"
        "及遗漏回补权重(1.5-5.5)\n\n"
        "2️⃣ 4D-PI+PHI 双组预测\n"
        "黄金分割+圆周率算力偏移\n"
        "取小数位特征生成双组\n\n"
        "3️⃣ Armor V23 杀组预测\n"
        "三策略杀组：长龙杀对立\n"
        "震荡杀最稳 / 极冷拦截\n"
        "排除一个形态，剩下3选1\n\n"
        "4️⃣ 5y Resonance 双组预测\n"
        "5y坐标漂移+属性共振锁定\n"
    )
    bot.send_message(m.chat.id, text, parse_mode="Markdown")


@bot.message_handler(func=lambda m: m.text == "🔑 购买/续费卡密")
def buy_panel(m):
    bot.send_message(m.chat.id, "💎 请选择授权套餐", reply_markup=buy_keyboard())


@bot.message_handler(func=lambda m: m.text == "👤 联系人工客服")
def kf(m):
    bot.send_message(m.chat.id, f"👤 官方人工客服\n如有支付、卡密问题请联系：{CUSTOMER_SERVICE}")


# ==================== 卡密验证 ====================
@bot.message_handler(func=lambda m: m.text.startswith("xhs"))
def auth_proc(m):
    chat_id = m.chat.id
    card = m.text.strip()

    if card in CARD_DATABASE:
        authorized_users[chat_id] = card
        bot.send_message(chat_id, "✅ 登录成功！主控台已解锁", reply_markup=main_menu_keyboard())
        return

    success, msg = check_card_keyt(card, str(chat_id))

    if success:
        authorized_users[chat_id] = card
        CARD_DATABASE.append(card)
        bot.send_message(chat_id, f"✅ 登录成功！{msg}", reply_markup=main_menu_keyboard())
    else:
        bot.send_message(chat_id, f"❌ {msg}")


# ==================== 回调事件 ====================
@bot.callback_query_handler(func=lambda c: c.data == "login_entry")
def cb_login(c):
    bot.answer_callback_query(c.id)
    bot.send_message(c.message.chat.id, "⌨️ 请输入 xhs 开头卡密完成登录")


@bot.callback_query_handler(func=lambda c: c.data == "buy_entry")
def cb_buy_entry(c):
    bot.answer_callback_query(c.id)
    bot.send_message(c.message.chat.id, "💎 请选择下方套餐", reply_markup=buy_keyboard())


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
    print("🚀 小鶴神终端 V18.0 已启动")
    bot.infinity_polling()
