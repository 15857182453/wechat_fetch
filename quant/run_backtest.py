"""
光迅科技 (002281.SZ) 量化回测主程序
====================================
运行所有策略并输出对比报告
"""

import pandas as pd
import numpy as np
import sys
sys.path.insert(0, '/home/openclaw/.openclaw/workspace/quant')

from backtest_engine import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# Font setup
fm.fontManager.addfont('/home/openclaw/.local/share/fonts/msyh.ttc')
prop = fm.FontProperties(fname='/home/openclaw/.local/share/fonts/msyh.ttc')

# Load data
df = pd.read_csv('/home/openclaw/.openclaw/workspace/002281_backtest_data.csv')
print(f"数据加载完成: {len(df)}条记录 ({df['trade_date'].iloc[0]} ~ {df['trade_date'].iloc[-1]})")
print(f"价格区间: ¥{df['low'].min():.2f} ~ ¥{df['high'].max():.2f}")

# Define strategies to run
strategies = [
    ('双均线交叉 (MA5/MA20)', lambda df, i: strategy_ma_crossover(df, i, fast=5, slow=20)),
    ('双均线交叉 (MA10/MA60)', lambda df, i: strategy_ma_crossover(df, i, fast=10, slow=60)),
    ('MACD金叉/死叉', strategy_macd),
    ('RSI超买超卖', lambda df, i: strategy_rsi(df, i, period=12, oversold=30, overbought=70)),
    ('RSI超买超卖(激进)', lambda df, i: strategy_rsi(df, i, period=6, oversold=25, overbought=75)),
    ('KDJ低位金叉', strategy_kdj),
    ('布林带反转', strategy_boll),
    ('多指标综合策略', strategy_combined),
    ('ATR跟踪止损(2x)', lambda df, i: strategy_atr_trailing(df, i, atr_mult=2.0)),
    ('ATR跟踪止损(3x)', lambda df, i: strategy_atr_trailing(df, i, atr_mult=3.0)),
]

# Run backtests
print("\n" + "="*80)
print("开始回测...")
print("="*80)

engine = BacktestEngine(df, initial_capital=1000000, commission_rate=0.0003, slippage=0.001)

results = []
for name, func in strategies:
    print(f"\n回测策略: {name}")
    result = engine.run(func, name)
    results.append(result)
    print(f"  总收益: {result.total_return:+.1f}% | 年化: {result.annual_return:+.1f}% | "
          f"最大回撤: {result.max_drawdown:.1f}% | 胜率: {result.win_rate:.1f}% | "
          f"交易次数: {result.total_trades}")

# Sort by total return
results.sort(key=lambda r: r.total_return, reverse=True)

# ========================================
# 输出对比报告
# ========================================

print("\n" + "="*80)
print("回测结果对比")
print("="*80)
print(f"\n{'策略名称':<25} {'总收益':>8} {'年化':>8} {'回撤':>8} {'夏普':>6} {'胜率':>6} {'交易':>4} {'盈亏比':>6}")
print("-"*80)

for r in results:
    pf = f"{r.profit_factor:.1f}" if r.profit_factor > 0 else "N/A"
    print(f"{r.strategy_name:<25} {r.total_return:>+7.1f}% {r.annual_return:>+7.1f}% "
          f"{r.max_drawdown:>7.1f}% {r.sharpe_ratio:>6.2f} {r.win_rate:>5.1f}% "
          f"{r.total_trades:>4} {pf:>6}")

# ========================================
# 生成图表
# ========================================

# 1. Equity curves comparison
fig, ax = plt.subplots(figsize=(16, 8))
fig.suptitle('光迅科技 (002281.SZ) — 策略净值对比 (2023.01-2026.05)',
             fontsize=16, fontweight='bold', fontproperties=prop)

colors = plt.cm.tab10(np.linspace(0, 1, len(results)))
for i, r in enumerate(results):
    if r.equity_curve:
        x = range(len(r.equity_curve))
        normalized = [e / r.equity_curve[0] * 100 for e in r.equity_curve]
        ax.plot(x, normalized, label=r.strategy_name, linewidth=1.5, alpha=0.8, color=colors[i])

ax.set_xlabel('交易日', fontproperties=prop)
ax.set_ylabel('净值 (基准=100)', fontproperties=prop)
ax.legend(prop=prop, fontsize=8, loc='upper left', ncol=2)
ax.grid(True, alpha=0.2)
ax.axhline(y=100, color='gray', linewidth=0.5, linestyle='--')

# Buy & Hold baseline
bh_return = (df.iloc[-1]['close'] / df.iloc[60]['close'] - 1) * 100  # from day 60 to avoid indicator warmup
bh_values = [100 * (df.iloc[i]['close'] / df.iloc[60]['close']) for i in range(60, len(df))]
ax.plot(range(60, len(df)), bh_values, color='black', linewidth=2, linestyle='--', 
        label=f'买入持有 ({bh_return:+.0f}%)', alpha=0.5)

plt.tight_layout()
plt.savefig('/home/openclaw/.openclaw/workspace/quant/equity_comparison.png', dpi=150, bbox_inches='tight')
plt.close()
print("\n图表已保存: equity_comparison.png")

# 2. Performance bar chart
fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle('光迅科技 (002281.SZ) — 策略性能对比',
             fontsize=16, fontweight='bold', fontproperties=prop)

strategy_names = [r.strategy_name[:20] for r in results]

# Total Return
ax = axes[0, 0]
colors_bar = ['#27AE60' if r.total_return > 0 else '#E74C3C' for r in results]
bars = ax.barh(strategy_names, [r.total_return for r in results], color=colors_bar, edgecolor='white')
for bar, val in zip(bars, [r.total_return for r in results]):
    ax.text(val + (1 if val > 0 else -1), bar.get_y() + bar.get_height()/2, 
            f'{val:+.1f}%', va='center', fontsize=9, fontweight='bold',
            ha='left' if val > 0 else 'right', fontproperties=prop)
ax.set_title('总收益率', fontproperties=prop, fontsize=12, fontweight='bold')
ax.axvline(x=0, color='gray', linewidth=0.5)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Max Drawdown
ax = axes[0, 1]
bars = ax.barh(strategy_names, [-r.max_drawdown for r in results], color='#E74C3C', edgecolor='white')
for bar, val in zip(bars, [-r.max_drawdown for r in results]):
    ax.text(val - 0.5, bar.get_y() + bar.get_height()/2, f'{abs(val):.1f}%', 
            va='center', fontsize=9, fontweight='bold', ha='right', fontproperties=prop)
ax.set_title('最大回撤', fontproperties=prop, fontsize=12, fontweight='bold')
ax.axvline(x=0, color='gray', linewidth=0.5)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Win Rate
ax = axes[1, 0]
bars = ax.barh(strategy_names, [r.win_rate for r in results], color='#3498DB', edgecolor='white')
for bar, val in zip(bars, [r.win_rate for r in results]):
    ax.text(val + 0.5, bar.get_y() + bar.get_height()/2, f'{val:.0f}%', 
            va='center', fontsize=9, fontweight='bold', fontproperties=prop)
ax.set_title('胜率', fontproperties=prop, fontsize=12, fontweight='bold')
ax.axvline(x=50, color='gray', linewidth=0.5, linestyle='--')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Sharpe Ratio
ax = axes[1, 1]
colors_sharpe = ['#27AE60' if r.sharpe_ratio > 0.5 else ('#F39C12' if r.sharpe_ratio > 0 else '#E74C3C') for r in results]
bars = ax.barh(strategy_names, [r.sharpe_ratio for r in results], color=colors_sharpe, edgecolor='white')
for bar, val in zip(bars, [r.sharpe_ratio for r in results]):
    ax.text(val + 0.02, bar.get_y() + bar.get_height()/2, f'{val:.2f}', 
            va='center', fontsize=9, fontweight='bold', fontproperties=prop)
ax.set_title('夏普比率', fontproperties=prop, fontsize=12, fontweight='bold')
ax.axvline(x=0, color='gray', linewidth=0.5)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig('/home/openclaw/.openclaw/workspace/quant/performance_comparison.png', dpi=150, bbox_inches='tight')
plt.close()
print("图表已保存: performance_comparison.png")

# 3. Best strategy equity curve with trades
best = results[0]
fig, ax = plt.subplots(figsize=(16, 6))
fig.suptitle(f'最佳策略: {best.strategy_name} — 净值曲线 & 交易记录',
             fontsize=16, fontweight='bold', fontproperties=prop)

ax.plot(best.equity_curve, color='#3498DB', linewidth=2, label='策略净值')
ax.axhline(y=1000000, color='gray', linewidth=0.5, linestyle='--', label='初始资金')

# Mark trades
for trade in best.trades:
    # Find index of entry and exit dates
    try:
        entry_idx = df[df['trade_date'] == int(trade.entry_date)].index[0]
        if trade.exit_date:
            exit_idx = df[df['trade_date'] == int(trade.exit_date)].index[0]
        else:
            exit_idx = entry_idx + 1
        
        # Entry marker
        ax.scatter(entry_idx, best.equity_history[entry_idx], marker='^', 
                  color='#E74C3C', s=100, zorder=5, edgecolors='white', linewidth=1)
        # Exit marker
        color = '#27AE60' if trade.pnl > 0 else '#E74C3C'
        ax.scatter(exit_idx, best.equity_history[exit_idx], marker='v',
                  color=color, s=100, zorder=5, edgecolors='white', linewidth=1)
    except:
        pass

ax.set_xlabel('交易日', fontproperties=prop)
ax.set_ylabel('净值 (¥)', fontproperties=prop)
ax.legend(prop=prop, fontsize=10)
ax.grid(True, alpha=0.2)

# Add trade table below
trade_data = []
for t in best.trades:
    holding = (pd.to_datetime(t.exit_date) - pd.to_datetime(t.entry_date)).days if t.exit_date else 0
    trade_data.append({
        'entry': t.entry_date, 'exit': t.exit_date,
        'entry_px': t.entry_price, 'exit_px': t.exit_price,
        'shares': t.shares, 'pnl': t.pnl, 'pnl_pct': t.pnl_pct,
        'days': holding, 'reason': t.stop_reason
    })

plt.tight_layout(rect=[0, 0.15, 1, 0.95])
plt.savefig('/home/openclaw/.openclaw/workspace/quant/best_strategy_detail.png', dpi=150, bbox_inches='tight')
plt.close()
print("图表已保存: best_strategy_detail.png")

# ========================================
# Save results to CSV
# ========================================
results_df = pd.DataFrame([{
    'strategy_name': r.strategy_name,
    'total_return_pct': r.total_return,
    'annual_return_pct': r.annual_return,
    'max_drawdown_pct': r.max_drawdown,
    'sharpe_ratio': r.sharpe_ratio,
    'win_rate_pct': r.win_rate,
    'total_trades': r.total_trades,
    'winning_trades': r.winning_trades,
    'losing_trades': r.losing_trades,
    'profit_factor': r.profit_factor,
    'avg_holding_days': r.avg_holding_days,
    'avg_win_pct': r.avg_win,
    'avg_loss_pct': r.avg_loss,
    'largest_win_pct': r.largest_win,
    'largest_loss_pct': r.largest_loss,
} for r in results])

results_df.to_csv('/home/openclaw/.openclaw/workspace/quant/backtest_results.csv', 
                  index=False, encoding='utf-8-sig')
print("\n结果已保存: backtest_results.csv")

# Print best strategy details
print("\n" + "="*80)
print(f"🏆 最佳策略: {best.strategy_name}")
print("="*80)
print(f"  总收益: {best.total_return:+.1f}%")
print(f"  年化收益: {best.annual_return:+.1f}%")
print(f"  最大回撤: {best.max_drawdown:.1f}%")
print(f"  夏普比率: {best.sharpe_ratio:.2f}")
print(f"  胜率: {best.win_rate:.1f}%")
print(f"  总交易: {best.total_trades} 笔 (胜 {best.winning_trades} / 负 {best.losing_trades})")
print(f"  盈亏比: {best.profit_factor:.1f}")
print(f"  平均持仓: {best.avg_holding_days:.0f} 天")
if best.largest_win:
    print(f"  最大单笔盈利: {best.largest_win:+.1f}%")
if best.largest_loss:
    print(f"  最大单笔亏损: {best.largest_loss:+.1f}%")

# Print trade log for best strategy
print(f"\n📋 {best.strategy_name} 交易记录:")
print(f"{'序号':>4} {'买入日期':>10} {'买入价':>8} {'卖出日期':>10} {'卖出价':>8} "
      f"{'盈亏':>8} {'收益率':>7} {'持仓':>4} {'原因':<20}")
print("-"*90)
for i, t in enumerate(best.trades):
    holding = (pd.to_datetime(t.exit_date) - pd.to_datetime(t.entry_date)).days if t.exit_date else 0
    print(f"{i+1:>4} {t.entry_date:>10} ¥{t.entry_price:>7.2f} {t.exit_date:>10} "
          f"¥{t.exit_price:>7.2f} {t.pnl:>+8.0f} {t.pnl_pct:>+6.1f}% {holding:>4}d {t.stop_reason:<20}")

print("\n" + "="*80)
print("回测完成！")
print("="*80)
