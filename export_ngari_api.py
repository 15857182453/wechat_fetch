#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
纳里健康对账报表 API 自动导出
完全无需浏览器，直接调用接口
"""

import requests
import json
import os
from datetime import datetime, timedelta

# ================= 配置 =================
CONFIG = {
    'api_url': 'https://yypt.ngarihealth.com/ehealth-opbase/openapi/gateway',
    'session_id': '11c884d6-56c3-40b1-b76a-d15c895b729b',
    'csrf_tk': '851915b0-de1e-4755-833f-f8adf1605fb4164238428',
    'download_dir': '/mnt/c/Users/44238/Desktop/业务对账数据/自动导出',
}

HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Content-Type': 'application/json',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0',
    'Origin': 'https://yypt.ngarihealth.com',
    'Referer': 'https://yypt.ngarihealth.com/',
    'X-Ca-Key': 'ngari-eeop',
    'X-Service-Id': 'opexport.exportService',
    'X-Service-Method': 'exportFinanceBillOrderExcel',
    'X-Service-Encrypt': '1',
    'csrfTk': CONFIG['csrf_tk'],
    'Encoding': 'utf-8',
}

COOKIES = {
    'SESSION': CONFIG['session_id'],
    'ut': 'NjkzN2JjMzhmMmM4M2QzZThlODU1ZjM4JjE2NDIzODQyOA==',
}

def export_report(start_date=None, end_date=None):
    """
    导出报表
    start_date: 开始日期 YYYY-MM-DD，默认昨天
    end_date: 结束日期 YYYY-MM-DD，默认昨天
    """
    os.makedirs(CONFIG['download_dir'], exist_ok=True)
    
    if not start_date:
        start_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = start_date
    
    print(f"📅 导出日期范围：{start_date} 到 {end_date}")
    
    # 注意：请求体是加密的，需要分析加密算法
    # 这里提供基础框架
    print("🔍 尝试导出...")
    print(f"API: {CONFIG['api_url']}")
    print(f"方法：exportFinanceBillOrderExcel")
    print(f"日期：{start_date} ~ {end_date}")
    
    # 由于请求体是加密的 (X-Content-MD5, X-Ca-Signature)，
    # 我们需要分析加密算法或使用 Playwright 在本地运行
    
    print("\n⚠️  请求体已加密，需要以下任一方案：")
    print("   方案 1：在你的 Windows 电脑上运行 Playwright 脚本")
    print("   方案 2：分析网站 JS 代码，找出加密算法")
    
    return {
        'status': 'need_encryption',
        'message': '请求体需要加密签名'
    }

if __name__ == '__main__':
    print("="*60)
    print("📊 纳里健康对账报表 API 导出")
    print("="*60)
    print(f"\n🌐 API: {CONFIG['api_url']}")
    print(f"📁 保存目录：{CONFIG['download_dir']}")
    print("\n" + "="*60)
    
    result = export_report()
    print(f"\n结果：{result['message']}")
