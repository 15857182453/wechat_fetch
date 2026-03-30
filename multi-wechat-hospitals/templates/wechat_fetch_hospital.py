#!/usr/bin/env python3
"""
单医院微信公众号文章数据抓取 + GrowingIO 自动上报
通过 --config 参数传入医院配置

使用方法:
    python3 wechat_fetch_hospital.py --config '{"name":"医院1",...}'
    python3 wechat_fetch_hospital.py --config config.json
    python3 wechat_fetch_hospital.py --config '{"name":"医院1",...}" --days 7
    python3 wechat_fetch_hospital.py --config '{"name":"医院1",...}" --start 2026-03-01 --end 2026-03-30
"""

import requests
import json
import datetime
import csv
import argparse
import os
import sys
import hashlib

# 添加 media-crawler 目录到 path 以导入 client 模块
MEDIA_CRAWLER_DIR = "/home/openclaw/.openclaw/workspace/media-crawler"
if MEDIA_CRAWLER_DIR not in sys.path:
    sys.path.insert(0, MEDIA_CRAWLER_DIR)

try:
    from client import Client, Request
except ImportError:
    print("⚠️ 无法导入 client 模块")
    Client = None
    Request = None
from collections import defaultdict

try:
    from growingio_tracker import DefaultConsumer, GrowingTracker
except ImportError:
    print("⚠️ growingio_tracker 未安装")
    GrowingTracker = None

# ============ 配置加载 ============
def load_config_from_args():
    """从命令行参数加载配置"""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--config", required=True, help="医院配置JSON字符串或文件路径")
    
    # 先解析 --config
    try:
        args, _ = parser.parse_known_args()
        
        # 判断是 JSON 字符串还是文件路径
        if args.config.startswith('{'):
            config = json.loads(args.config)
        else:
            with open(args.config, 'r', encoding='utf-8') as f:
                config = json.load(f)
        
        return config
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        sys.exit(1)

# 加载配置
HOSPITAL_CONFIG = load_config_from_args()

# 提取配置参数
HOSPITAL_ORG_ID = HOSPITAL_CONFIG['org_id']
OFFICIAL_ACCOUNT_NAME = HOSPITAL_CONFIG['account_name']
OFFICIAL_ACCOUNT_TYPE = HOSPITAL_CONFIG['account_type']
APPID = HOSPITAL_CONFIG['appid']

# 动态路径配置
OUTPUT_DIR = HOSPITAL_CONFIG.get('output_dir', 'logs')
LOGS_DIR = os.path.join(OUTPUT_DIR, 'logs')
REPORT_STATE_FILE = os.path.join(LOGS_DIR, 'wechat_report_state.json')

# API配置
OPENAPI_CONFIG = HOSPITAL_CONFIG['openapi']
GROWINGIO_CONFIG = HOSPITAL_CONFIG['growingio']

# 钉钉通知配置
DINGTALK_CONFIG = HOSPITAL_CONFIG.get('dingtalk', {'enabled': False})
DINGTALK_ENABLED = DINGTALK_CONFIG.get('enabled', False)
DINGTALK_URL = DINGTALK_CONFIG.get('webhook_url', '')

# ============ 工具函数 ============

def ensure_logs_dir():
    """确保日志目录存在"""
    os.makedirs(LOGS_DIR, exist_ok=True)

def load_report_state():
    """加载已上报的记录状态"""
    ensure_logs_dir()
    
    try:
        with open(REPORT_STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"reported": []}
    except json.JSONDecodeError:
        print(f"⚠️ {REPORT_STATE_FILE} 格式错误，重置为空")
        return {"reported": []}

def save_report_state(state):
    """保存已上报的记录状态"""
    ensure_logs_dir()
    
    with open(REPORT_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def generate_report_key(org_id, msgid_full, stat_date):
    """生成上报记录的唯一键名（包含orgId来区分不同医院）"""
    return f"{org_id}_{msgid_full}_{stat_date}"

def filter_new_events(events):
    """过滤掉已上报过的记录，只返回新数据"""
    state = load_report_state()
    reported_set = set(state.get("reported", []))
    
    new_events = []
    duplicates = 0
    duplicate_details = []
    
    for event in events:
        org_id = event.get("orgId", "")
        msgid_full = event.get("oa_articleId", "")
        stat_date = event.get("_stat_date", "")
        key = generate_report_key(org_id, msgid_full, stat_date)
        
        if key not in reported_set:
            new_events.append(event)
        else:
            duplicates += 1
            duplicate_details.append((org_id, msgid_full, stat_date))
    
    if duplicates > 0:
        print(f"📊 已过滤 {duplicates} 条重复数据")
        if len(duplicate_details) <= 20:
            print("   重复数据详情：")
            for org, msgid, date in duplicate_details:
                print(f"   - [{org}] {msgid} on {date}")
        else:
            print(f"   （共 {len(duplicate_details)} 条，超过20条，仅显示前20条）")
            print("   重复数据详情（前20条）：")
            for org, msgid, date in duplicate_details[:20]:
                print(f"   - [{org}] {msgid} on {date}")
    
    return new_events, reported_set

def get_access_token():
    """通过 OpenAPI 获取微信 access_token"""
    global Client, Request
    
    if Client is None:
        try:
            from client import Client as ClientClass, Request as RequestClass
            Client = ClientClass
            Request = RequestClass
        except ImportError:
            print("❌ 无法导入 client 模块")
            return None
    
    try:
        client = Client(
            api_url=OPENAPI_CONFIG["api_url"],
            app_key=OPENAPI_CONFIG["app_key"],
            app_secret=OPENAPI_CONFIG["app_secret"],
            encoding_aes_key=""
        )

        request = Request()
        request.service_id = "openapi.wxAccessTokenService"
        request.method = "getWxTokenByWxAppId"
        request.bodys = [OPENAPI_CONFIG["app_key"], OPENAPI_CONFIG["wx_app_id"]]
        request.add_header("X-Service-Id", request.service_id)
        request.add_header("X-Service-Method", request.method)

        response = client.execute(request)
        if response.is_success():
            token_data = response.json_response.get("body", {})
            if isinstance(token_data, dict):
                return next(iter(token_data.values()), None)
            elif isinstance(token_data, list):
                return token_data[0] if token_data else None
            return token_data
        else:
            print(f"❌ 获取 Token 失败：{response.get_error_message()}")
            return None
    except Exception as e:
        print(f"❌ 获取 Token 异常：{e}")
        return None

def fetch_article_data(access_token, date):
    """调用微信 API 获取指定日期的文章数据"""
    url = f"https://api.weixin.qq.com/datacube/getarticletotaldetail?access_token={access_token}"
    payload = {"begin_date": date, "end_date": date}
    headers = {"Content-Type": "application/json"}

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        result = resp.json()

        if result.get("errcode") == 40001:
            print(f"❌ {date} token 失效")
            return None
        elif "list" in result:
            return result["list"]
        else:
            print(f"⚠️ {date} 返回异常：{result}")
            return None
    except Exception as e:
        print(f"❌ {date} 请求异常：{e}")
        return None

def process_article(article, date):
    """处理单篇文章，生成 GrowingIO 所需的事件属性"""
    msgid_full = article.get("msgid", "")
    msgid_parts = msgid_full.split("_")
    index = msgid_parts[1] if len(msgid_parts) > 1 else "1"
    title = article.get("title", "")
    content_url = article.get("content_url", "")
    ref_date = article.get("ref_date", date)

    events = []
    cumulative_read = 0
    cumulative_share = 0

    for detail in article.get("detail_list", []):
        stat_date = detail.get("stat_date")
        daily_read = int(detail.get("read_user", 0) or 0)
        daily_share = int(detail.get("share_user", 0) or 0)
        cumulative_read += daily_read
        cumulative_share += daily_share

        # 计算阅读跳出率
        daily_jump_rate = 0.0
        for jump in detail.get("read_jump_position", []):
            if jump.get("position") == 1:
                daily_jump_rate = jump.get("rate", 0.0)
                break

        # 阅读来源字符串
        source_str = ",".join([
            f"{src['scene_desc']}:{src['user_count']}"
            for src in detail.get("read_user_source", [])
            if src['scene_desc'] != "全部"
        ])

        # 构建事件属性
        attributes = {
            "orgId": HOSPITAL_ORG_ID,
            "wechatAppid": APPID,
            "oa_nikeName": OFFICIAL_ACCOUNT_NAME,
            "oa_type": OFFICIAL_ACCOUNT_TYPE,
            "oa_articleId": msgid_full,
            "articleTitle": title,
            "oa_content": "",
            "oa_contentUrl": content_url,
            "oa_articleDate": ref_date,
            "oa_articlePosition": index,
            "oa_targetUser": "0",
            "oa_readUserSource": source_str,
            "oa_readUser": cumulative_read,
            "oa_oriPageReadUser_var": 0,
            "oa_shareUser": cumulative_share,
            "oa_likeUser": detail.get("like_user", 0),
            "oa_collectionUser": detail.get("collection_user", 0),
            "oa_commentCount": detail.get("comment_count", 0),
            "oa_readSubscribeUser": detail.get("read_subscribe_user", 0),
            "oa_readDeliveryRate": detail.get("read_delivery_rate", 0.0),
            "oa_readFinishRate": detail.get("read_finish_rate", 0.0),
            "oa_avg_activetime": detail.get("read_avg_activetime", 0.0),
            "oa_readJumpPosition": str(daily_jump_rate),
            "oa_stat_date": stat_date,
            "oa_readUser_di": daily_read,
            "oa_shareUser_di": daily_share,
            "_stat_date": stat_date,
        }
        events.append(attributes)

    return events

def save_to_csv(all_events, filename):
    """保存汇总数据到 CSV"""
    if not all_events:
        return

    fieldnames = [
        "医院组织 id", "公众号名称", "公众号类型", "公众号 appid", "文章 id", "文章标题",
        "文章内容", "文章 url", "文章发布日期", "oa_文章位置", "oa_推送人数",
        "oa_阅读来源", "oa_阅读人数", "oa_原文页阅读人数", "oa_分享人数",
        "oa_拇指赞人数", "oa_收藏人数", "oa_留言条数", "oa_阅读后关注人数",
        "oa_阅读送达率", "oa_阅读完成率", "oa_平均阅读时长（分钟）", "oa_阅读跳出率",
        "oa_统计日期", "oa_每日阅读人数", "oa_每日分享人数"
    ]

    def event_to_csv_row(event):
        return {
            "医院组织 id": event.get("orgId", ""),
            "公众号名称": event.get("oa_nikeName", ""),
            "公众号类型": event.get("oa_type", ""),
            "公众号 appid": event.get("wechatAppid", ""),
            "文章 id": event.get("oa_articleId", ""),
            "文章标题": event.get("articleTitle", ""),
            "文章内容": event.get("oa_content", ""),
            "文章 url": event.get("oa_contentUrl", ""),
            "文章发布日期": event.get("oa_articleDate", ""),
            "oa_文章位置": event.get("oa_articlePosition", ""),
            "oa_推送人数": event.get("oa_readUser", ""),
            "oa_阅读来源": event.get("oa_readUserSource", ""),
            "oa_阅读人数": event.get("oa_readUser", ""),
            "oa_原文页阅读人数": event.get("oa_oriPageReadUser_var", ""),
            "oa_分享人数": event.get("oa_shareUser", ""),
            "oa_拇指赞人数": event.get("oa_likeUser", ""),
            "oa_收藏人数": event.get("oa_collectionUser", ""),
            "oa_留言条数": event.get("oa_commentCount", ""),
            "oa_阅读后关注人数": event.get("oa_readSubscribeUser", ""),
            "oa_阅读送达率": event.get("oa_readDeliveryRate", ""),
            "oa_阅读完成率": event.get("oa_readFinishRate", ""),
            "oa_平均阅读时长（分钟）": event.get("oa_avg_activetime", ""),
            "oa_阅读跳出率": event.get("oa_readJumpPosition", ""),
            "oa_统计日期": event.get("oa_stat_date", ""),
            "oa_每日阅读人数": event.get("oa_readUser_di", 0),
            "oa_每日分享人数": event.get("oa_shareUser_di", 0),
        }

    csv_rows = [event_to_csv_row(event) for event in all_events]

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    print(f"📄 汇总数据已保存至 {filename}，共 {len(csv_rows)} 条记录")

def save_to_json(events, filename):
    """保存上报数据到 JSON"""
    # 移除内部字段
    clean_events = []
    for event in events:
        clean = {k: v for k, v in event.items() if not k.startswith("_")}
        clean_events.append({
            "attributes": clean
        })

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(clean_events, f, ensure_ascii=False, indent=2)

    print(f"📄 上报数据已保存至 {filename}，共 {len(clean_events)} 条记录")

# ============ GrowingIO 上报 ============

def upload_to_growio(events, debug=False, dry_run=False):
    """上报事件到 GrowingIO"""
    if GrowingTracker is None:
        print("⚠️ growingio_tracker 未安装，跳过上报")
        print("   安装命令：pip install growingio-tracker")
        return 0, len(events)
    
    try:
        consumer = DefaultConsumer(
            GROWINGIO_CONFIG["product_id"],
            GROWINGIO_CONFIG["data_source_id"],
            GROWINGIO_CONFIG["server_host"]
        )
        tracker = GrowingTracker.consumer(consumer)

        success_count = 0
        fail_count = 0

        for i, event_attrs in enumerate(events, 1):
            clean_attrs = {k: v for k, v in event_attrs.items() if not k.startswith("_")}

            print(f"[{i}/{len(events)}] ", end="")
            try:
                tracker.track_custom_event(
                    GROWINGIO_CONFIG["event_name"],
                    attributes=clean_attrs,
                    anonymous_id='python',
                    login_user_id='12345'
                )
                success_count += 1
                print("✅")
            except Exception as e:
                fail_count += 1
                print(f"❌ {e}")

        if hasattr(tracker, 'close'):
            tracker.close()
        return success_count, fail_count

    except Exception as e:
        print(f"❌ GrowingIO 上报异常：{e}")
        return 0, len(events)

# ============ 主流程 ============

def main():
    # 解析 --config 参数
    config_param = None
    remaining_args = []
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == '--config' and i + 1 < len(sys.argv):
            config_param = sys.argv[i + 1]
            i += 2
        else:
            remaining_args.append(sys.argv[i])
            i += 1
    
    # 加载配置
    if config_param:
        if config_param.startswith('{'):
            config = json.loads(config_param)
        else:
            with open(config_param, 'r', encoding='utf-8') as f:
                config = json.load(f)
        
        # 提取配置参数
        global HOSPITAL_ORG_ID, OFFICIAL_ACCOUNT_NAME, OFFICIAL_ACCOUNT_TYPE, APPID
        global OPENAPI_CONFIG, GROWINGIO_CONFIG, OUTPUT_DIR, LOGS_DIR, REPORT_STATE_FILE
        global DINGTALK_CONFIG, DINGTALK_ENABLED, DINGTALK_URL
        
        HOSPITAL_ORG_ID = config['org_id']
        OFFICIAL_ACCOUNT_NAME = config['account_name']
        OFFICIAL_ACCOUNT_TYPE = config['account_type']
        APPID = config['appid']
        OPENAPI_CONFIG = config['openapi']
        GROWINGIO_CONFIG = config['growingio']
        
        OUTPUT_DIR = config.get('output_dir', 'logs')
        LOGS_DIR = os.path.join(OUTPUT_DIR, 'logs')
        REPORT_STATE_FILE = os.path.join(LOGS_DIR, 'wechat_report_state.json')
        
        DINGTALK_CONFIG = config.get('dingtalk', {'enabled': False})
        DINGTALK_ENABLED = DINGTALK_CONFIG.get('enabled', False)
        DINGTALK_URL = DINGTALK_CONFIG.get('webhook_url', '')

    parser = argparse.ArgumentParser(description="单医院微信文章数据抓取 + GrowingIO 上报")
    parser.add_argument("--start", type=str, help="开始日期 (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, help="结束日期 (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, help="最近 N 天")
    parser.add_argument("--today", action="store_true", help="仅今天")
    parser.add_argument("--dry-run", action="store_true", help="仅抓取不上报")
    parser.add_argument("--debug", action="store_true", help="调试模式")
    parser.add_argument("--output", type=str, default=".", help="输出目录")

    args = parser.parse_args(remaining_args)

    # 计算日期范围
    today = datetime.date.today()

    if args.today:
        start_date = today
        end_date = today
    elif args.days:
        end_date = today
        start_date = today - datetime.timedelta(days=args.days - 1)
    elif args.start:
        start_date = datetime.datetime.strptime(args.start, "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(args.end, "%Y-%m-%d").date() if args.end else start_date
    else:
        # 默认最近 7 天
        end_date = today
        start_date = today - datetime.timedelta(days=6)

    print(f"🏥 医院: {OFFICIAL_ACCOUNT_NAME}")
    print(f"📅 日期范围：{start_date} 至 {end_date}")
    
    # 确保日志目录存在
    ensure_logs_dir()

    # 获取 access_token
    print("\n🔑 获取 access_token...")
    access_token = get_access_token()
    if not access_token:
        print("❌ 无法获取 access_token，程序退出")
        send_dingtalk_notice(start_date, end_date, 0, 0, 0, -1, "获取 token 失败")
        return

    print(f"✅ Token 获取成功：{access_token[:20]}...")
    
    # 抓取数据
    print("\n📥 开始抓取文章数据...")
    all_events = []

    current = start_date
    while current <= end_date:
        date_str = current.strftime("%Y-%m-%d")
        print(f"\n[{date_str}]")

        articles = fetch_article_data(access_token, date_str)
        if articles:
            for article in articles:
                events = process_article(article, date_str)
                all_events.extend(events)
                print(f"   📄 文章: {article.get('title', '')[:30]}... - {len(events)} 条统计记录")
        else:
            print("   无数据")

        current += datetime.timedelta(days=1)

    print(f"\n📊 抓取完成，共 {len(all_events)} 条记录")

    if not all_events:
        print("没有获取到任何数据")
        send_dingtalk_notice(start_date, end_date, 0, 0, 0, 0, "无数据")
        return
    
    # 去重处理
    print("\n🔍 去重检查...")
    new_events, reported_set = filter_new_events(all_events)
    duplicate_count = len(all_events) - len(new_events)
    
    if len(new_events) == 0:
        print("所有数据均已上报过，无需重复上报")
        send_dingtalk_notice(start_date, end_date, 0, 0, 0, duplicate_count, "无新数据")
        return
    
    print(f"📊 新数据 {len(new_events)} 条")

    # 保存文件
    today_str = today.strftime("%Y%m%d")
    date_range_str = f"{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
    
    # 使用医院名称生成唯一文件名前缀
    hospital_name_clean = OFFICIAL_ACCOUNT_NAME.replace("医院", "").replace(" ", "")
    json_filename = os.path.join(LOGS_DIR, f"{hospital_name_clean}_daily_report_{today_str}_{date_range_str}.json")
    csv_filename = os.path.join(LOGS_DIR, f"{hospital_name_clean}_wechat_article_stats_{today_str}_{date_range_str}.csv")
    
    print(f"\n💾 保存数据到 {json_filename}...")
    save_to_json(new_events, json_filename)
    save_to_csv(new_events, csv_filename)

    # 上报到 GrowingIO
    if not args.dry_run:
        print("\n📤 上报到 GrowingIO...")
        success, fail = upload_to_growio(new_events, debug=args.debug, dry_run=args.dry_run)
        print(f"\n✅ 上报完成：成功 {success} 条，失败 {fail} 条")
        
        # 更新已上报记录状态
        if success > 0:
            state = load_report_state()
            reported_set = set(state.get("reported", []))
            for event in new_events:
                org_id = event.get("orgId", "")
                msgid_full = event.get("oa_articleId", "")
                stat_date = event.get("_stat_date", "")
                key = generate_report_key(org_id, msgid_full, stat_date)
                if key not in reported_set:
                    reported_set.add(key)
            state["reported"] = list(reported_set)
            save_report_state(state)
            print(f"💾 已更新上报记录，当前共 {len(reported_set)} 条记录")
        
        # 钉钉通知
        send_dingtalk_notice(start_date, end_date, len(new_events), success, fail, duplicate_count, "成功")
    else:
        print("\n⏭️  跳过上报（dry-run 模式）")
        send_dingtalk_notice(start_date, end_date, len(new_events), 0, 0, duplicate_count, "dry-run")

def send_dingtalk_notice(start_date, end_date, new_count, success_count, fail_count, duplicate_count, status):
    """通过钉钉机器人发送任务完成通知"""
    if not DINGTALK_ENABLED or not DINGTALK_URL:
        return
    
    today = datetime.date.today()
    date_range = f"{start_date.strftime('%m/%d')} - {end_date.strftime('%m/%d')}"
    
    if duplicate_count > 0:
        markdown_content = f"""# 📊 {OFFICIAL_ACCOUNT_NAME} 数据抓取完成
    
## 🏥 医院名称
**{OFFICIAL_ACCOUNT_NAME}**

## 📢 微信数据
**📅 抓取日期范围：** {date_range}
**📊 抓取总数：** {new_count + duplicate_count}
**📝 新增数据条数：** {new_count}
**📉 重复数据条数：** {duplicate_count}
**✅ 上报成功：** {success_count}
**❌ 上报失败：** {fail_count}
**⏱️ 执行时间：** {today.strftime('%Y年%m月%d日')} """
    else:
        markdown_content = f"""# 📊 {OFFICIAL_ACCOUNT_NAME} 数据抓取完成
    
## 🏥 医院名称
**{OFFICIAL_ACCOUNT_NAME}**

## 📢 微信数据
**📅 抓取日期范围：** {date_range}
**📝 新增数据条数：** {new_count}
**✅ 上报成功：** {success_count}
**❌ 上报失败：** {fail_count}
**⏱️ 执行时间：** {today.strftime('%Y年%m月%d日')} """

    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": f"📊 {OFFICIAL_ACCOUNT_NAME} 数据抓取完成",
            "text": markdown_content
        }
    }
    
    try:
        import urllib.request
        req = urllib.request.Request(
            DINGTALK_URL,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            result = response.read().decode('utf-8')
            print(f"🔔 钉钉通知发送成功: {result}")
    except Exception as e:
        print(f"⚠️ 钉钉通知发送失败: {e}")

if __name__ == "__main__":
    main()
