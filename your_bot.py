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
    clean, keno_data, yl_data = [], [], {}
    try:
        resp = requests.get(API_KJ, timeout=8)
        if resp.status_code == 200:
            for item in resp.json().get("data", []):
                num_str = item.get("number", "")
                if not num_str: continue
                try:
                    nums = [int(x) for x in num_str.split("+")]
                    clean.append({"nbr": item.get("nbr", ""), "total": sum(nums), "combination": item.get("combination", "未知"), "number": num_str, "nums": nums})
                except: continue
        if clean: global_kj_cache = clean
        resp2 = requests.get(API_KENO, timeout=8)
        if resp2.status_code == 200:
            keno_data = resp2.json().get("data", [])
            if keno_data: global_keno_cache = keno_data
        resp3 = requests.get(API_YL, timeout=8)
        if resp3.status_code == 200:
            yl_data = resp3.json().get("data", {})
            if yl_data: global_yl_cache = yl_data
        last_fetch_time = now
    except: pass
    return global_kj_cache, global_keno_cache, global_yl_cache


# ==================== 原始4大算法 ====================
def algo_v8_hybrid(history, keno_data, yl_data):
    try:
        if not keno_data or len(keno_data) < 15: return ["小双", "小单"]
        best_w = {"keno": 55, "yl": 3.5}; max_hits = -1
        for k_w in [35, 55, 75]:
            for y_w in [1.5, 3.5, 5.5]:
                hits = 0
                for i in range(1, min(10, len(keno_data)-1, len(history))+1):
                    try:
                        nbrs = [int(n) for n in keno_data[i]["nbrs"].split(",")]
                        p_val = sum([nbrs[j] for j in [1,4,7,10,13,16]]) % 10
                        raw_map = ["小双","小单","小双","小单","小双","大单","大双","大单","大双","大单"]
                        scores = {"大单":100,"小单":100,"大双":100,"小双":100}
                        scores[raw_map[p_val]] += k_w
                        for cat in scores: scores[cat] += float(yl_data.get(cat,0)) * y_w
                        dual = sorted(scores, key=scores.get, reverse=True)[:2]
                        if history[i-1]["combination"] in dual: hits += 1
                    except: continue
                if hits > max_hits: max_hits = hits; best_w = {"keno":k_w, "yl":y_w}
        nbrs = [int(n) for n in keno_data[0]["nbrs"].split(",")]
        p_val = sum([nbrs[i] for i in [1,4,7,10,13,16]]) % 10
        raw_map = ["小双","小单","小双","小单","小双","大单","大双","大单","大双","大单"]
        scores = {"大单":100,"小单":100,"大双":100,"小双":100}
        scores[raw_map[p_val]] += best_w["keno"]
        for cat in scores: scores[cat] += float(yl_data.get(cat,0)) * best_w["yl"]
        return sorted(scores, key=scores.get, reverse=True)[:2]
    except: return ["小双","小单"]

def algo_4d_pi(history):
    try:
        if len(history) < 5: return ["大双","大单"]
        phi = (1+5**0.5)/2; latest = history[0]
        fixed_sum = sum(h["total"] for h in history[1:5]) if len(history)>=5 else 52
        raw = (fixed_sum*phi)/(latest["total"]*math.pi if latest["total"]>0 else 1.5)
        s = "{:.10f}".format(abs(raw-int(raw))).split('.')[1]
        cat_map = {0:"小双",1:"小单",2:"小双",3:"小单",4:"小双",5:"大单",6:"大双",7:"大单",8:"大双",9:"大单"}
        opp = {"大单":"小单","大双":"小双","小单":"大单","小双":"大双"}
        c1,c2 = cat_map[int(s[0])], cat_map[int(s[1])] if len(s)>1 else cat_map[(int(s[0])+5)%10]
        if c1==c2: c2=opp[c1]
        return [c1,c2]
    except: return ["大双","大单"]

def algo_v23_armor(history):
    try:
        if len(history)<15: return ["小单"],"数据不足"
        r10=[i["combination"] for i in history[:10]]
        r40=[i["combination"] for i in history[:min(40,len(history))]]
        c40=Counter(r40); curr,prev=r10[0],r10[1]
        opp={"大单":"小双","小双":"大单","大双":"小单","小单":"大双"}
        af=["大单","小单","大双","小双"]
        if curr==prev: s=opp.get(curr,"小单"); reason=f"【{curr}】长龙运行"
        elif len(set(r10[:5]))>=3: s=sorted(af,key=lambda x:abs(c40.get(x,10)-10))[0]; reason="盘路震荡"
        else:
            om={}
            for f in af:
                try: om[f]=r40.index(f)
                except: om[f]=40
            s=sorted(om,key=om.get,reverse=True)[0]; reason="形态深冷"
        return [s],reason
    except: return ["小单"],"数据异常"

def algo_5y_resonance(history):
    try:
        if len(history)<15: return ["大单","小双"]
        fyt={0:[20,15,25,5,10],1:[1,11,21,6,16,26],2:[2,12,22,7,17,27],3:[13,23,3,8,18],4:[14,24,4,19,9]}
        def gc(n): return ("大" if n>=14 else "小")+("单" if n%2!=0 else "双")
        fyp={k:Counter([gc(n) for n in nums]) for k,nums in fyt.items()}
        yl=[sum(i.get("nums",[int(x) for x in i["number"].split("+")]))%5 for i in history[:15]]
        diffs=[yl[i]-yl[i+1] for i in range(min(3,len(yl)-1))]
        avg=sum(diffs)/len(diffs) if diffs else 0
        pyi=int(round(yl[0]+avg))%5
        rc=Counter([i["combination"] for i in history[:20]])
        gc2=fyp.get(pyi,Counter())
        sc={comb:gc2.get(comb,0)*(rc.get(comb,0)+2) for comb in ["大单","小单","大双","小双"]}
        return [x[0] for x in sorted(sc.items(),key=lambda x:x[1],reverse=True)[:2]]
    except: return ["大单","小双"]


# ==================== 604个模型 ====================
ALL_MODELS = {}

# --- 杀组核心逻辑 ---
def master_slay_logic(history, config):
    if not history or len(history) < config['min_len']:
        return ["小单"], "基础数据不足"
    all_forms = ["大单", "小单", "大双", "小双"]
    opposites = {"大单": "小双", "小双": "大单", "大双": "小单", "小单": "大双"}
    recent = [h.get("combination", "小单") for h in history[:config['lookback']]]
    counts = Counter(recent)
    curr = recent[0]
    mode = config['mode']
    if mode == "COLD":
        target = sorted(all_forms, key=lambda x: counts.get(x, 0))[0]
        reason = f"冷态排除: {target}"
    elif mode == "HOT":
        target = sorted(all_forms, key=lambda x: counts.get(x, 0), reverse=True)[0]
        reason = f"过热回避: {target}"
    elif mode == "DRAGON":
        if len(recent) >= config['threshold'] and all(x == curr for x in recent[:config['threshold']]):
            target = opposites.get(curr, "小单")
            reason = f"长龙趋势拦截: {target}"
        else:
            target = random.choice(all_forms)
            reason = "非长龙区间随机杀"
    elif mode == "CYCLE":
        idx = (int(history[0].get('nbr', 0)) % config['mod_val']) % 4
        target = all_forms[idx]
        reason = f"周期性偏移杀: {target}"
    else:
        target = opposites.get(curr, "大单")
        reason = "形态对称性排除"
    return [target], reason

# --- 双组核心逻辑 ---
def master_dual_logic(history, keno, yl, config):
    all_forms = ["大单", "小单", "大双", "小双"]
    if not history or not keno: return [random.choice(all_forms), random.choice(all_forms)]
    scores = {cat: 100.0 for cat in all_forms}
    try:
        nbrs = [int(n) for n in keno[0].get("nbrs", "").split(",")]
        p_val = sum([nbrs[i] for i in config['keno_indices'] if i < len(nbrs)]) % 10
        raw_map = ["小双", "小单", "小双", "小单", "小双", "大单", "大双", "大单", "大双", "大单"]
        scores[raw_map[p_val]] += config['keno_weight']
    except: pass
    for cat in all_forms: scores[cat] += float(yl.get(cat, 0)) * config['yl_weight']
    recent = [h.get("combination") for h in history[:config['trend_depth']]]
    for cat in all_forms: scores[cat] += recent.count(cat) * config['trend_weight']
    return [x[0] for x in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:2]]

# --- 300个杀组模型 (1-300) ---
for i in range(1, 301):
    if i <= 60: conf = {'mode': "COLD", 'lookback': 10 + i, 'min_len': 15, 'desc': "冷态流"}
    elif i <= 120: conf = {'mode': "HOT", 'lookback': 20 + (i-60), 'min_len': 25, 'desc': "热态流"}
    elif i <= 180: conf = {'mode': "DRAGON", 'lookback': 5, 'threshold': 2 + (i % 4), 'min_len': 10, 'desc': "截龙流"}
    elif i <= 240: conf = {'mode': "CYCLE", 'mod_val': 3 + (i % 9), 'lookback': 1, 'min_len': 5, 'desc': "周期流"}
    else: conf = {'mode': "REVERSE", 'lookback': 1, 'min_len': 5, 'desc': "对称流"}
    ALL_MODELS[i] = {
        "func": lambda h, c=conf: master_slay_logic(h, c),
        "info": {"id": i, "name": f"杀组M{i}", "type": "杀组", "params": f"L:{conf['lookback']} M:{conf['mode']}"}
    }

# --- 300个双组模型 (301-600) ---
for i in range(1, 301):
    mid = i + 300
    if i <= 75: conf = {'keno_weight': 60 + (i * 0.4), 'yl_weight': 1.5, 'trend_weight': 5, 'trend_depth': 5, 'keno_indices': [1, 4, 7, 10, 13, 16], 'desc': "Keno领先型"}
    elif i <= 150: conf = {'keno_weight': 30, 'yl_weight': 3.0 + (i * 0.04), 'trend_weight': 10, 'trend_depth': 10, 'keno_indices': [0, 2, 5, 8, 11, 14], 'desc': "遗漏补偿型"}
    elif i <= 225: conf = {'keno_weight': 20, 'yl_weight': 1.0, 'trend_weight': 15 + (i * 0.15), 'trend_depth': 15 + (i % 7), 'keno_indices': [3, 6, 9, 12, 15, 18], 'desc': "趋势惯性型"}
    else: conf = {'keno_weight': 45, 'yl_weight': 2.5, 'trend_weight': 12, 'trend_depth': 8, 'keno_indices': random.sample(range(20), 6), 'desc': "混沌均衡型"}
    ALL_MODELS[mid] = {
        "func": lambda h, k, y, c=conf: master_dual_logic(h, k, y, c),
        "info": {"id": mid, "name": f"双组D{i}", "type": "双组", "params": f"K:{conf['keno_weight']:.1f} Y:{conf['yl_weight']:.2f} T:{conf['trend_weight']:.1f}"}
    }

# --- 4个原始算法 (601-604) ---
ALL_MODELS[601] = {"func": lambda h, k=None, y=None: algo_v8_hybrid(h, k, y), "info": {"id": 601, "name": "V8-Hybrid 双组(原)", "type": "双组", "params": "原始权重"}}
ALL_MODELS[602] = {"func": lambda h, k=None, y=None: algo_4d_pi(h), "info": {"id": 602, "name": "4D-PI+PHI 双组(原)", "type": "双组", "params": "原始算力"}}
ALL_MODELS[603] = {"func": lambda h, k=None, y=None: algo_v23_armor(h), "info": {"id": 603, "name": "Armor V23 杀组(原)", "type": "杀组", "params": "原始装甲"}}
ALL_MODELS[604] = {"func": lambda h, k=None, y=None: algo_5y_resonance(h), "info": {"id": 604, "name": "5y Resonance 双组(原)", "type": "双组", "params": "原始共振"}}


# ==================== 排行榜 ====================
def get_backtest_rank_top10(filter_type=None):
    history, keno, yl = get_global_clean_data()
    if len(history) < 25: return []
    MAX_BACKTEST = min(200, len(history) - 1)
    ranks = []
    for mid, md in ALL_MODELS.items():
        info = md["info"]
        if filter_type and info["type"] != filter_type: continue
        func = md["func"]; mt = info["type"]
        win = streak = ms = 0
        for i in range(1, MAX_BACKTEST + 1):
            try:
                h_slice = history[i:]
                if mt == "双组": p = func(h_slice, keno, yl)
                else: p = func(h_slice)
                if isinstance(p, tuple): p = p[0]
                actual = history[i-1]["combination"]
                if mt == "双组":
                    if actual in p: win += 1; streak += 1
                    else: streak = 0
                else:
                    if actual != p[0]: win += 1; streak += 1
                    else: streak = 0
                ms = max(ms, streak)
            except: continue
        rate = (win / MAX_BACKTEST) * 100
        ranks.append({"id": mid, "name": info["name"], "type": mt, "win": win, "total": MAX_BACKTEST, "rate": rate, "streak": ms, "current_streak": streak, "params": info["params"]})
    return sorted(ranks, key=lambda x: x["win"], reverse=True)[:10]


# ==================== 键盘 ====================
def main_menu_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🔮 输入编号预测", "📊 杀组胜率排行")
    kb.add("📊 双组胜率排行", "📈 数据走势分析")
    kb.add("🔍 模型编号查询", "🔑 购买/续费卡密")
    kb.add("👤 联系人工客服")
    return kb

def auth_keyboard():
    mk = types.InlineKeyboardMarkup(row_width=2)
    mk.add(types.InlineKeyboardButton("🔑 购买授权", callback_data="buy_entry"), types.InlineKeyboardButton("🔓 立即登录", callback_data="login_entry"))
    return mk

def buy_keyboard():
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(types.InlineKeyboardButton("🎫 天卡 - 5.88", callback_data="p_5.88"), types.InlineKeyboardButton("📅 周卡 - 18.88", callback_data="p_18.88"), types.InlineKeyboardButton("🌙 月卡 - 38.88", callback_data="p_38.88"), types.InlineKeyboardButton("👑 永久卡 - 88.88", callback_data="p_88.88"))
    return mk

def predict_refresh_keyboard(model_id):
    mk = types.InlineKeyboardMarkup(row_width=2)
    mk.add(types.InlineKeyboardButton("🔄 刷新预测", callback_data=f"refresh_{model_id}"), types.InlineKeyboardButton("📋 换模型", callback_data="change_model"))
    return mk

def check_auth(chat_id): return chat_id in authorized_users


# ==================== 统一模型调用 ====================
def run_model_pred(model_id, history, keno, yl):
    model_data = ALL_MODELS.get(model_id)
    if not model_data: return None, None
    info = model_data["info"]; func = model_data["func"]
    try:
        if info["type"] == "双组": result = func(history, keno, yl)
        else: result = func(history)
        return result, info
    except Exception as e:
        print(f"模型{model_id}错误: {e}")
        return None, info


# ==================== 指令 ====================
MAX_MODEL_ID = 604

@bot.message_handler(commands=['start'])
def welcome(m):
    text = f"欢迎来到『小鶴神』矩阵终端 V23.0\n━━━━━━━━━━━━━━\n集成{MAX_MODEL_ID}个演算模型\n杀组1-300 | 双组301-600 | 原始601-604\n━━━━━━━━━━━━━━\n输入编号即可预测"
    if check_auth(m.chat.id): bot.send_message(m.chat.id, "✨ 主控台已就绪", reply_markup=main_menu_keyboard())
    else: bot.send_photo(m.chat.id, IMG_LOGO, caption=text, reply_markup=auth_keyboard())

@bot.message_handler(func=lambda m: m.text in ["🔮 输入编号预测", "📊 杀组胜率排行", "📊 双组胜率排行", "📈 数据走势分析", "🔍 模型编号查询"])
def protected_features(m):
    if not check_auth(m.chat.id): bot.send_message(m.chat.id, "⚠️ 请先登录", reply_markup=auth_keyboard()); return
    if m.text == "🔮 输入编号预测": bot.send_message(m.chat.id, f"🎯 输入编号 (1-{MAX_MODEL_ID})")
    elif m.text == "📊 杀组胜率排行": show_rank(m, "杀组")
    elif m.text == "📊 双组胜率排行": show_rank(m, "双组")
    elif m.text == "📈 数据走势分析": data_analysis(m)
    elif m.text == "🔍 模型编号查询": bot.send_message(m.chat.id, f"📋 输入编号 (1-{MAX_MODEL_ID})")

@bot.message_handler(func=lambda m: m.text.isdigit() and 1 <= int(m.text) <= MAX_MODEL_ID)
def predict_by_model_id(m):
    if not check_auth(m.chat.id): bot.send_message(m.chat.id, "⚠️ 请先登录", reply_markup=auth_keyboard()); return
    model_id = int(m.text)
    history, keno, yl = get_global_clean_data()
    if not history: bot.send_message(m.chat.id, "❌ 无法获取开奖数据"); return
    result, info = run_model_pred(model_id, history, keno, yl)
    if result is None: bot.send_message(m.chat.id, f"❌ 模型{model_id}演算失败"); return
    test_len = min(100, len(history) - 1)
    win_count = streak = max_streak = 0
    for i in range(1, test_len + 1):
        try:
            h_slice = history[i:]
            if info["type"] == "双组": p = ALL_MODELS[model_id]["func"](h_slice, keno, yl)
            else: p = ALL_MODELS[model_id]["func"](h_slice)
            if isinstance(p, tuple): p = p[0]
            actual = history[i-1]["combination"]
            if info["type"] == "双组":
                if actual in p: win_count += 1; streak += 1
                else: streak = 0
            else:
                if actual != p[0]: win_count += 1; streak += 1
                else: streak = 0
            max_streak = max(max_streak, streak)
        except: continue
    try:
        next_issue = int(history[0]['nbr']) + 1
        if info["type"] == "双组":
            res_list = result[0] if isinstance(result, tuple) else result
            pred_text = f"🔥 双组: 【 {res_list[0]} + {res_list[1]} 】"
        else:
            if isinstance(result, tuple): slay_item, reason = result[0][0], result[1]
            else: slay_item, reason = result[0], "智能杀组"
            pred_text = f"🚫 必杀: 【 {slay_item} 】\n📝 {reason}"
        msg = (f"🎯 {info['name']} ({model_id})\n━━━━━━━━━━━━━━\n📡 上期: {history[0]['nbr']}期 → {history[0]['combination']}\n🎯 预测: {next_issue}期\n\n{pred_text}\n━━━━━━━━━━━━━━\n📈 近{test_len}期: {win_count/test_len*100:.1f}%\n🔥 连中: {streak} | 最大: {max_streak}\n⚙️ {info['params']}")
        bot.send_message(m.chat.id, msg, reply_markup=predict_refresh_keyboard(model_id))
    except Exception as e: bot.send_message(m.chat.id, f"❌ 处理异常: {e}")

@bot.callback_query_handler(func=lambda c: c.data.startswith("refresh_"))
def cb_refresh(c):
    chat_id = c.message.chat.id
    if not check_auth(chat_id): bot.answer_callback_query(c.id, "⚠️ 请先登录", show_alert=True); return
    model_id = int(c.data.split("_")[1])
    history, keno, yl = get_global_clean_data()
    if not history: bot.answer_callback_query(c.id, "数据不足", show_alert=True); return
    result, info = run_model_pred(model_id, history, keno, yl)
    if result is None: bot.answer_callback_query(c.id, "演算失败", show_alert=True); return
    test_len = min(100, len(history) - 1)
    win_count = streak = max_streak = 0
    for i in range(1, test_len + 1):
        try:
            h_slice = history[i:]
            if info["type"] == "双组": p = ALL_MODELS[model_id]["func"](h_slice, keno, yl)
            else: p = ALL_MODELS[model_id]["func"](h_slice)
            if isinstance(p, tuple): p = p[0]
            actual = history[i-1]["combination"]
            if info["type"] == "双组":
                if actual in p: win_count += 1; streak += 1
                else: streak = 0
            else:
                if actual != p[0]: win_count += 1; streak += 1
                else: streak = 0
            max_streak = max(max_streak, streak)
        except: continue
    try:
        next_issue = int(history[0]['nbr']) + 1
        if info["type"] == "双组":
            res_list = result[0] if isinstance(result, tuple) else result
            pred_text = f"🔥 双组: 【 {res_list[0]} + {res_list[1]} 】"
        else:
            if isinstance(result, tuple): slay_item, reason = result[0][0], result[1]
            else: slay_item, reason = result[0], "智能杀组"
            pred_text = f"🚫 必杀: 【 {slay_item} 】\n📝 {reason}"
        msg = (f"🔄 {info['name']} ({model_id})\n━━━━━━━━━━━━━━\n📡 上期: {history[0]['nbr']}期 → {history[0]['combination']}\n🎯 预测: {next_issue}期\n\n{pred_text}\n━━━━━━━━━━━━━━\n📈 近{test_len}期: {win_count/test_len*100:.1f}%\n🔥 连中: {streak} | 最大: {max_streak}\n⚙️ {info['params']}")
        bot.edit_message_text(msg, chat_id, c.message.message_id, reply_markup=predict_refresh_keyboard(model_id))
        bot.answer_callback_query(c.id, "✅ 已刷新")
    except Exception as e: bot.answer_callback_query(c.id, f"错误: {e}", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data == "change_model")
def cb_change(c): bot.answer_callback_query(c.id); bot.send_message(c.message.chat.id, f"🎯 输入新编号 (1-{MAX_MODEL_ID})")

def show_rank(m, filter_type=None):
    ranks = get_backtest_rank_top10(filter_type)
    if not ranks: bot.send_message(m.chat.id, "❌ 数据不足"); return
    type_name = filter_type if filter_type else "全部"
    txt = f"🏆 TOP10 {type_name} (近{ranks[0]['total']}期)\n━━━━━━━━━━━━━━\n"
    for i, r in enumerate(ranks):
        medal = ["🥇","🥈","🥉"][i] if i < 3 else f"{i+1}."
        txt += f"{medal} #{r['id']} {r['name']}：{r['rate']:.1f}%\n   🔥 最大: {r['streak']} | 当前: {r['current_streak']}\n"
    bot.send_message(m.chat.id, txt)

def data_analysis(m):
    history, _, _ = get_global_clean_data()
    if not history or len(history) < 20: bot.send_message(m.chat.id, "❌ 数据不足"); return
    recent_20 = [h["combination"] for h in history[:20]]
    counter = Counter(recent_20); total = len(recent_20)
    max_streak = cur_streak = 1
    for i in range(1, len(recent_20)):
        if recent_20[i] == recent_20[i-1]: cur_streak += 1; max_streak = max(max_streak, cur_streak)
        else: cur_streak = 1
    all_nums = [x for h in history[:20] for x in h.get("nums", [int(x) for x in h["number"].split("+")])]
    num_counter = Counter(all_nums)
    hot_nums = num_counter.most_common(5); cold_nums = num_counter.most_common()[:-6:-1]
    totals = [h["total"] for h in history[:20]]; avg_total = sum(totals) / len(totals)
    txt = f"📈 近20期走势\n━━━━━━━━━━━━━━\n📊 形态:\n• 大单: {counter.get('大单',0)} ({counter.get('大单',0)/total*100:.1f}%)\n• 小单: {counter.get('小单',0)} ({counter.get('小单',0)/total*100:.1f}%)\n• 大双: {counter.get('大双',0)} ({counter.get('大双',0)/total*100:.1f}%)\n• 小双: {counter.get('小双',0)} ({counter.get('小双',0)/total*100:.1f}%)\n\n🔥 最大连号: {max_streak}期 ({recent_20[0]})\n📌 当前: {recent_20[0]}\n📊 均和: {avg_total:.1f}\n\n🔴 热号: {', '.join([str(n[0]) for n in hot_nums])}\n🔵 冷号: {', '.join([str(n[0]) for n in cold_nums])}"
    bot.send_message(m.chat.id, txt)

@bot.message_handler(func=lambda m: m.text == "🔑 购买/续费卡密")
def buy_panel(m): bot.send_message(m.chat.id, "💎 选择套餐", reply_markup=buy_keyboard())

@bot.message_handler(func=lambda m: m.text == "👤 联系人工客服")
def kf(m): bot.send_message(m.chat.id, f"👤 客服: {CUSTOMER_SERVICE}")

@bot.message_handler(func=lambda m: m.text.startswith("XHS"))
def auth_proc(m):
    chat_id, card = m.chat.id, m.text.strip()
    if card in CARD_DATABASE: authorized_users[chat_id] = card; bot.send_message(chat_id, "✅ 登录成功", reply_markup=main_menu_keyboard()); return
    success, msg = check_card_keyt(card, str(chat_id))
    if success: authorized_users[chat_id] = card; CARD_DATABASE.append(card); bot.send_message(chat_id, f"✅ {msg}", reply_markup=main_menu_keyboard())
    else: bot.send_message(chat_id, f"❌ {msg}")

@bot.callback_query_handler(func=lambda c: c.data == "login_entry")
def cb_login(c): bot.answer_callback_query(c.id); bot.send_message(c.message.chat.id, "⌨️ 输入 XHS 开头卡密")

@bot.callback_query_handler(func=lambda c: c.data == "buy_entry")
def cb_buy_entry(c): bot.answer_callback_query(c.id); bot.send_message(c.message.chat.id, "💎 选择套餐", reply_markup=buy_keyboard())

@bot.callback_query_handler(func=lambda c: c.data.startswith("p_"))
def cb_pay_select(c):
    bot.answer_callback_query(c.id); price = c.data.split("_")[1]
    mk = types.InlineKeyboardMarkup(); mk.add(types.InlineKeyboardButton("微信", callback_data=f"qr_wx_{price}"), types.InlineKeyboardButton("支付宝", callback_data=f"qr_ali_{price}"))
    bot.edit_message_text(f"💰 {price}元\n选择支付方式", c.message.chat.id, c.message.message_id, reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("qr_"))
def cb_send_qr(c):
    bot.answer_callback_query(c.id); _, method, price = c.data.split("_")
    img = IMG_WECHAT if method == "wx" else IMG_ALIPAY
    mk = types.InlineKeyboardMarkup(); mk.add(types.InlineKeyboardButton("✅ 我已支付", callback_data="conf_pay"))
    bot.delete_message(c.message.chat.id, c.message.message_id)
    bot.send_photo(c.message.chat.id, img, caption=f"🎯 扫码支付 {price} 元\n完成后点我已支付", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "conf_pay")
def cb_conf(c): bot.answer_callback_query(c.id, "已提交", show_alert=True); bot.send_message(c.message.chat.id, f"✅ 已登记，联系客服领卡: {CUSTOMER_SERVICE}")

if __name__ == "__main__":
    print(f"🚀 小鶴神 V23.0 ({MAX_MODEL_ID}模型) 已启动")
    while True:
        try: bot.infinity_polling(timeout=60, long_polling_timeout=30)
        except requests.exceptions.ReadTimeout: print("超时重连..."); time.sleep(3)
        except requests.exceptions.ConnectionError: print("断开重连..."); time.sleep(5)
        except Exception as e: print(f"异常: {e}"); time.sleep(5)
