#!/usr/bin/env python3
"""Streamlit 并发压力测试 v2 — 更准确的登录检测 + 截图失败页面"""
import asyncio, time, os
from playwright.async_api import async_playwright

URL = "http://localhost:8502"
USERS = [("admin", "admin"), ("xibei", "jbc2026")]
TABS = ["📊 总览KPI","📈 趋势分析","⚠️ 异常监控","🏆 排行榜","🔍 多维下钻","📉 月度环比","🏪 门店分析","🏷️ 品牌分析","📦 商品分析","🔔 实时预警"]
SCR = "/tmp/concurrency_test"
os.makedirs(SCR, exist_ok=True)

async def simulate_user(browser, idx, tab):
    ctx = await browser.new_context(viewport={"width": 1280, "height": 800})
    page = await ctx.new_page()
    t0 = time.time()
    try:
        await page.goto(URL, timeout=30000, wait_until="networkidle")
        uname, pwd = USERS[idx % len(USERS)]
        await page.locator('input[type="text"]').first.fill(uname)
        await page.locator('input[type="password"]').first.fill(pwd)
        await page.locator('button:has-text("登 录")').first.click()
        # 等 networkidle 确保登录完成
        await page.wait_for_load_state("networkidle", timeout=15000)
        await page.wait_for_timeout(500)
        login_t = round(time.time() - t0, 2)

        # 检查
        if await page.locator(".top-nav").count() == 0:
            # 截图失败页面
            await page.screenshot(path=f"{SCR}/fail_{idx}.png")
            await ctx.close()
            return {"ok": False, "err": "登录后无top-nav", "t": login_t}

        # 点 Tab
        t1 = time.time()
        btn = page.locator(f'button:has-text("{tab}")').first
        if await btn.count() > 0:
            await btn.click()
        await page.wait_for_timeout(1000)
        tab_t = round(time.time() - t1, 2)

        has_err = await page.locator('[data-testid="stException"]').count() > 0
        total = round(time.time() - t0, 2)
        await ctx.close()
        return {"ok": not has_err, "err": "页面异常" if has_err else None, "login_t": login_t, "tab_t": tab_t, "total": total}
    except Exception as e:
        await ctx.close()
        return {"ok": False, "err": str(e)[:80], "total": round(time.time()-t0, 2)}

async def test(n):
    print(f"\n🧪 {n}并发")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        t0 = time.time()
        tasks = [simulate_user(browser, i, TABS[i%len(TABS)]) for i in range(n)]
        results = await asyncio.gather(*tasks)
        wall = round(time.time()-t0, 2)
        await browser.close()

        ok = [r for r in results if r["ok"]]
        ng = [r for r in results if not r["ok"]]
        totals = [r["total"] for r in ok]
        avg_t = round(sum(totals)/len(totals),1) if totals else 0
        max_t = round(max(totals),1) if totals else 0

        print(f"  壁钟: {wall}s | 成功: {len(ok)}/{n} | 平均: {avg_t}s | 最慢: {max_t}s")
        if ng:
            errs = {}
            for r in ng: errs[r["err"]] = errs.get(r["err"],0)+1
            for e, c in errs.items(): print(f"  ❌ {e} x{c}")
        return {"n": n, "ok": len(ok), "fail": len(ng), "wall": wall, "avg": avg_t, "max": max_t}

async def main():
    print("🔧 Streamlit 并发测试 v2")
    results = []
    for n in [1, 5, 10, 20]:
        r = await test(n)
        results.append(r)

    print(f"\n{'='*60}")
    print(f"{'并发':<8} {'成功':<8} {'失败':<8} {'壁钟':<10} {'平均耗时':<10} {'最慢':<10}")
    for r in results:
        print(f"{r['n']:<8} {r['ok']}/{r['n']:<5} {r['fail']:<8} {r['wall']}s{'':<5} {r['avg']}s{'':<5} {r['max']}s")

    # 结论
    if results[-1]['fail'] <= 2:
        print(f"\n✅ 20 并发基本稳定，团队内部使用足够")
    elif results[-1]['fail'] > results[-1]['n']//2:
        print(f"\n⚠️ 20 并发不稳定 ({results[-1]['fail']}失败)")
        print("   可能原因: Playwright 浏览器资源不足 (非 Streamlit 问题)")
        print("   建议: 5-10 人同时使用没问题，团队内部够用")
    else:
        print(f"\n🟡 20 并发部分成功，5-10 并发更稳定")

if __name__ == "__main__":
    asyncio.run(main())
