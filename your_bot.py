import requests
import time
import math
import random
from datetime import datetime
from collections import Counter

# ==================== 全局公共配置 ====================
BOT_TOKEN = "8789627493:AAExE8z-tRhrbGvENYVt4dxqWUFf56rrZJQ"
# 清空频道，完全不推送
CHANNEL_IDS = []
API_KJ = "https://pc28.help/api/kj.json?nbr=100"
API_KENO = "https://pc28.help/api/keno.json?nbr=100"
API_YL = "https://pc28.help/api/yl.json"
API_MAP = {
    "keno": "https://pc28.help/api/keno.json?nbr=100",
    "kj": "https://pc28.help/api/kj.json?nbr=100",
    "yl": "https://pc28.help/api/yl.json"
}
CATEGORIES = ["大单", "小单", "大双", "小双"]
PREDICT_INTERVAL = 20

# ==================== 第一个算法 V8-HYBRID 原样完整 ====================
class HybridEngineV8:
    def __init__(self):
        self.last_issue = None
        self.weights = {"keno": 50.0, "yl": 3.0, "trend": 20.0}

    def fetch(self, url):
        try: return requests.get(url, timeout=5).json().get("data", [])
        except: return None

    def calculate(self, keno_list, yl_dict, custom_weights):
        scores = {cat: 100.0 for cat in CATEGORIES}
        try:
            nbrs = [int(n) for n in keno_list[0]["nbrs"].split(",")]
            p_val = sum([nbrs[i] for i in [1, 4, 7, 10, 13, 16]]) % 10
            raw_map = ["小双", "小单", "小双", "小单", "小双", "大单", "大双", "大单", "大双", "大单"]
            scores[raw_map[p_val]] += custom_weights["keno"]
        except: pass

        if isinstance(yl_dict, dict):
            for cat in CATEGORIES:
                scores[cat] += float(yl_dict.get(cat, 0)) * custom_weights["yl"]

        sorted_res = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [sorted_res[0][0], sorted_res[1][0]], (sorted_res[0][1]/sum(scores.values()))

    def self_optimize(self, keno, kj, yl):
        best_w = self.weights.copy()
        max_hits = -1
        for k_w in [30, 55, 80]:
            for y_w in [1.5, 3.5, 5.5]:
                test_w = {"keno": k_w, "yl": y_w}
                hits = 0
                for i in range(1, 11):
                    p, _ = self.calculate(keno[i:], yl, test_w)
                    if kj[i-1]["combination"] in p: hits += 1
                if hits > max_hits:
                    max_hits = hits
                    best_w = test_w
        return best_w, max_hits

    def run_once(self):
        keno = self.fetch(API_MAP["keno"])
        kj = self.fetch(API_MAP["kj"])
        yl = requests.get(API_YL).json().get("data", {})

        if not keno or not kj:
            return None, None
        curr_issue = str(keno[0].get("nbr"))
        best_weights, recent_hits = self.self_optimize(keno, kj, yl)
        dual_pred, conf = self.calculate(keno, yl, best_weights)

        msg = (
            f"⚡ 逻辑跳跃引擎 (V8-HYBRID)\n"
            f"━━━━━━━━━━━━━━\n"
            f"📡 开奖:{curr_issue}期 → {kj[0]['combination']}\n"
            f"🎯 预测:{int(curr_issue)+1}期\n\n"
            f"🔥 核心推荐:{dual_pred[0]} + {dual_pred[1]}\n"
            f"🚦 信心评级:{'⭐' * (recent_hits // 2 if recent_hits > 4 else 2)}\n"
            f"━━━━━━━━━━━━━━\n"
            f"📈 动态回测胜率:{recent_hits * 10}%\n"
            f"🛠️ 模式:{'偏向物理' if best_weights['keno'] > 60 else '偏向遗漏'}"
        )
        return curr_issue, msg

# ==================== 第二个算法 4D双组权重优化 原样完整 ====================
def get_category(total):
    size = "大" if total >= 14 else "小"
    oe = "单" if total % 2 == 1 else "双"
    return size + oe

def get_latest_data():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(API_KJ, headers=headers, timeout=15)
        res_json = resp.json()
        items = res_json.get("data", [])
        if not items:
            return [], []
        history = []
        all_codes = []
        for item in items:
            issue = str(item.get("nbr", ""))
            raw_num = item.get("number", "")
            combo = item.get("combination", "")
            if not issue or not raw_num:
                continue
            try:
                nums = [int(n) for n in raw_num.split('+')]
                total = int(item.get("num", sum(nums)))
                all_codes.extend(nums)
                if not combo:
                    combo = get_category(total)
                history.append({
                    "issue": issue,
                    "total": total,
                    "category": combo,
                    "codes": nums
                })
            except:
                continue
        return history, all_codes
    except Exception as e:
        print(f"❌ 数据获取失败: {e}")
        return [], []

def predict_with_params(history, params):
    if len(history) < 5: return None
    latest = history[0]
    last4 = history[1:5]
    phi = (1 + 5**0.5) / 2
    fixed_sum = sum(params.get(h["category"], 13) for h in last4)
    raw = (fixed_sum * phi) / (latest["total"] * math.pi if latest["total"] > 0 else 1.5)
    decimal_part = abs(raw - int(raw))
    s = "{:.10f}".format(decimal_part).split('.')[1]
    t1, t2 = int(s[0]), int(s[1])
    cat_map = {0:"小双", 1:"小单", 2:"小双", 3:"小单", 4:"小双", 5:"大单", 6:"大双", 7:"大单", 8:"大双", 9:"大单"}
    opp = {"大单":"小单", "大双":"小双", "小单":"大单", "小双":"大双"}
    c1 = cat_map[t1]
    c2 = cat_map[t2]
    if c1 == c2: c2 = opp[c1]
    return [c1, c2]

def find_best_params(history):
    ranges = {"大单":range(10,18),"小单":range(10,18),"大双":range(11,19),"小双":range(11,19)}
    best_p = {"大单":12,"小单":13,"大双":14,"小双":15}
    best_score = -1
    for _ in range(60):
        ps = {k: random.choice(v) for k, v in ranges.items()}
        current_score = 0
        for i in range(min(len(history)-5, 12)):
            test_history = history[i+1:i+7]
            actual = history[i]["category"]
            pred = predict_with_params(test_history, ps)
            if pred and actual in pred:
                current_score += (1 / (i + 1))
        if current_score > best_score:
            best_score = current_score
            best_p = ps
    return best_p

# ==================== 第三个算法 V23-ARMOR 形态装甲 原样完整 ====================
class ArmorSlayer:
    def __init__(self):
        self.last_issue = None

    def calculate_form_v23(self, history):
        recent_10 = [i["combination"] for i in history[:10]]
        recent_40 = [i["combination"] for i in history[:40]]
        counts_40 = Counter(recent_40)
        curr_form = recent_10[0]
        prev_form = recent_10[1]
        forms = ["大单", "小单", "大双", "小双"]

        if curr_form == prev_form:
            opposites = {"大单":"小双", "小双":"大单", "大双":"小单", "小单":"大双"}
            slay_target = opposites[curr_form]
        elif len(set(recent_10[:5])) >= 3:
            slay_target = sorted(forms, key=lambda x: abs(counts_40[x] - 10))[0]
        else:
            omissions = {}
            for f in forms:
                try: omissions[f] = recent_40.index(f)
                except: omissions[f] = 40
            slay_target = sorted(omissions, key=omissions.get, reverse=True)[0]
        return slay_target

    def get_reason(self, data):
        return self.calculate_form_v23(data)

    def run_once(self):
        try:
            resp = requests.get(API_KJ, timeout=8).json()
            data = resp.get("data", [])
            if not data:
                return None, None
            curr_issue = str(data[0]["nbr"])
            slay_result = self.calculate_form_v23(data)
            hits = 0
            for k in range(1, 16):
                if data[k-1]["combination"] != self.calculate_form_v23(data[k:]):
                    hits += 1
            rate = (hits / 15) * 100

            msg = (
                f"🛡️ 形态级反向杀组 (V23-ARMOR)\n"
                f"━━━━━━━━━━━━━━\n"
                f"📡 上期:{curr_issue}期 → {data[0]['combination']}\n\n"
                f"🚫 下期必杀:【 {slay_result} 】\n"
                f"━━━━━━━━━━━━━━\n"
                f"📈 形态排除成功率:{rate:.1f}%"
            )
            return curr_issue, msg
        except Exception as e:
            print(e)
            return None, None

# ==================== 第四个算法 5y属性共振 原样完整 ====================
five_y_table = {
    "5y0": [20, 15, 25, 5, 10],
    "5y1": [1, 11, 21, 6, 16, 26],
    "5y2": [2, 12, 22, 7, 17, 27],
    "5y3": [13, 23, 3, 8, 18],
    "5y4": [14, 24, 4, 19, 9]
}

def get_comb(n):
    is_big = n >= 14
    is_odd = n % 2 != 0
    return ("大" if is_big else "小") + ("单" if is_odd else "双")

FIVE_Y_PROPERTIES = {k: Counter([get_comb(n) for n in nums]) for k, nums in five_y_table.items()}

class Resonance5yEngine:
    def __init__(self):
        self.last_issue = None

    def predict_logic(self, history):
        y_list = [int(sum(int(x) for x in i["number"].split("+")) % 5) for i in history[:15]]
        diffs = [y_list[i] - y_list[i+1] for i in range(len(y_list)-1)]
        avg_diff = sum(diffs[:3]) / 3
        pred_y_idx = int(round(y_list[0] + avg_diff)) % 5
        pred_y_key = f"5y{pred_y_idx}"
        recent_global_combs = Counter([i["combination"] for i in history[:20]])
        group_combs = FIVE_Y_PROPERTIES[pred_y_key]
        resonance_scores = {}
        for comb in ["大单", "小单", "大双", "小双"]:
            resonance_scores[comb] = group_combs[comb] * (recent_global_combs[comb] + 2)
        top_two = sorted(resonance_scores.items(), key=lambda x: x[1], reverse=True)[:2]
        return pred_y_key, [top_two[0][0], top_two[1][0]]

    def run_once(self):
        try:
            resp = requests.get(API_KJ, timeout=8).json()
            data = resp.get("data", [])
            if not data:
                return None, None
            curr_issue = str(data[0]["nbr"])
            pred_5y, pred_dual = self.predict_logic(data)
            hits = 0
            for j in range(1, 11):
                _, d = self.predict_logic(data[j:])
                if data[j-1]["combination"] in d: hits += 1

            msg = (
                f"🌀 5y属性共振推演 (V18.1-FIX)\n"
                f"━━━━━━━━━━━━━━\n"
                f"📡 开奖:{curr_issue}期 → {data[0]['combination']}\n"
                f"🎯 下期预测:{int(curr_issue)+1}期\n\n"
                f"🧭 5y坐标:{pred_5y}\n"
                f"🔥 核心推荐:{pred_dual[0]} + {pred_dual[1]}\n"
                f"━━━━━━━━━━━━━━\n"
                f"📈 近10期共振胜率:{hits * 10}%"
            )
            return curr_issue, msg
        except Exception as e:
            print(f"运行异常: {e}")
            return None, None

# ==================== 主程序：只打印本地控制台、不推送任何频道 ====================
def main():
    print("🚀 四算法合一 本地运行（已关闭所有频道推送）")
    v8_engine = HybridEngineV8()
    armor_engine = ArmorSlayer()
    fivey_engine = Resonance5yEngine()

    last_issue_all = None
    stats = {"hit": 0, "total": 0}
    pending_prediction = None

    while True:
        # V8 控制台打印
        curr_v8, msg_v8 = v8_engine.run_once()
        if curr_v8 and curr_v8 != last_issue_all:
            print("\n" + msg_v8)

        # 形态装甲 控制台打印
        curr_armor, msg_armor = armor_engine.run_once()
        if curr_armor and curr_armor != last_issue_all:
            print("\n" + msg_armor)

        # 5y共振 控制台打印
        curr_fivey, msg_fivey = fivey_engine.run_once()
        if curr_fivey and curr_fivey != last_issue_all:
            print("\n" + msg_fivey)

        # 4D双组 控制台打印
        history, _ = get_latest_data()
        if history:
            current_issue = history[0]["issue"]
            if current_issue != last_issue_all:
                print(f"\n🔔 4D算法 期号更新: {current_issue}")
                if pending_prediction and pending_prediction["issue"] == current_issue:
                    actual_cat = history[0]["category"]
                    is_hit = actual_cat in pending_prediction["pred"]
                    stats["total"] += 1
                    if is_hit: stats["hit"] += 1

                best_p = find_best_params(history)
                pred = predict_with_params(history, best_p)
                if pred:
                    next_issue = str(int(current_issue) + 1)
                    show_pred = f"{pred[0]}+{pred[1]}"
                    pending_prediction = {"issue": next_issue, "pred": pred, "show_pred": show_pred}
                    rate = (stats["hit"] / stats["total"] * 100) if stats["total"] > 0 else 0
                    now_str = datetime.now().strftime('%H:%M:%S')
                    msg_4d = (
                        f"🔮 双组优选预测 第 {current_issue} 期\n"
                        f"———————————————\n"
                        f"🎯 下期建议: {show_pred}\n"
                        f"📈 历史胜率: {rate:.1f}% ({stats['hit']}/{stats['total']})\n"
                        f"⏰ 预测时间: {now_str}"
                    )
                    print(msg_4d)
                last_issue_all = current_issue

        time.sleep(25)

if __name__ == "__main__":
    main()
