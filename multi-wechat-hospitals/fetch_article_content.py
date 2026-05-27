#!/usr/bin/env python3
"""
获取微信公众号已发布文章的正文内容，并与现有统计数据拼接

功能：
1. 通过 freepublish_batchget 接口批量获取所有已发布文章（含 content 正文）
2. 建立 title → content 的映射字典
3. 读取现有抓取的统计数据（JSON/CSV），通过标题匹配拼接正文内容
4. 输出拼接后的完整数据

使用方法：
    # 获取文章内容并拼接到现有数据
    python3 fetch_article_content.py --config hospitals.yml --hospital "杭州师范大学附属医院"

    # 仅获取文章内容列表（不拼接）
    python3 fetch_article_content.py --config hospitals.yml --hospital "浙江省中医院" --list-only

    # 指定现有数据文件拼接
    python3 fetch_article_content.py --config hospitals.yml --hospital "杭州师范大学附属医院" --data-file path/to/report.json

    # 获取所有医院
    python3 fetch_article_content.py --config hospitals.yml
"""

import yaml
import requests
import json
import os
import sys
import time
import argparse
import csv
import glob
from datetime import datetime

# 添加依赖路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MEDIA_CRAWLER_DIR = "/home/openclaw/.openclaw/workspace/media-crawler"
if MEDIA_CRAWLER_DIR not in sys.path:
    sys.path.insert(0, MEDIA_CRAWLER_DIR)

try:
    from client import Client, Request
except ImportError:
    print("⚠️ 无法导入 client 模块，将无法获取 access_token")
    Client = None
    Request = None


# ============ 配置加载 ============

def load_hospitals_config(config_path):
    """加载医院配置文件"""
    full_path = os.path.join(SCRIPT_DIR, config_path) if not os.path.isabs(config_path) else config_path
    with open(full_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def get_access_token(openapi_config):
    """通过 OpenAPI 获取微信 access_token"""
    if Client is None:
        print("❌ client 模块不可用")
        return None

    try:
        client = Client(
            api_url=openapi_config["api_url"],
            app_key=openapi_config["app_key"],
            app_secret=openapi_config["app_secret"],
            encoding_aes_key=""
        )

        request = Request()
        request.service_id = "openapi.wxAccessTokenService"
        request.method = "getWxTokenByWxAppId"
        request.bodys = [openapi_config["app_key"], openapi_config["wx_app_id"]]
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


# ============ 文章内容获取 ============

def fetch_published_articles_batch(access_token, offset=0, count=20, no_content=0):
    """
    调用 freepublish_batchget 接口获取已发布文章列表
    
    参数：
        access_token: 微信 access_token
        offset: 起始位置
        count: 返回数量（1-20）
        no_content: 0 返回正文，1 不返回正文
    
    返回：
        (items, total_count) 或 (None, 0)
    """
    url = f"https://api.weixin.qq.com/cgi-bin/freepublish/batchget?access_token={access_token}"
    payload = {
        "offset": offset,
        "count": min(count, 20),
        "no_content": no_content
    }

    try:
        resp = requests.post(url, json=payload, timeout=30)
        result = resp.json()

        if result.get("errcode", 0) != 0:
            print(f"❌ batchget 失败：errcode={result.get('errcode')}, errmsg={result.get('errmsg')}")
            return None, 0

        total_count = result.get("total_count", 0)
        items = result.get("item", [])
        return items, total_count

    except Exception as e:
        print(f"❌ batchget 请求异常：{e}")
        return None, 0


def fetch_single_article(access_token, article_id):
    """
    调用 freepublishGetarticle 接口获取单篇文章详情
    
    参数：
        access_token: 微信 access_token
        article_id: 文章 ID
    
    返回：
        news_item 列表或 None
    """
    url = f"https://api.weixin.qq.com/cgi-bin/freepublish/getarticle?access_token={access_token}"
    payload = {"article_id": article_id}

    try:
        resp = requests.post(url, json=payload, timeout=30)
        result = resp.json()

        if result.get("errcode", 0) != 0:
            print(f"❌ getarticle 失败：errcode={result.get('errcode')}, errmsg={result.get('errmsg')}")
            return None

        return result.get("news_item", [])

    except Exception as e:
        print(f"❌ getarticle 请求异常：{e}")
        return None


def fetch_all_published_articles(access_token, max_articles=500):
    """
    分页获取所有已发布文章，建立 title → content 映射
    
    参数：
        access_token: 微信 access_token
        max_articles: 最大获取数量（防止无限循环）
    
    返回：
        {
            "title1": {"content": "...", "author": "...", "digest": "...", "url": "...", "article_id": "..."},
            "title2": {...},
            ...
        }
    """
    title_content_map = {}
    offset = 0
    count = 20  # 每次最多 20 条
    total_fetched = 0

    print(f"\n📥 开始批量获取已发布文章内容...")

    while total_fetched < max_articles:
        items, total_count = fetch_published_articles_batch(access_token, offset=offset, count=count, no_content=0)

        if items is None:
            print(f"❌ 获取失败，已获取 {total_fetched} 篇")
            break

        if not items:
            print(f"✅ 所有文章获取完毕，共 {total_fetched} 篇")
            break

        for item in items:
            article_id = item.get("article_id", "")
            update_time = item.get("update_time", 0)
            news_items = item.get("content", {}).get("news_item", [])

            for idx, news in enumerate(news_items):
                title = news.get("title", "").strip()
                if title:
                    title_content_map[title] = {
                        "content": news.get("content", ""),
                        "author": news.get("author", ""),
                        "digest": news.get("digest", ""),
                        "content_source_url": news.get("content_source_url", ""),
                        "thumb_url": news.get("thumb_url", ""),
                        "url": news.get("url", ""),
                        "article_id": article_id,
                        "position": idx + 1,
                        "update_time": update_time,
                        "is_deleted": news.get("is_deleted", False),
                    }

        batch_count = len(items)
        total_fetched += batch_count
        offset += batch_count

        # 打印进度
        print(f"   📄 已获取 {total_fetched}/{total_count} 篇（本批 {batch_count} 篇）")

        # 如果已获取全部，退出
        if total_fetched >= total_count:
            print(f"✅ 所有文章获取完毕，共 {total_fetched} 篇")
            break

        # 频率限制：每秒最多 5 次
        time.sleep(0.3)

    print(f"📊 建立标题映射：{len(title_content_map)} 个唯一标题")
    return title_content_map


# ============ 数据拼接 ============

def load_existing_data(data_file):
    """加载现有的统计数据（JSON 格式）"""
    with open(data_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def merge_content(events, title_content_map):
    """
    将文章正文内容拼接到现有统计数据中
    
    匹配策略：通过 articleTitle 精确匹配
    
    参数：
        events: 现有统计数据列表
        title_content_map: {title: {content, author, digest, ...}}
    
    返回：
        merged_events, match_count, miss_count
    """
    match_count = 0
    miss_count = 0
    matched_titles = set()
    missed_titles = set()

    for event in events:
        title = event.get("articleTitle", "").strip()
        if title in title_content_map:
            content_info = title_content_map[title]
            event["oa_content"] = content_info["content"]
            event["oa_author"] = content_info.get("author", "")
            event["oa_digest"] = content_info.get("digest", "")
            event["oa_thumbUrl"] = content_info.get("thumb_url", "")
            event["oa_freepublish_article_id"] = content_info.get("article_id", "")
            matched_titles.add(title)
            match_count += 1
        else:
            missed_titles.add(title)
            miss_count += 1

    return events, match_count, miss_count, matched_titles, missed_titles


def save_merged_data(events, output_file, format="json"):
    """保存拼接后的数据"""
    if format == "json":
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(events, f, ensure_ascii=False, indent=2)
    elif format == "csv":
        if not events:
            return
        fieldnames = list(events[0].keys())
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(events)

    print(f"💾 已保存到：{output_file}")


# ============ 主流程 ============

def process_hospital(hospital_config, args):
    """处理单个医院"""
    hospital_name = hospital_config['name']
    output_dir = hospital_config.get('output_dir', 'logs')
    logs_dir = os.path.join(SCRIPT_DIR, output_dir, 'logs')

    print(f"\n{'='*60}")
    print(f"🏥 {hospital_name}")
    print(f"{'='*60}")

    # 1. 获取 access_token
    print("\n🔑 获取 access_token...")
    openapi_config = hospital_config['openapi']
    access_token = get_access_token(openapi_config)
    if not access_token:
        print("❌ 无法获取 access_token")
        return False
    print(f"✅ Token: {access_token[:20]}...")

    # 2. 批量获取文章内容
    title_content_map = fetch_all_published_articles(
        access_token,
        max_articles=args.max_articles
    )

    if not title_content_map:
        print("❌ 未获取到任何文章内容")
        return False

    # 3. 如果是 list-only 模式，仅列出文章
    if args.list_only:
        print(f"\n📋 文章列表（共 {len(title_content_map)} 篇）：")
        for i, (title, info) in enumerate(title_content_map.items(), 1):
            content_len = len(info['content']) if info['content'] else 0
            deleted = " [已删除]" if info.get('is_deleted') else ""
            print(f"   {i}. {title[:50]}{'...' if len(title) > 50 else ''} ({content_len} 字){deleted}")
        
        # 保存文章列表
        list_file = os.path.join(logs_dir, f"article_content_list.json")
        os.makedirs(logs_dir, exist_ok=True)
        with open(list_file, 'w', encoding='utf-8') as f:
            json.dump(title_content_map, f, ensure_ascii=False, indent=2)
        print(f"\n💾 文章列表已保存：{list_file}")
        return True

    # 4. 加载现有统计数据
    if args.data_file:
        data_file = args.data_file
    else:
        # 自动查找最新的 JSON 数据文件
        pattern = os.path.join(logs_dir, "*_daily_report_*.json")
        json_files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
        if not json_files:
            print(f"⚠️ 未找到现有数据文件：{pattern}")
            print("   请使用 --data-file 指定数据文件，或先运行 run_hospitals.py 抓取统计数据")
            
            # 仍然保存文章内容映射
            content_file = os.path.join(logs_dir, "article_content_map.json")
            os.makedirs(logs_dir, exist_ok=True)
            with open(content_file, 'w', encoding='utf-8') as f:
                json.dump(title_content_map, f, ensure_ascii=False, indent=2)
            print(f"💾 文章内容映射已保存：{content_file}")
            return True
        data_file = json_files[0]

    print(f"\n📂 加载统计数据：{os.path.basename(data_file)}")
    events = load_existing_data(data_file)
    print(f"   共 {len(events)} 条记录")

    # 5. 拼接
    print(f"\n🔗 开始拼接文章内容...")
    merged_events, match_count, miss_count, matched_titles, missed_titles = merge_content(events, title_content_map)

    print(f"\n📊 拼接结果：")
    print(f"   ✅ 匹配成功：{match_count} 条（{len(matched_titles)} 篇文章）")
    print(f"   ❌ 未匹配：{miss_count} 条（{len(missed_titles)} 篇文章）")

    if missed_titles:
        print(f"\n⚠️ 未匹配的文章标题：")
        for title in list(missed_titles)[:10]:
            print(f"   - {title[:60]}{'...' if len(title) > 60 else ''}")
        if len(missed_titles) > 10:
            print(f"   ... 还有 {len(missed_titles) - 10} 篇")

    # 6. 保存拼接后的数据
    os.makedirs(logs_dir, exist_ok=True)
    
    # JSON 格式
    merged_json = os.path.join(logs_dir, f"merged_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    save_merged_data(merged_events, merged_json, format="json")

    # CSV 格式
    merged_csv = os.path.join(logs_dir, f"merged_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    save_merged_data(merged_events, merged_csv, format="csv")

    # 同时保存内容映射表
    content_map_file = os.path.join(logs_dir, "article_content_map.json")
    with open(content_map_file, 'w', encoding='utf-8') as f:
        json.dump(title_content_map, f, ensure_ascii=False, indent=2)
    print(f"💾 内容映射表：{content_map_file}")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="获取微信公众号文章正文内容并拼接到统计数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 获取并拼接所有医院
  python3 fetch_article_content.py --config hospitals.yml

  # 指定医院
  python3 fetch_article_content.py --config hospitals.yml --hospital "浙江省中医院"

  # 仅列出文章（不拼接）
  python3 fetch_article_content.py --config hospitals.yml --hospital "杭州师范大学附属医院" --list-only

  # 指定数据文件拼接
  python3 fetch_article_content.py --config hospitals.yml --hospital "杭州师范大学附属医院" --data-file report.json
        """
    )

    parser.add_argument("--config", default="hospitals.yml", help="医院配置文件")
    parser.add_argument("--hospital", type=str, help="指定医院名称")
    parser.add_argument("--data-file", type=str, help="指定现有统计数据文件路径")
    parser.add_argument("--list-only", action="store_true", help="仅列出文章，不拼接")
    parser.add_argument("--max-articles", type=int, default=500, help="最大获取文章数（默认 500）")

    args = parser.parse_args()

    # 加载配置
    config = load_hospitals_config(args.config)
    hospitals = config.get('hospitals', [])

    if args.hospital:
        hospitals = [h for h in hospitals if h['name'] == args.hospital]
        if not hospitals:
            print(f"❌ 未找到医院：{args.hospital}")
            print(f"   可选：{[h['name'] for h in config.get('hospitals', [])]}")
            return

    print("=" * 60)
    print("📰 微信公众号文章内容获取 & 数据拼接工具")
    print("=" * 60)
    print(f"📋 待处理医院：{len(hospitals)} 家")

    success = 0
    fail = 0

    for hospital in hospitals:
        if process_hospital(hospital, args):
            success += 1
        else:
            fail += 1

    print(f"\n{'='*60}")
    print(f"📊 执行完毕：✅ {success} 成功，❌ {fail} 失败")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
