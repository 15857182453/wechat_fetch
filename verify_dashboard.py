#!/usr/bin/env python3
"""Dashboard 验证脚本 — 模拟登录 + 逐个 Tab 截图 + 错误检测"""
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
import os

SCREENSHOT_DIR = "/tmp/jbc_screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

TABS = [
    "📊 总览KPI", "📈 趋势分析", "⚠️ 异常监控", "🏆 排行榜",
    "🔍 多维下钻", "📉 月度环比", "🏪 门店分析", "🏷️ 品牌分析",
    "📦 商品分析", "🔔 实时预警", "👥 用户管理", "📋 数据导入"
]

async def verify():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})

        results = []

        # 1. 登录页截图
        print("📸 1. 登录页面...")
        await page.goto("http://localhost:8502", timeout=15000, wait_until="networkidle")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/01_login.png", full_page=True)
        print("   ✅ 截图: 01_login.png")

        # 2. 执行登录
        print("🔑 2. 登录中...")
        try:
            # 填写用户名
            username_input = page.locator('input[type="text"]').first
            await username_input.fill("admin")
            # 填写密码
            password_input = page.locator('input[type="password"]').first
            await password_input.fill("admin")
            # 点击登录按钮
            login_btn = page.locator('button:has-text("登 录")').first
            await login_btn.click()
            await page.wait_for_timeout(3000)
            await page.wait_for_load_state("networkidle", timeout=10000)

            # 检查是否成功登录 (应该有 top-nav)
            top_nav = page.locator(".top-nav")
            if await top_nav.count() > 0:
                print("   ✅ 登录成功")
                await page.screenshot(path=f"{SCREENSHOT_DIR}/02_after_login.png", full_page=True)
            else:
                # 可能还在登录页, 检查错误
                error_msg = page.locator('[data-testid="stNotification"]')
                if await error_msg.count() > 0:
                    err_text = await error_msg.first.text_content()
                    print(f"   ❌ 登录失败: {err_text}")
                else:
                    print("   ⚠️ 未检测到 top-nav，检查页面状态...")
                    await page.screenshot(path=f"{SCREENSHOT_DIR}/02_login_error.png", full_page=True)
        except Exception as e:
            print(f"   ❌ 登录异常: {e}")
            await page.screenshot(path=f"{SCREENSHOT_DIR}/02_login_exception.png", full_page=True)

        # 3. 逐个 Tab 验证
        for idx, tab_name in enumerate(TABS):
            print(f"📸 {idx+3}. Tab: {tab_name}...")
            try:
                # 点击 Tab
                tab_btn = page.locator(f'button:has-text("{tab_name}")').first
                if await tab_btn.count() == 0:
                    # Tab 可能在 overflow 中不可见，尝试滚动
                    tab_list = page.locator('[data-baseweb="tab-list"]').first
                    if await tab_list.count() > 0:
                        # 尝试找到 tab 按钮
                        all_tabs = page.locator('[data-baseweb="tab"]')
                        tab_count = await all_tabs.count()
                        found = False
                        for i in range(tab_count):
                            tab = all_tabs.nth(i)
                            text = await tab.text_content()
                            if tab_name in (text or ""):
                                await tab.click()
                                found = True
                                break
                        if not found:
                            print(f"   ⚠️ Tab 未找到: {tab_name}")
                            results.append((tab_name, "NOT_FOUND"))
                            continue
                    else:
                        print(f"   ⚠️ Tab 列表未找到")
                        results.append((tab_name, "NO_TAB_LIST"))
                        continue
                else:
                    await tab_btn.click()

                await page.wait_for_timeout(2000)

                # 检查是否有 Streamlit 异常弹窗
                st_exception = page.locator('[data-testid="stException"]')
                if await st_exception.count() > 0:
                    exc_text = await st_exception.first.text_content()
                    print(f"   ❌ Streamlit 异常: {exc_text[:200]}")
                    results.append((tab_name, f"EXCEPTION: {exc_text[:100]}"))
                    continue

                # 检查 st.error / st.warning 消息中是否包含报错
                st_notif = page.locator('[data-testid="stNotification"]')
                ncount = await st_notif.count()
                has_db_error = False
                for i in range(ncount):
                    text = await st_notif.nth(i).text_content()
                    if text and ("DatabaseError" in text or "UndefinedColumn" in text or "ProgrammingError" in text):
                        has_db_error = True
                        print(f"   ❌ DB错误: {text[:200]}")
                        results.append((tab_name, f"DB_ERROR: {text[:100]}"))
                        break

                if not has_db_error:
                    print(f"   ✅ 正常")
                    results.append((tab_name, "OK"))

                # 截图
                filename = f"{SCREENSHOT_DIR}/{idx+3:02d}_{tab_name.replace(' ','_').replace('⚠️','').replace('🔍','').replace('🔔','').replace('👥','').replace('🏆','').replace('🏪','').replace('🏷️','').replace('📦','').replace('📋','').replace('📊','').replace('📈','').replace('📉','')}.png"
                await page.screenshot(path=filename, full_page=True)

            except Exception as e:
                print(f"   ❌ 异常: {e}")
                results.append((tab_name, f"EXCEPTION: {str(e)[:80]}"))

        await browser.close()

        # 汇总
        print("\n" + "=" * 60)
        print("📊 验证结果汇总")
        print("=" * 60)
        ok = sum(1 for _, status in results if status == "OK")
        fail = sum(1 for _, status in results if status != "OK")
        for tab, status in results:
            icon = "✅" if status == "OK" else "❌"
            print(f"  {icon} {tab}: {status}")
        print(f"\n{ok} 通过 / {fail} 失败 / {len(results)} 总计")

        return results

asyncio.run(verify())
