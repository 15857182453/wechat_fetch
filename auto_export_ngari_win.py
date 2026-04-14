#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
纳里健康报表导出 (真实浏览器版)
使用真实浏览器配置文件，网站无法检测到自动化
"""

import asyncio
import os
import json
from playwright.async_api import async_playwright

CONFIG = {
    'url': 'https://yypt.ngarihealth.com',
    'download_dir': r'C:\Users\44238\Desktop\业务对账数据\自动导出',
    # 使用 Edge 浏览器的真实配置文件路径
    'user_data_dir': r'C:\Users\44238\AppData\Local\Microsoft\Edge\User Data',
}

async def main():
    async with async_playwright() as p:
        os.makedirs(CONFIG['download_dir'], exist_ok=True)
        
        print("🌐 正在启动 Edge 浏览器...")
        print("⚠️  如果提示浏览器已打开，请先关闭 Edge 浏览器再运行")
        
        try:
            # 使用真实浏览器配置文件启动
            browser = await p.chromium.launch_persistent_context(
                user_data_dir=CONFIG['user_data_dir'],
                headless=False,
                channel='msedge',  # 使用 Edge 浏览器
                accept_downloads=True,
            )
            page = browser.pages[0] if browser.pages else await browser.new_page()
            
            print("✅ 浏览器已启动")
            print(f"📍 导航到: {CONFIG['url']}")
            await page.goto(CONFIG['url'])
            
            print("\n👉 请在浏览器中手动操作:")
            print("   1. 登录（你的 Edge 可能已自动登录）")
            print("   2. 完成验证")
            print("   3. 进入报表页，选择日期，点击导出")
            print("\n   全部完成后按回车键...")
            input()

            # 检查下载的文件
            files = os.listdir(CONFIG['download_dir'])
            if files:
                print("\n📁 已下载的文件:")
                for f in sorted(files, reverse=True)[:5]:
                    print(f"   {f}")
            else:
                print("\n⚠️  未检测到下载文件")

            await browser.close()
            print("\n✅ 完成！")
            
        except Exception as e:
            print(f"\n❌ 启动失败: {e}")
            print("\n💡 解决方案:")
            print("   1. 先关闭所有 Edge 浏览器窗口")
            print("   2. 确保 Edge 安装在默认路径")
            print("   3. 或者改用 Chrome，把 channel 改为 'chrome'")

if __name__ == '__main__':
    asyncio.run(main())
