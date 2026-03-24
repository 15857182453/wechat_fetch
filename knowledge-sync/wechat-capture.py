#!/usr/bin/env python3
"""
微信公众号文章批量抓取工具
用于抓取已知链接的文章内容，保存到飞书多维表格

用法：
    python3 wechat-capture.py --links links.txt
    python3 wechat-capture.py --url "https://mp.weixin.qq.com/s/xxx"
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import argparse
from datetime import datetime

# 飞书 API 配置
FEISHU_CONFIG = {
    'app_id': 'cli_a924dc7790625bd3',
    'app_secret': 'KfKqczGdsExKvXMq4m8HafrFc3WQx7t1',
    'app_token': 'BKABw6CJriaeYtkE9v9cjy4wneg',
    'table_id': 'tblhWgNl1uLYa4GL',
}

def get_feishu_token():
    """获取飞书 Access Token"""
    url = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
    data = {
        'app_id': FEISHU_CONFIG['app_id'],
        'app_secret': FEISHU_CONFIG['app_secret'],
    }
    response = requests.post(url, json=data)
    result = response.json()
    
    if result.get('code') != 0:
        raise Exception(f'获取 Token 失败：{result.get("msg")}')
    
    return result['tenant_access_token']

def capture_article(url):
    """抓取微信公众号文章内容"""
    print(f'📥 抓取：{url}')
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            print(f'   ❌ 失败：HTTP {response.status_code}')
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 提取标题
        title_elem = soup.find('h1', class_='rich_media_title')
        if not title_elem:
            title_elem = soup.find('h2', class_='rich_media_title')
        title = title_elem.get_text(strip=True) if title_elem else '无标题'
        
        # 提取发布时间
        publish_elem = soup.find('span', class_='rich_media_meta_text')
        publish_date = publish_elem.get_text(strip=True) if publish_elem else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 提取作者
        author_elem = soup.find('span', class_='rich_media_meta_nickname')
        author = author_elem.get_text(strip=True) if author_elem else '浙江省中医院'
        
        # 提取正文
        content_elem = soup.find('div', class_='rich_media_content')
        if not content_elem:
            content_elem = soup.find('div', id='js_content')
        
        content = content_elem.get_text('\n', strip=True) if content_elem else ''
        
        # 提取封面图
        cover_elem = soup.find('img', class_='rich_media_content')
        cover_url = cover_elem.get('src', '') if cover_elem else ''
        
        # 提取摘要（取前 200 字）
        summary = content[:200] + '...' if len(content) > 200 else content
        
        print(f'   ✅ 成功：{title[:30]}...')
        
        return {
            'title': title,
            'publish_date': publish_date,
            'author': author,
            'content': content,
            'summary': summary,
            'cover_url': cover_url,
            'url': url,
        }
        
    except Exception as e:
        print(f'   ❌ 错误：{str(e)}')
        return None

def save_to_feishu(token, article):
    """保存文章到飞书多维表格"""
    url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_CONFIG["app_token"]}/tables/{FEISHU_CONFIG["table_id"]}/records'
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    
    # 飞书表格字段映射
    fields = {
        '标题': article['title'],
        '文章内容': article['content'],
        '文章总结': article['summary'],
        '文章地址': article['url'],
        '封面地址': article['cover_url'],
        '发表时间': article['publish_date'],
        '文章总结 kimi': article['summary'],  # 可以调用 AI API 生成更好的摘要
    }
    
    data = {
        'fields': fields,
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        
        if result.get('code') == 0:
            print(f'   💾 已保存到飞书表格')
            return True
        else:
            print(f'   ❌ 保存失败：{result.get("msg")}')
            return False
            
    except Exception as e:
        print(f'   ❌ 保存错误：{str(e)}')
        return False

def main():
    parser = argparse.ArgumentParser(description='微信公众号文章抓取工具')
    parser.add_argument('--url', type=str, help='单篇文章链接')
    parser.add_argument('--links', type=str, help='文章链接列表文件（每行一个）')
    parser.add_argument('--output', type=str, default='articles.json', help='输出文件（不保存到飞书时）')
    parser.add_argument('--dry-run', action='store_true', help='仅抓取不保存到飞书')
    
    args = parser.parse_args()
    
    # 收集文章链接
    urls = []
    
    if args.url:
        urls.append(args.url)
    
    if args.links:
        with open(args.links, 'r', encoding='utf-8') as f:
            urls.extend([line.strip() for line in f if line.strip()])
    
    if not urls:
        print('❌ 请提供文章链接（--url 或 --links）')
        parser.print_help()
        return
    
    print(f'🚀 开始抓取 {len(urls)} 篇文章\n')
    
    # 获取飞书 Token（如果需要保存）
    token = None
    if not args.dry_run:
        try:
            token = get_feishu_token()
            print('✅ 飞书 Token 获取成功\n')
        except Exception as e:
            print(f'❌ 飞书 Token 获取失败：{str(e)}')
            print('   将仅抓取不保存\n')
            args.dry_run = True
    
    # 抓取文章
    articles = []
    success_count = 0
    
    for i, url in enumerate(urls, 1):
        print(f'[{i}/{len(urls)}] ', end='')
        
        article = capture_article(url)
        
        if article:
            articles.append(article)
            success_count += 1
            
            # 保存到飞书
            if token and not args.dry_run:
                save_to_feishu(token, article)
                time.sleep(0.5)  # 避免请求过快
        
        time.sleep(1)  # 避免请求过快
    
    # 输出统计
    print(f'\n📊 抓取完成')
    print(f'   成功：{success_count}/{len(urls)}')
    print(f'   失败：{len(urls) - success_count}')
    
    # 保存到本地文件
    if articles:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        print(f'   已保存到：{args.output}')
    
    # 输出文章标题
    print(f'\n📋 抓取的文章：')
    for article in articles:
        print(f'   - {article["title"]}')

if __name__ == '__main__':
    main()
