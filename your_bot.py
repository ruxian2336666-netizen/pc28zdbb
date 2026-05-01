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

CARD_DATABASE = ["xhs_vip_888"]
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


# ==================== 原有4大算法 ====================
def algo_v8_hybrid(history, keno_data, yl_data):
    try:
        if not keno_data or len(keno_data) < 15:
            return ["小双", "小单"]
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
        return [sorted_res[0][0], sorted_res[1][0]]
    except:
        return ["小双", "小单"]


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
            return ("大" if n >= 14 else "小") + ("单" if n % 2 != 0 else "双")
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


# ==================== 204个模型 ====================
def generate_dual_models():
    models = {}
    all_forms = ["大单", "小单", "大双", "小双"]
    
    for idx in range(1, 101):
        model_id = idx
        k_w = random.choice([25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80])
        y_w = random.choice([1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0])
        base_score = random.choice([80, 90, 100, 110, 120])
        mix_mode = random.choice(["keno_first", "yl_first", "balanced", "random_mix"])
        use_opposite = random.choice([True, False])
        
        def make_dual_model(k_w, y_w, base_score, mix_mode, use_opposite):
            def dual_model(history, keno_data, yl_data):
                try:
                    if not keno_data or len(keno_data) < 2:
                        return [random.choice(all_forms), random.choice(all_forms)]
                    
                    scores = {cat: float(base_score) for cat in all_forms}
                    
                    if mix_mode in ["keno_first", "balanced", "random_mix"]:
                        try:
                            nbrs_str = keno_data[0].get("nbrs", "")
                            if nbrs_str:
                                nbrs = [int(n) for n in nbrs_str.split(",")]
                                n_len = len(nbrs)
                                if n_len >= 17:
                                    idx_list = [1, 4, 7, 10, 13, 16]
                                elif n_len >= 6:
                                    idx_list = random.sample(range(n_len), min(6, n_len))
                                else:
                                    idx_list = list(range(n_len))
                                if idx_list:
                                    p_val = sum([nbrs[i] for i in idx_list]) % 10
                                    raw_map = ["小双", "小单", "小双", "小单", "小双", "大单", "大双", "大单", "大双", "大单"]
                                    scores[raw_map[p_val]] += k_w
                        except:
                            pass
                    
                    if mix_mode in ["yl_first", "balanced"]:
                        for cat in all_forms:
                            try:
                                scores[cat] += float(yl_data.get(cat, 0)) * y_w
                            except:
                                pass
                    
                    if len(history) >= 5:
                        recent = [h.get("combination", "") for h in history[:5]]
                        for cat in all_forms:
                            scores[cat] += recent.count(cat) * random.uniform(5, 15)
                    
                    sorted_res = sorted(scores.items(), key=lambda x: x[1], reverse=True)
                    dual = [sorted_res[0][0], sorted_res[1][0]]
                    
                    if use_opposite and dual[0] == dual[1]:
                        opp = {"大单": "小单", "大双": "小双", "小单": "大单", "小双": "大双"}
                        dual[1] = opp.get(dual[0], random.choice([c for c in all_forms if c != dual[0]]))
                    
                    return dual
                except:
                    return [random.choice(all_forms), random.choice(all_forms)]
            return dual_model
        
        models[model_id] = {
            "func": make_dual_model(k_w, y_w, base_score, mix_mode, use_opposite),
            "info": {
                "id": model_id,
                "name": f"双组M{model_id}",
                "type": "双组",
                "params": f"K:{k_w} Y:{y_w} B:{base_score} M:{mix_mode} O:{use_opposite}"
            }
        }
    
    return models


def generate_slay_models():
    models = {}
    all_forms = ["大单", "小单", "大双", "小双"]
    opposites = {"大单": "小双", "小双": "大单", "大双": "小单", "小单": "大双"}
    
    for idx in range(1, 101):
        model_id = idx + 100
        strategy = random.choice(["long_dragon", "cold_hunt", "hot_avoid", "cycle_kill", "random_avoid", "trend_reverse"])
        lookback = random.choice([5, 10, 15, 20, 25, 30, 35, 40])
        threshold = random.choice([2, 3, 4, 5])
        
        def make_slay_model(strategy, lookback, threshold):
            def slay_model(history):
                try:
                    if len(history) < lookback + 2:
                        return [random.choice(all_forms)], "数据不足"
                    
                    recent = [i["combination"] for i in history[:lookback]]
                    counts = Counter(recent)
                    curr = recent[0]
                    
                    if strategy == "long_dragon":
                        if len(recent) >= 2 and recent[0] == recent[1]:
                            slay = opposites.get(curr, random.choice(all_forms))
                            reason = f"长龙{curr}，杀对立{slay}"
                        else:
                            slay = curr
                            reason = f"无长龙，杀当前{slay}"
                    
                    elif strategy == "cold_hunt":
                        slay = sorted(all_forms, key=lambda x: counts.get(x, 0))[0]
                        reason = f"杀最冷{slay}({counts.get(slay,0)}次)"
                    
                    elif strategy == "hot_avoid":
                        slay = sorted(all_forms, key=lambda x: counts.get(x, 0), reverse=True)[0]
                        reason = f"避热杀{slay}({counts.get(slay,0)}次)"
                    
                    elif strategy == "cycle_kill":
                        cycle_idx = (len(history) // max(threshold, 1)) % 4
                        slay = all_forms[cycle_idx]
                        reason = f"周期轮杀{slay}"
                    
                    elif strategy == "random_avoid":
                        slay = random.choice(all_forms)
                        reason = f"随机排除{slay}"
                    
                    elif strategy == "trend_reverse":
                        if len(recent) >= 3 and recent[0] == recent[1] == recent[2]:
                            slay = opposites.get(curr, random.choice(all_forms))
                            reason = f"三连{curr}，反转杀{slay}"
                        else:
                            slay = sorted(all_forms, key=lambda x: counts.get(x, 0))[0]
                            reason = f"趋势不明，杀最冷{slay}"
                    
                    else:
                        slay = random.choice(all_forms)
                        reason = f"默认{slay}"
                    
                    return [slay], f"[{strategy}] {reason}"
                except:
                    return [random.choice(all_forms)], "异常"
            return slay_model
        
        models[model_id] = {
            "func": make_slay_model(strategy, lookback, threshold),
            "info": {
                "id": model_id,
                "name": f"杀组M{model_id}",
                "type": "杀组",
                "params": f"S:{strategy} L:{lookback} T:{threshold}"
            }
        }
    
    return models


DUAL_MODELS = generate_dual_models()
SLAY_MODELS = generate_slay_models()
ALL_MODELS = {**DUAL_MODELS, **SLAY_MODELS}

ALL_MODELS[201] = {
    "func": lambda h, k, y: algo_v8_hybrid(h, k, y),
    "info": {"id": 201, "name": "V8-Hybrid 双组(原)", "type": "双组", "params": "原始权重"}
}
ALL_MODELS[202] = {
    "func": lambda h, k, y: algo_4d_pi(h),
    "info": {"id": 202, "name": "4D-PI+PHI 双组(原)", "type": "双组", "params": "原始算力"}
}
ALL_MODELS[203] = {
    "func": lambda h, k, y: algo_v23_armor(h)[0],
    "info": {"id": 203, "name": "Armor V23 杀组(原)", "type": "杀组", "params": "原始装甲"}
}
ALL_MODELS[204] = {
    "func": lambda h, k, y: algo_5y_resonance(h),
    "info": {"id": 204, "name": "5y Resonance 双组(原)", "type": "双组", "params": "原始共振"}
}


# ==================== 排行榜TOP10 ====================
def get_backtest_rank_top10():
    history, keno, yl = get_global_clean_data()
    if len(history) < 25:
        return []

    MAX_BACKTEST = min(200, len(history) - 1)
    ranks = []

    for model_id, model_data in ALL_MODELS.items():
        info = model_data["info"]
        func = model_data["func"]
        model_type = info["type"]
        
        win = 0
        streak = 0
        max_streak = 0
        
        for i in range(1, MAX_BACKTEST + 1):
            try:
                if model_type == "双组":
                    pred = func(history[i:], keno, yl)
                    if isinstance(pred, tuple):
                        pred = pred[0]
                    if history[i - 1]["combination"] in pred:
                        win += 1
                        streak += 1
                        max_streak = max(max_streak, streak)
                    else:
                        streak = 0
                else:
                    pred = func(history[i:])
                    if isinstance(pred, tuple):
                        pred = pred[0]
                    if history[i - 1]["combination"] != pred[0]:
                        win += 1
                        streak += 1
                        max_streak = max(max_streak, streak)
                    else:
                        streak = 0
            except:
                continue
        
        rate = (win / MAX_BACKTEST) * 100
        
        ranks.append({
            "id": model_id,
            "name": info["name"],
            "type": model_type,
            "win": win,
            "total": MAX_BACKTEST,
            "rate": rate,
            "streak": max_streak,
            "current_streak": streak,
            "params": info["params"]
        })

    return sorted(ranks, key=lambda x: x["win"], reverse=True)[:10]


# ==================== 键盘 ====================
def main_menu_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🔮 输入编号预测", "📊 算法胜率排行")
    kb.add("📈 数据走势分析", "🔍 模型编号查询")
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


def predict_refresh_keyboard(model_id):
    mk = types.InlineKeyboardMarkup(row_width=2)
    mk.add(
        types.InlineKeyboardButton("🔄 刷新预测", callback_data=f"refresh_{model_id}"),
        types.InlineKeyboardButton("📋 换模型", callback_data="change_model")
    )
    return mk


def check_auth(chat_id):
    return chat_id in authorized_users


# ==================== 指令 ====================
@bot.message_handler(commands=['start'])
def welcome(m):
    text = (
        "**欢迎来到『小鶴神』矩阵终端 V20.0**\n"
        "━━━━━━━━━━━━━━\n"
        "集成204个顶级PC28演算模型\n"
        "• 100个双组模型 (编号1-100)\n"
        "• 100个杀组模型 (编号101-200)\n"
        "• 4个原始算法 (编号201-204)\n"
        "━━━━━━━━━━━━━━\n"
        "输入编号即可预测"
    )
    if check_auth(m.chat.id):
        bot.send_message(m.chat.id, "✨ 小鶴神主控台已就绪", reply_markup=main_menu_keyboard())
    else:
        bot.send_photo(m.chat.id, IMG_LOGO, caption=text, reply_markup=auth_keyboard(), parse_mode="Markdown")


@bot.message_handler(func=lambda m: m.text in ["🔮 输入编号预测", "📊 算法胜率排行", "📈 数据走势分析", "🔍 模型编号查询"])
def protected_features(m):
    if not check_auth(m.chat.id):
        bot.send_message(m.chat.id, "⚠️ 请先登录授权", reply_markup=auth_keyboard())
        return

    if m.text == "🔮 输入编号预测":
        bot.send_message(m.chat.id, "🎯 请输入模型编号 (1-204)")
    elif m.text == "📊 算法胜率排行":
        show_rank(m)
    elif m.text == "📈 数据走势分析":
        data_analysis(m)
    elif m.text == "🔍 模型编号查询":
        bot.send_message(m.chat.id, "📋 请输入编号 (1-204)")


@bot.message_handler(func=lambda m: m.text.isdigit() and 1 <= int(m.text) <= 204)
def predict_by_model_id(m):
    if not check_auth(m.chat.id):
        bot.send_message(m.chat.id, "⚠️ 请先登录授权")
        return

    model_id = int(m.text)
    user_algo_choice[m.chat.id] = model_id

    history, keno, yl = get_global_clean_data()
    if not history or len(history) < 10:
        bot.send_message(m.chat.id, "❌ 数据不足")
        return

    try:
        next_issue = int(history[0]['nbr']) + 1
    except:
        next_issue = "?"

    model_data = ALL_MODELS.get(model_id)
    if not model_data:
        bot.send_message(m.chat.id, "❌ 模型不存在")
        return

    info = model_data["info"]
    func = model_data["func"]
    model_type = info["type"]

    test_len = min(200, len(history) - 1)
    win_count = 0
    streak = 0
    max_streak = 0

    for i in range(1, test_len + 1):
        try:
            if model_type == "双组":
                pred = func(history[i:], keno, yl)
                if isinstance(pred, tuple):
                    pred = pred[0]
                if history[i - 1]["combination"] in pred:
                    win_count += 1
                    streak += 1
                    max_streak = max(max_streak, streak)
                else:
                    streak = 0
            else:
                pred = func(history[i:])
                if isinstance(pred, tuple):
                    pred = pred[0]
                if history[i - 1]["combination"] != pred[0]:
                    win_count += 1
                    streak += 1
                    max_streak = max(max_streak, streak)
                else:
                    streak = 0
        except:
            continue

    current_streak = streak

    if model_type == "双组":
        result = func(history, keno, yl)
        if isinstance(result, tuple):
            result = result[0]
        pred_text = f"🔥 双组推荐: 【 **{result[0]} + {result[1]}** 】"
    else:
        result = func(history)
        reason = ""
        if isinstance(result, tuple):
            reason = result[1]
            result = result[0]
        else:
            reason = "策略杀组"
        pred_text = f"🚫 下期必杀: 【 **{result[0]}** 】\n📝 理由: {reason}"

    msg = (
        f"🎯 **{info['name']}** (编号{model_id})\n"
        f"━━━━━━━━━━━━━━\n"
        f"📡 上期: {history[0]['nbr']}期 → {history[0]['combination']}\n"
        f"🎯 预测: {next_issue}期\n\n"
        f"{pred_text}\n"
        f"━━━━━━━━━━━━━━\n"
        f"🔥 当前连中: {current_streak}期 | 最大连中: {max_streak}期\n"
        f"📈 近{test_len}期胜率: {win_count}/{test_len} ({win_count/test_len*100:.1f}%)\n"
        f"⚙️ 参数: {info['params']}\n"
        f"━━━━━━━━━━━━━━\n"
        f"💡 输入其他编号切换模型"
    )

    bot.send_message(m.chat.id, msg, parse_mode="Markdown", reply_markup=predict_refresh_keyboard(model_id))


@bot.callback_query_handler(func=lambda c: c.data.startswith("refresh_"))
def cb_refresh_predict(c):
    chat_id = c.message.chat.id
    if not check_auth(chat_id):
        bot.answer_callback_query(c.id, "⚠️ 请先登录授权", show_alert=True)
        return

    model_id = int(c.data.split("_")[1])
    user_algo_choice[chat_id] = model_id

    history, keno, yl = get_global_clean_data()
    if not history or len(history) < 10:
        bot.answer_callback_query(c.id, "数据不足", show_alert=True)
        return

    try:
        next_issue = int(history[0]['nbr']) + 1
    except:
        next_issue = "?"

    model_data = ALL_MODELS.get(model_id)
    if not model_data:
        bot.answer_callback_query(c.id, "模型不存在", show_alert=True)
        return

    info = model_data["info"]
    func = model_data["func"]
    model_type = info["type"]

    test_len = min(200, len(history) - 1)
    win_count = 0
    streak = 0
    max_streak = 0

    for i in range(1, test_len + 1):
        try:
            if model_type == "双组":
                pred = func(history[i:], keno, yl)
                if isinstance(pred, tuple):
                    pred = pred[0]
                if history[i - 1]["combination"] in pred:
                    win_count += 1
                    streak += 1
                    max_streak = max(max_streak, streak)
                else:
                    streak = 0
            else:
                pred = func(history[i:])
                if isinstance(pred, tuple):
                    pred = pred[0]
                if history[i - 1]["combination"] != pred[0]:
                    win_count += 1
                    streak += 1
                    max_streak = max(max_streak, streak)
                else:
                    streak = 0
        except:
            continue

    current_streak = streak

    if model_type == "双组":
        result = func(history, keno, yl)
        if isinstance(result, tuple):
            result = result[0]
        pred_text = f"🔥 双组推荐: 【 **{result[0]} + {result[1]}** 】"
    else:
        result = func(history)
        reason = ""
        if isinstance(result, tuple):
            reason = result[1]
            result = result[0]
        else:
            reason = "策略杀组"
        pred_text = f"🚫 下期必杀: 【 **{result[0]}** 】\n📝 理由: {reason}"

    msg = (
        f"🔄 **已刷新 {info['name']}** (编号{model_id})\n"
        f"━━━━━━━━━━━━━━\n"
        f"📡 上期: {history[0]['nbr']}期 → {history[0]['combination']}\n"
        f"🎯 预测: {next_issue}期\n\n"
        f"{pred_text}\n"
        f"━━━━━━━━━━━━━━\n"
        f"🔥 当前连中: {current_streak}期 | 最大连中: {max_streak}期\n"
        f"📈 近{test_len}期胜率: {win_count}/{test_len} ({win_count/test_len*100:.1f}%)\n"
        f"⚙️ 参数: {info['params']}"
    )

    bot.edit_message_text(msg, chat_id, c.message.message_id, parse_mode="Markdown", reply_markup=predict_refresh_keyboard(model_id))
    bot.answer_callback_query(c.id, "✅ 已刷新")


@bot.callback_query_handler(func=lambda c: c.data == "change_model")
def cb_change_model(c):
    bot.answer_callback_query(c.id)
    bot.send_message(c.message.chat.id, "🎯 请输入新的模型编号 (1-204)")


def show_rank(m):
    ranks = get_backtest_rank_top10()
    if not ranks:
        bot.send_message(m.chat.id, "❌ 数据不足")
        return
    txt = f"🏆 **TOP10 算法胜率榜单 (近{ranks[0]['total']}期)**\n━━━━━━━━━━━━━━\n"
    for i, r in enumerate(ranks):
        medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i+1}."
        note = "(双组)" if r["type"] == "双组" else "(杀组)"
        txt += f"{medal} #{r['id']} {r['name']}：{r['rate']:.1f}%  {note}\n"
        txt += f"   🔥 最大连中: {r['streak']}期 | 当前: {r['current_streak']}期\n"
    bot.send_message(m.chat.id, txt, parse_mode="Markdown")


def data_analysis(m):
    history, _, _ = get_global_clean_data()
    if not history or len(history) < 20:
        bot.send_message(m.chat.id, "❌ 数据不足")
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
    print("🚀 小鶴神终端 V20.0 已启动")
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=30)
        except requests.exceptions.ReadTimeout:
            print("超时重连...")
            time.sleep(3)
        except requests.exceptions.ConnectionError:
            print("连接断开重连...")
            time.sleep(5)
        except Exception as e:
            print(f"异常: {e}")
            time.sleep(5)
