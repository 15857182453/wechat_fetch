#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试使用 Cookie 访问网站
"""

import http.cookiejar
import requests

# 加载 Netscape 格式 Cookie
cj = http.cookiejar.MozillaCookieJar()
cj.load('/mnt/c/Users/44238/Desktop/yypt.ngarihealth.com_cookies.txt', ignore_discard=True, ignore_expires=True)

session = requests.Session()
session.cookies = cj

# 测试访问
url = "https://yypt.ngarihealth.com/#/ehealth-yypt/reconciliation-statistics-finance-detail"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

try:
    print(f"正在访问: {url}")
    response = session.get("https://yypt.ngarihealth.com/", headers=headers, allow_redirects=True)
    print(f"状态码: {response.status_code}")
    print(f"最终 URL: {response.url}")
    
    # 检查是否登录成功
    if "login" not in response.url.lower() and response.status_code == 200:
        print("✅ Cookie 有效！看起来已登录")
        # 打印页面标题或关键信息
        if "<title>" in response.text:
            start = response.text.find("<title>") + 7
            end = response.text.find("</title>", start)
            if end > start:
                print(f"页面标题: {response.text[start:end]}")
    else:
        print("❌ 可能未登录或 Cookie 已过期")
        print(f"重定向到: {response.url}")

except Exception as e:
    print(f"请求失败: {e}")
