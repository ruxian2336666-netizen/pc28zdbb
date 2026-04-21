# ==================== 假端口（让 Render 不报错） ====================
from http.server import HTTPServer, BaseHTTPRequestHandler
import os

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

def start_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()

import threading
threading.Thread(target=start_dummy_server, daemon=True).start()

# ==================== 真正的 Bot 代码 ====================
import requests
import time
import math
import random
from datetime import datetime
import json

# ==================== 配置区 ====================
BOT_TOKEN = "8789627493:AAFZd5F2tRHZqfslhEDKksngWK06uNiTbUU"
ADMIN_PASSWORD = "uo123456"

CHANNEL_IDS = [
    "@xhsttkx72738",
    "@xhszdbs1",
]

API_URL = "https://pc28.help/api/kj.json?nbr=30"
PREDICT_INTERVAL = 30
MAX_CONSECUTIVE_LOSS = 1
# =================================================

# 全局状态
authorized_users = set()
broadcast_running = False
current_algo = None
consecutive_loss = 0
last_update_id = 0
bot_username = ""

# 候选参数范围
PARAM_RANGES = {
    "大单": (10, 17),
    "小单": (10, 17),
    "大双": (11, 17),
    "小双": (11, 17)
}

# ==================== 算法核心函数 ====================
def get_category(total):
    size = "大" if total >= 14 else "小"
    oe = "单" if total % 2 == 1 else "双"
    return size + oe

def get_three_digits(decimal):
    s = str(decimal)[2:]
    digits = []
    seen = set()
    for ch in s:
        if ch.isdigit():
            num = int(ch) % 10
            if num not in seen:
                digits.append(num)
                seen.add(num)
        if len(digits) >= 3:
            break
    while len(digits) < 3:
        for i in range(10):
            if i not in seen:
                digits.append(i)
                seen.add(i)
                break
    return digits

def get_two_digits(decimal):
    s = str(decimal)[2:]
    if len(s) >= 2:
        result = s[:2]
    else:
        result = s + "0"
    return int(result[0]), int(result[1])

def get_omission(category, history):
    for i, h in enumerate(history):
        if h["category"] == category:
            return i
    return len(history)

def get_market_state(history):
    if len(history) < 6:
        return "震荡", 3
    categories = [h["category"] for h in history[:6]]
    streak = 1
    for i in range(1, len(categories)):
        if categories[i] == categories[0]:
            streak += 1
        else:
            break
    if streak >= 3:
        return "趋势", 5
    else:
        return "震荡", 3

def get_category_by_tail(tail):
    mapping = {0:"小双",1:"小单",2:"小双",3:"小单",4:"小双",5:"大单",6:"大双",7:"大单",8:"大双",9:"大单"}
    return mapping.get(tail, "大单")

def get_opposite(cat):
    mapping = {"大单":"小双","大双":"小单","小单":"大双","小双":"大单"}
    return mapping.get(cat, "小双")

def predict_v7_double(history, params):
    if len(history) < 5:
        return None
    latest = history[0]
    market_state, window_size = get_market_state(history)
    window_size = min(window_size, len(history) - 1)
    last_n = history[1:1+window_size]
    fixed_sum = 0
    weight_sum = 0
    for i, h in enumerate(last_n):
        w = len(last_n) - i
        omission = get_omission(h["category"], history[1:])
        adjust = 1 + min(omission, 10) * 0.03
        fixed_sum += params[h["category"]] * w * adjust
        weight_sum += w * adjust
    fixed_sum = fixed_sum / weight_sum if weight_sum > 0 else 0
    raw = fixed_sum / (latest["total"] * math.pi)
    decimal = raw - int(raw)
    tail1, tail2 = get_two_digits(decimal)
    cat1 = get_category_by_tail(tail1)
    cat2 = get_category_by_tail(tail2)
    if cat1 == cat2:
        cat2 = get_opposite(cat1)
    return [cat1, cat2], market_state, window_size

def predict_v7_kill(history, params):
    if len(history) < 5:
        return None
    latest = history[0]
    market_state, window_size = get_market_state(history)
    window_size = min(window_size, len(history) - 1)
    last_n = history[1:1+window_size]
    fixed_sum = 0
    weight_sum = 0
    for i, h in enumerate(last_n):
        w = len(last_n) - i
        omission = get_omission(h["category"], history[1:])
        adjust = 1 + min(omission, 10) * 0.03
        fixed_sum += params[h["category"]] * w * adjust
        weight_sum += w * adjust
    fixed_sum = fixed_sum / weight_sum if weight_sum > 0 else 0
    raw = fixed_sum / (latest["total"] * math.pi)
    decimal = raw - int(raw)
    tail1, tail2 = get_two_digits(decimal)
    cat1 = get_category_by_tail(tail1)
    cat2 = get_category_by_tail(tail2)
    if cat1 == cat2:
        kill = get_opposite(cat1)
    else:
        freq1 = sum(1 for h in history[1:10] if h["category"] == cat1)
        freq2 = sum(1 for h in history[1:10] if h["category"] == cat2)
        kill = cat1 if freq1 >= freq2 else cat2
    return kill, market_state, window_size

def predict_v7_ball(history, params):
    if len(history) < 5:
        return None
    latest = history[0]
    market_state, window_size = get_market_state(history)
    window_size = min(window_size, len(history) - 1)
    last_n = history[1:1+window_size]
    fixed_sum = 0
    weight_sum = 0
    for i, h in enumerate(last_n):
        w = len(last_n) - i
        omission = get_omission(h["category"], history[1:])
        adjust = 1 + min(omission, 10) * 0.03
        fixed_sum += params[h["category"]] * w * adjust
        weight_sum += w * adjust
    fixed_sum = fixed_sum / weight_sum if weight_sum > 0 else 0
    raw = fixed_sum / (latest["total"] * math.pi)
    decimal = raw - int(raw)
    kill_balls = get_three_digits(decimal)
    return kill_balls, market_state, window_size

def evaluate_params(history, params, algo_type):
    hits = 0
    total = 0
    for i in range(len(history) - 6):
        train = history[i+1:i+7]
        actual = history[i]
        if algo_type == "v7_double":
            result = predict_v7_double(train, params)
            if result:
                pred, _, _ = result
                if actual["category"] in pred:
                    hits += 1
        elif algo_type == "v7_kill":
            result = predict_v7_kill(train, params)
            if result:
                kill, _, _ = result
                if actual["category"] != kill:
                    hits += 1
        elif algo_type == "v7_ball":
            result = predict_v7_ball(train, params)
            if result:
                balls, _, _ = result
                if actual["b"] not in balls:
                    hits += 1
        total += 1
    return hits / total if total > 0 else 0

def adaptive_grid_search(history, algo_type, iterations=40):
    best_params = {"大单": 12, "小单": 13, "大双": 14, "小双": 15}
    best_score = -1
    for _ in range(iterations // 2):
        params = {
            "大单": random.randint(10, 17),
            "小单": random.randint(10, 17),
            "大双": random.randint(11, 17),
            "小双": random.randint(11, 17)
        }
        score = evaluate_params(history, params, algo_type)
        if score > best_score:
            best_score = score
            best_params = params.copy()
    for _ in range(iterations // 2):
        params = {
            "大单": best_params["大单"] + random.randint(-2, 2),
            "小单": best_params["小单"] + random.randint(-2, 2),
            "大双": best_params["大双"] + random.randint(-2, 2),
            "小双": best_params["小双"] + random.randint(-2, 2)
        }
        for k in params:
            params[k] = max(PARAM_RANGES[k][0], min(PARAM_RANGES[k][1], params[k]))
        score = evaluate_params(history, params, algo_type)
        if score > best_score:
            best_score = score
            best_params = params.copy()
    return best_params, best_score

def get_latest_data():
    resp = requests.get(API_URL, timeout=10)
    data = resp.json()["data"]
    history = []
    for item in data[:25]:
        nums = item["number"].split("+")
        a, b, c = int(nums[0]), int(nums[1]), int(nums[2])
        total = a + b + c
        dt = datetime.strptime(f"{item['date']} {item['time']}", "%Y-%m-%d %H:%M:%S")
        history.append({
            "issue": item["nbr"],
            "a": a, "b": b, "c": c,
            "total": total,
            "category": get_category(total)
        })
    return history

def send_channel_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    for channel in CHANNEL_IDS:
        try:
            requests.post(url, data={"chat_id": channel, "text": text}, timeout=10)
        except:
            pass

def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    requests.post(url, data=data)

def get_bot_info():
    global bot_username
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
    resp = requests.get(url)
    data = resp.json()
    if data.get("ok"):
        bot_username = data["result"]["username"]
        print(f"🤖 Bot用户名: @{bot_username}")

def get_updates():
    global last_update_id
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    if last_update_id:
        url += f"?offset={last_update_id + 1}"
    try:
        resp = requests.get(url, timeout=10)
        return resp.json().get("result", [])
    except:
        return []

def handle_command(chat_id, text, user_id, username):
    global broadcast_running, current_algo, authorized_users
    
    # 处理群聊中 @Bot 的消息
    if f"@{bot_username}" in text:
        clean_text = text.replace(f"@{bot_username}", "").strip()
        
        # 群聊登录
        if clean_text == ADMIN_PASSWORD:
            if user_id not in authorized_users:
                authorized_users.add(user_id)
                send_message(chat_id, "✅ 登录成功！\n\n现在可以使用：\n@Bot 切换算法 双组\n@Bot 切换算法 杀组\n@Bot 切换算法 杀球")
            else:
                send_message(chat_id, "🔐 您已登录")
            return
        
        # 群聊帮助
        if clean_text in ["帮助", "help"]:
            help_text = """🤖 **可用命令**

**切换算法：**
• @Bot 切换算法 双组
• @Bot 切换算法 杀组
• @Bot 切换算法 杀球

**其他：**
• @Bot 帮助
• @Bot 状态
• @Bot 停止"""
            send_message(chat_id, help_text)
            return
        
        # 需要登录才能用的命令
        if user_id not in authorized_users:
            send_message(chat_id, "❌ 请先登录：@Bot 密码")
            return
        
        if "切换算法" in clean_text:
            if not broadcast_running:
                send_message(chat_id, "❌ 播报未启动，请先私聊Bot启动")
                return
            
            if "双组" in clean_text:
                current_algo = "v7_double"
                send_message(chat_id, "✅ 已切换到 V7 双组版")
            elif "杀组" in clean_text:
                current_algo = "v7_kill"
                send_message(chat_id, "✅ 已切换到 V7 杀组版")
            elif "杀球" in clean_text or "杀b" in clean_text:
                current_algo = "v7_ball"
                send_message(chat_id, "✅ 已切换到 V7 杀b球版")
            else:
                send_message(chat_id, "❌ 请指定：双组 / 杀组 / 杀球")
            return
        
        if "状态" in clean_text:
            if broadcast_running:
                algo_name = {"v7_double":"双组","v7_kill":"杀组","v7_ball":"杀b球"}.get(current_algo, "未知")
                send_message(chat_id, f"🟢 播报中\n当前算法：{algo_name}")
            else:
                send_message(chat_id, "🔴 播报已停止")
            return
        
        if "停止" in clean_text:
            broadcast_running = False
            send_message(chat_id, "⏹️ 播报已停止")
            return
    
    # 私聊命令
    if text == "/start":
        send_message(chat_id, "🔐 请输入管理员密码：")
    
    elif text == ADMIN_PASSWORD and user_id not in authorized_users:
        authorized_users.add(user_id)
        send_message(chat_id, "✅ 登录成功！请选择播报算法：", {
            "keyboard": [
                [{"text": "V7 双组版"}, {"text": "V7 杀组版"}],
                [{"text": "V7 杀b球版"}, {"text": "停止播报"}]
            ],
            "resize_keyboard": True
        })
    
    elif user_id in authorized_users:
        if text == "V7 双组版":
            current_algo = "v7_double"
            broadcast_running = True
            send_message(chat_id, "🚀 V7双组版已启动，开始24小时播报...")
        elif text == "V7 杀组版":
            current_algo = "v7_kill"
            broadcast_running = True
            send_message(chat_id, "🚀 V7杀组版已启动，开始24小时播报...")
        elif text == "V7 杀b球版":
            current_algo = "v7_ball"
            broadcast_running = True
            send_message(chat_id, "🚀 V7杀b球版已启动，开始24小时播报...")
        elif text == "停止播报":
            broadcast_running = False
            send_message(chat_id, "⏹️ 播报已停止")
        else:
            send_message(chat_id, "请选择一个算法：", {
                "keyboard": [
                    [{"text": "V7 双组版"}, {"text": "V7 杀组版"}],
                    [{"text": "V7 杀b球版"}, {"text": "停止播报"}]
                ],
                "resize_keyboard": True
            })

def broadcast_loop():
    global broadcast_running, current_algo, consecutive_loss
    stats = {"hit": 0, "total": 0}
    history_lines = []
    pending_prediction = None
    last_issue = None
    best_params = {"大单": 12, "小单": 13, "大双": 14, "小双": 15}
    
    while True:
        if broadcast_running and current_algo:
            try:
                history = get_latest_data()
                if not history:
                    time.sleep(PREDICT_INTERVAL)
                    continue
                
                current = history[0]
                current_issue = current["issue"]
                
                if current_issue != last_issue:
                    if consecutive_loss >= MAX_CONSECUTIVE_LOSS:
                        for k in PARAM_RANGES:
                            mid = (PARAM_RANGES[k][0] + PARAM_RANGES[k][1]) / 2
                            PARAM_RANGES[k] = (max(10, mid - 2), min(17, mid + 2))
                    else:
                        PARAM_RANGES["大单"] = (10, 17)
                        PARAM_RANGES["小单"] = (10, 17)
                        PARAM_RANGES["大双"] = (11, 17)
                        PARAM_RANGES["小双"] = (11, 17)
                    
                    best_params, _ = adaptive_grid_search(history, current_algo)
                    
                    if pending_prediction is not None:
                        is_hit = False
                        if current_algo == "v7_double":
                            is_hit = current["category"] in pending_prediction
                        elif current_algo == "v7_kill":
                            is_hit = current["category"] != pending_prediction
                        elif current_algo == "v7_ball":
                            is_hit = current["b"] not in pending_prediction
                        
                        stats["total"] += 1
                        if is_hit:
                            stats["hit"] += 1
                            consecutive_loss = 0
                            history_lines[-1] += "🈵"
                        else:
                            consecutive_loss += 1
                            history_lines[-1] += "❌"
                        
                        if current_algo == "v7_ball":
                            history_lines[-1] += str(current['b'])
                        else:
                            history_lines[-1] += str(current['total']).zfill(2)
                    
                    if current_algo == "v7_double":
                        result = predict_v7_double(history, best_params)
                        if result:
                            pred, market_state, window_size = result
                            pending_prediction = pred
                            next_issue = str(int(current_issue) + 1)
                            short = next_issue[-2:] if len(next_issue) >= 2 else next_issue.zfill(2)
                            history_lines.append(f"{short}期.{pred[0]}{pred[1]}")
                    
                    elif current_algo == "v7_kill":
                        result = predict_v7_kill(history, best_params)
                        if result:
                            kill, market_state, window_size = result
                            pending_prediction = kill
                            next_issue = str(int(current_issue) + 1)
                            short = next_issue[-2:] if len(next_issue) >= 2 else next_issue.zfill(2)
                            history_lines.append(f"{short}期.杀{kill}")
                    
                    elif current_algo == "v7_ball":
                        result = predict_v7_ball(history, best_params)
                        if result:
                            balls, market_state, window_size = result
                            pending_prediction = balls
                            next_issue = str(int(current_issue) + 1)
                            short = next_issue[-2:] if len(next_issue) >= 2 else next_issue.zfill(2)
                            balls_str = "/".join(str(b) for b in balls)
                            history_lines.append(f"{short}期.杀b{balls_str}")
                    
                    if history_lines:
                        rate = stats["hit"] / stats["total"] if stats["total"] > 0 else 0
                        param_str = f"{best_params['大单']}/{best_params['小单']}/{best_params['大双']}/{best_params['小双']}"
                        algo_show = {"v7_double":"双组","v7_kill":"杀组","v7_ball":"杀b球"}.get(current_algo, "")
                        full_msg = f"願得一人心({algo_show} {param_str})\n" + "\n".join(history_lines[-15:]) + f"\n📊 {stats['hit']}中{stats['total']} 命中率{rate*100:.1f}%"
                        send_channel_message(full_msg)
                    
                    last_issue = current_issue
                
                time.sleep(PREDICT_INTERVAL)
            except Exception as e:
                print(f"错误: {e}")
                time.sleep(10)
        else:
            time.sleep(1)

# ==================== 主程序 ====================
get_bot_info()

broadcast_thread = threading.Thread(target=broadcast_loop, daemon=True)
broadcast_thread.start()

print(f"🤖 Bot 已启动，等待命令... (用户名: @{bot_username})")

while True:
    try:
        updates = get_updates()
        for update in updates:
            last_update_id = update["update_id"]
            if "message" in update:
                msg = update["message"]
                chat_id = msg["chat"]["id"]
                user_id = msg["from"]["id"]
                username = msg["from"].get("username", "")
                text = msg.get("text", "")
                handle_command(chat_id, text, user_id, username)
        time.sleep(2)
    except Exception as e:
        print(f"主循环错误: {e}")
        time.sleep(5)
