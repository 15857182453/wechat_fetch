#!/usr/bin/env python3
"""从分析体（fenxiti.com）API 拉取 Tab 11 用户行为分析数据"""
import json
import os
import requests

TOKEN = "fvoaF0c7BPS5va8Ijxd9T_jsiZU"
SPACE_ID = "aYMlRm4x"
BASE_URL = "https://api-portal.fenxiti.com/v1/api"

# 4 个事件分析图表
ANALYSES = [
    {"name": "monthly_4",  "chart_id": "GMJJWkMP", "desc": "4月核心指标"},
    {"name": "monthly_5",  "chart_id": "Dp2jw0pJ", "desc": "5月核心指标"},
    {"name": "rx_4",       "chart_id": "DpBqejMk", "desc": "4月药方数据"},
    {"name": "rx_5",       "chart_id": "Y4YEJj4m", "desc": "5月药方数据"},
]

OUTPUT_DIR = "/home/openclaw/.openclaw/workspace"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "language": "CH",
}

results = {}
for item in ANALYSES:
    url = f"{BASE_URL}/projects/{SPACE_ID}/analysis/olap_event/{item['chart_id']}/chartdata"
    params = {"forceRefresh": "true", "offset": 0, "limit": 50000}
    print(f"📡 获取 {item['desc']} ({item['chart_id']})...")
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        # API 返回的数据直接在顶层（不在 data 字段下）
        if data.get("code") == -1 or (data.get("code") is not None and data["code"] != 0):
            print(f"  ❌ API 返回错误: {data.get('msg', 'unknown')}")
            continue
        
        output = {
            "analysisInfo": data.get("analysisInfo", {}),
            "resultHeader": data.get("resultHeader", []),
            "resultRows": data.get("resultRows", []),
        }
        row_count = len(output["resultRows"])
        fname = f"data_fenxiti_{item['name']}.json"
        fpath = os.path.join(OUTPUT_DIR, fname)
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"  ✅ 获取成功，{row_count} 行 → {fname}")
        results[item['name']] = True
    except Exception as e:
        print(f"  ❌ 请求失败: {e}")
        results[item['name']] = False

print(f"\n{'='*50}")
ok = sum(1 for v in results.values() if v)
print(f"完成: {ok}/{len(ANALYSES)} 成功")
if ok == len(ANALYSES):
    print("✅ 全部成功，Dashboard Tab 11 已自动刷新（文件缓存 TTL 3600s）")
