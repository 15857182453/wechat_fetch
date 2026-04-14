#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动化导出对账统计报表（财务版）
网站：https://yypt.ngarihealth.com
"""

import asyncio
import os
import time
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

# 配置
CONFIG = {
    'url': 'https://yypt.ngarihealth.com/#/ehealth-yypt/reconciliation-statistics-finance-detail',
    'username': 'zly_yyzx',
    'password': 'Hello12345~',
    'download_dir': '/home/openclaw/.openclaw/workspace/报表导出',
    'state_file': '/home/openclaw/.openclaw/workspace/login_state.json',
    'headless': False,  # 首次运行设为 False，之后可设为 True
}

async def save_state(context, state_file):
    """保存登录状态"""
    await context.storage_state(path=state_file)
    print(f"✅ 登录状态已保存到：{state_file}")

async def login_and_export():
    """主流程：登录 + 导航 + 导出"""
    async with async_playwright() as p:
        # 创建下载目录
        os.makedirs(CONFIG['download_dir'], exist_ok=True)
        
        # 检查是否有保存的登录状态
        if os.path.exists(CONFIG['state_file']):
            print("📋 使用已保存的登录状态...")
            browser = await p.chromium.launch(headless=CONFIG['headless'])
            context = await browser.new_context(
                storage_state=CONFIG['state_file'],
                accept_downloads=True,
                downloads_path=CONFIG['download_dir']
            )
            page = await context.new_page()
        else:
            print("🔑 首次登录，请手动完成验证...")
            browser = await p.chromium.launch(headless=False)  # 首次必须显示浏览器
            context = await browser.new_context(
                accept_downloads=True,
                downloads_path=CONFIG['download_dir']
            )
            page = await context.new_page()
            
            # 导航到登录页面
            print(f"🌐 打开网站...")
            await page.goto(CONFIG['url'], wait_until='domcontentloaded')
            await page.wait_for_timeout(3000)
            
            # 尝试登录
            try:
                print("📝 输入账号密码...")
                # 查找用户名输入框
                username_input = page.locator('input[placeholder*="用户名"], input[placeholder*="账号"], input[name="username"]').first
                if await username_input.count() == 0:
                    # 尝试其他选择器
                    username_input = page.locator('input').first
                
                await username_input.click()
                await username_input.fill(CONFIG['username'])
                
                # 查找密码输入框
                password_input = page.locator('input[type="password"]').first
                await password_input.click()
                await password_input.fill(CONFIG['password'])
                
                print("⚠️  请在浏览器中完成滑动验证，然后点击登录")
                print("   完成后按回车键继续...")
                input()
                
                # 保存登录状态
                await save_state(context, CONFIG['state_file'])
                print("✅ 登录状态已保存，下次运行将自动登录！")
                
            except Exception as e:
                print(f"❌ 登录失败：{e}")
                print("请在浏览器中手动完成登录，然后按回车继续")
                input()
                await save_state(context, CONFIG['state_file'])
        
        # 导航到导出页面
        print(f"\n📊 导航到报表页面...")
        await page.goto(CONFIG['url'], wait_until='domcontentloaded')
        await page.wait_for_timeout(5000)
        
        # 选择业务分账明细
        print("📋 选择业务分账明细...")
        try:
            # 尝试查找下拉框或选项
            # 常见选择器：select, el-select, ant-select 等
            selectors = [
                '.el-select',
                '.ant-select',
                'select',
                '[class*="select"]',
                'text=业务分账明细',
            ]
            
            for sel in selectors:
                elements = page.locator(sel)
                if await elements.count() > 0:
                    print(f"  找到选择器：{sel}")
                    break
            
            print("⚠️  请在浏览器中确认选择了'业务分账明细'")
            
        except Exception as e:
            print(f"  选择器未找到：{e}")
        
        # 选择日期（默认昨天）
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        print(f"📅 选择日期：{yesterday}")
        
        print("\n⚠️  请在浏览器中：")
        print("   1. 确认选择了正确的日期")
        print("   2. 点击'导出'按钮")
        print("   3. 等待文件下载完成")
        print("   完成后按回车键...")
        input()
        
        print("\n✅ 导出流程完成！")
        print(f"📁 文件保存在：{CONFIG['download_dir']}")
        
        # 列出下载的文件
        files = os.listdir(CONFIG['download_dir'])
        if files:
            print("\n📄 已下载的文件：")
            for f in sorted(files, reverse=True)[:5]:
                print(f"   - {f}")
        
        await browser.close()

if __name__ == '__main__':
    print("=" * 60)
    print("📊 自动化导出对账统计报表")
    print("=" * 60)
    print(f"\n🌐 网站：{CONFIG['url']}")
    print(f"👤 账号：{CONFIG['username']}")
    print(f"📁 下载目录：{CONFIG['download_dir']}")
    print(f"💾 状态文件：{CONFIG['state_file']}")
    print("\n" + "=" * 60)
    
    asyncio.run(login_and_export())
