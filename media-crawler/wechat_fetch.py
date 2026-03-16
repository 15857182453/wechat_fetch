#!/usr/bin/env python3
"""
微信公众号文章数据抓取 + GrowingIO 自动上报
整合了数据抓取和上报流程，实现全自动化

用法:
python3 wechat_fetch.py --start 2026-02-14 --end 2026-02-14 # 指定日期范围
python3 wechat_fetch.py --days 7 # 最近 7 天
python3 wechat_fetch.py --today # 仅今天
"""

import requests
import json
import datetime
import csv
import argparse
from collections import defaultdict
from client import Client, Request

# ============ 配置区域 ============
# 微信公众号配置
HOSPITAL_ORG_ID = "1005657"
OFFICIAL_ACCOUNT_NAME = "杭州师范大学附属医院"
OFFICIAL_ACCOUNT_TYPE = "订阅号"
APPID = "wxb946acbb0c6d9de6"

# OpenAPI 配置
OPENAPI_CONFIG = {
    "api_url": "https://openapi.ngarihealth.com/openapi/gateway",
    "app_key": "ngari5e93bcd7347bcc28",
    "app_secret": "347bcc28d2e9d26b",
    "wx_app_id": "wx530c8ee57cd2fa6e",  # 目标公众号 AppID
}

# GrowingIO 配置
GROWINGIO_CONFIG = {
    "product_id": "98b451a0ec02c41a",
    "data_source_id": "b7f6d83f9c9734b6",
    "server_host": "https://ngari-collect.fenxiti.com/",
    "event_name": "OA_officialNewsDailyData2",
}

# 去重记录文件路径
REPORT_STATE_FILE = "wechat_report_state.json"

# ============ 工具函数 ============

def load_report_state():
    """加载已上报的记录状态"""
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
    with open(REPORT_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def generate_report_key(msgid_full, stat_date):
    """生成上报记录的唯一键名"""
    return f"{msgid_full}_{stat_date}"


def filter_new_events(events):
    """过滤掉已上报过的记录，只返回新数据"""
    state = load_report_state()
    reported_set = set(state.get("reported", []))
    
    new_events = []
    duplicates = 0
    duplicate_details = []
    
    for event in events:
        msgid_full = event.get("oa_articleId", "")
        stat_date = event.get("_stat_date", "")
        key = generate_report_key(msgid_full, stat_date)
        
        if key not in reported_set:
            new_events.append(event)
        else:
            duplicates += 1
            duplicate_details.append((msgid_full, stat_date))
    
    if duplicates > 0:
        print(f"📊 已过滤 {duplicates} 条重复数据")
        # 显示重复数据的详细信息
        if len(duplicate_details) <= 20:
            print("   重复数据详情：")
            for msgid, date in duplicate_details:
                print(f"   - {msgid} on {date}")
        else:
            print(f"   （共 {len(duplicate_details)} 条，超过20条，仅显示前20条）")
            print("   重复数据详情（前20条）：")
            for msgid, date in duplicate_details[:20]:
                print(f"   - {msgid} on {date}")
    
    return new_events, reported_set

def get_access_token():
    """通过 OpenAPI 获取微信 access_token"""
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

    try:
        response = client.execute(request)
        if response.is_success():
            token_data = response.json_response.get("body", {})
            # token_data 可能是字典或列表，取第一个值
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
    cumulative_read = 0  # 新增累计变量
    cumulative_share = 0  # 如有需要也可累计分享

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

        # 事件时间戳（毫秒）
        dt = datetime.datetime.strptime(stat_date, "%Y-%m-%d")
        event_time = int(dt.timestamp() * 1000)

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
            # 额外字段（用于 CSV 导出）
            "_event_time": event_time,
            "_stat_date": stat_date,
        }
        events.append(attributes)

    return events


def save_to_csv(all_events, filename="wechat_article_stats.csv"):
    """保存汇总数据到 CSV（从 GrowingIO 事件格式转换）"""
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
        """将 GrowingIO 事件属性转换为 CSV 行"""
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


def save_to_json(events, filename="daily_report.json"):
    """保存上报数据到 JSON"""
    # 移除内部字段
    clean_events = []
    for event in events:
        clean = {k: v for k, v in event.items() if not k.startswith("_")}
        clean_events.append({
            "attributes": clean,
            "event_time": event.get("_event_time")
        })

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(clean_events, f, ensure_ascii=False, indent=2)

    print(f"📄 上报数据已保存至 {filename}，共 {len(clean_events)} 条记录")


# ============ GrowingIO 上报 ============

def upload_to_growio(events, debug=False, dry_run=False):
    """上报事件到 GrowingIO"""
    try:
        from growingio_tracker import DefaultConsumer, GrowingTracker

        consumer = DefaultConsumer(
            GROWINGIO_CONFIG["product_id"],
            GROWINGIO_CONFIG["data_source_id"],
            GROWINGIO_CONFIG["server_host"]
        )
        tracker = GrowingTracker.consumer(consumer)

        success_count = 0
        fail_count = 0

        for i, event_attrs in enumerate(events, 1):
            # 移除内部字段
            clean_attrs = {k: v for k, v in event_attrs.items() if not k.startswith("_")}

            print(f"[{i}/{len(events)}] ", end="")
            try:
                tracker.track_custom_event(
                    GROWINGIO_CONFIG["event_name"],
                    attributes=clean_attrs,
                    anonymous_id='python'
                )
                success_count += 1
                print("✅")
            except Exception as e:
                fail_count += 1
                print(f"❌ {e}")

        if hasattr(tracker, 'close'):
            tracker.close()
        return success_count, fail_count

    except ImportError:
        print("⚠️ growingio_tracker 未安装，跳过上报")
        print("   安装命令：pip install growingio-tracker")
        return 0, len(events)


# ============ 主流程 ============

def main():
    parser = argparse.ArgumentParser(description="微信文章数据抓取 + GrowingIO 上报")
    parser.add_argument("--start", type=str, help="开始日期 (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, help="结束日期 (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, help="最近 N 天")
    parser.add_argument("--today", action="store_true", help="仅今天")
    parser.add_argument("--dry-run", action="store_true", help="仅抓取不上报")
    parser.add_argument("--debug", action="store_true", help="调试模式")
    parser.add_argument("--output", type=str, default=".", help="输出目录")

    args = parser.parse_args()

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

    print(f"📅 日期范围：{start_date} 至 {end_date}")

    # 获取 access_token
    print("\n🔑 获取 access_token...")
    access_token = get_access_token()
    if not access_token:
        print("❌ 无法获取 access_token，程序退出")
        return

    print(f"✅ Token 获取成功：{access_token[:20]}...")

    # 抓取数据
    print("\n📥 开始抓取文章数据...")
    all_events = []
    all_csv_rows = []

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
        return
    
    # 去重处理
    print("\n🔍 去重检查...")
    new_events, reported_set = filter_new_events(all_events)
    
    if len(new_events) == 0:
        print("所有数据均已上报过，无需重复上报")
        return
    
    print(f"📊 新数据 {len(new_events)} 条，已上报记录总数 {len(reported_set)} 条")

    # 保存文件
    today_str = datetime.date.today().strftime("%Y%m%d")
    date_range_str = f"{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
    
    # 使用日期后缀避免覆盖，格式：daily_report_20260316_20260215_20260316.json
    json_filename = f"{args.output}/daily_report_{today_str}_{date_range_str}.json"
    print(f"\n💾 保存数据到 {json_filename}...")
    save_to_json(new_events, json_filename)
    
    # 保存 CSV（使用去重后的新数据）
    csv_filename = f"{args.output}/wechat_article_stats_{today_str}_{date_range_str}.csv"
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
                msgid_full = event.get("oa_articleId", "")
                stat_date = event.get("_stat_date", "")
                key = generate_report_key(msgid_full, stat_date)
                if key not in reported_set:
                    reported_set.add(key)
            state["reported"] = list(reported_set)
            save_report_state(state)
            print(f"💾 已更新上报记录，当前共 {len(reported_set)} 条记录")
        
        # 钉钉机器人播报
        send_dingtalk_notice(start_date, end_date, len(new_events), success, fail)
    else:
        print("\n⏭️  跳过上报（dry-run 模式）")


def send_dingtalk_notice(start_date, end_date, new_count, success_count, fail_count):
    """通过钉钉机器人发送任务完成通知"""
    DingDing_URL = "https://oapi.dingtalk.com/robot/send?access_token=84f55b1393f892b7859aca7692fc9e94a69280def75f72c90c1ebf40c9878e31"
    
    # 构建消息内容
    today = datetime.date.today()
    date_range = f"{start_date.strftime('%m/%d')} - {end_date.strftime('%m/%d')}"
    
    markdown_content = f"""# 📊 微信公众号数据抓取完成
    
## 📢 微信数据
**📅 抓取日期范围：** {date_range}
**📝 新增数据条数：** {new_count}
**✅ 上报成功：** {success_count}
**❌ 上报失败：** {fail_count}
**⏱️ 执行时间：** {today.strftime('%Y年%m月%d日')} """

    import urllib.parse
    import json
    
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": "📊 微信公众号数据抓取完成",
            "text": markdown_content
        }
    }
    
    try:
        import urllib.request
        req = urllib.request.Request(
            DingDing_URL,
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
