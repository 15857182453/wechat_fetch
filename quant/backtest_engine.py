"""
光迅科技 (002281.SZ) 量化回测引擎
====================================
支持多种策略回测：
1. 双均线交叉策略
2. MACD金叉/死叉策略
3. RSI超买超卖策略
4. KDJ策略
5. 布林带策略
6. 多指标综合策略
7. ATR跟踪止损策略
"""

import pandas as pd
import numpy as np
from typing import Callable, List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
import json

class Signal(Enum):
    BUY = 1
    SELL = -1
    HOLD = 0

@dataclass
class Trade:
    """单笔交易记录"""
    entry_date: str
    entry_price: float
    exit_date: str = ''
    exit_price: float = 0.0
    shares: int = 0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    holding_days: int = 0
    stop_reason: str = ''

@dataclass
class BacktestResult:
    """回测结果"""
    strategy_name: str
    total_return: float = 0.0
    annual_return: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    avg_holding_days: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)

class PositionManager:
    """仓位管理器"""
    def __init__(self, initial_capital: float = 1000000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.shares = 0
        self.avg_cost = 0.0
        self.equity = initial_capital
        self.peak_equity = initial_capital
        self.max_drawdown = 0.0
        self.equity_history = []
        self.trades: List[Trade] = []
        self.current_trade: Optional[Trade] = None

    def buy(self, date: str, price: float, signal_strength: float = 1.0) -> bool:
        """买入"""
        if self.shares > 0:
            return False
        
        # 按信号强度调整仓位 (0.25 - 1.0)
        position_size = min(1.0, max(0.25, signal_strength))
        amount = self.cash * position_size
        shares = int(amount / price / 100) * 100  # 按100股整数倍
        
        if shares <= 0:
            return False
        
        cost = shares * price
        self.cash -= cost
        self.shares = shares
        self.avg_cost = price
        
        self.current_trade = Trade(
            entry_date=date,
            entry_price=price,
            shares=shares
        )
        return True

    def sell(self, date: str, price: float, reason: str = '') -> bool:
        """卖出"""
        if self.shares <= 0:
            return False
        
        revenue = self.shares * price
        pnl = revenue - self.shares * self.avg_cost
        pnl_pct = (price - self.avg_cost) / self.avg_cost * 100
        
        self.cash += revenue
        self.shares = 0
        self.avg_cost = 0.0
        
        if self.current_trade:
            self.current_trade.exit_date = date
            self.current_trade.exit_price = price
            self.current_trade.pnl = pnl
            self.current_trade.pnl_pct = pnl_pct
            self.current_trade.stop_reason = reason
            self.trades.append(self.current_trade)
            self.current_trade = None
        
        return True

    def update_equity(self, date: str, current_price: float):
        """更新净值"""
        self.equity = self.cash + self.shares * current_price
        if self.equity > self.peak_equity:
            self.peak_equity = self.equity
        drawdown = (self.peak_equity - self.equity) / self.peak_equity * 100
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown
        self.equity_history.append(self.equity)

    def close_all(self, date: str, price: float, reason: str = '回测结束'):
        """平仓所有持仓"""
        if self.shares > 0:
            self.sell(date, price, reason)


class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, df: pd.DataFrame, initial_capital: float = 1000000, 
                 commission_rate: float = 0.0003, slippage: float = 0.0):
        self.df = df.copy()
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate  # 手续费率
        self.slippage = slippage  # 滑点
        
    def run(self, strategy_func: Callable, strategy_name: str, **kwargs) -> BacktestResult:
        """运行回测"""
        pm = PositionManager(self.initial_capital)
        
        for i in range(1, len(self.df)):
            row = self.df.iloc[i]
            prev_row = self.df.iloc[i-1]
            price = row['close']
            date = str(row['trade_date'])
            
            # 获取信号
            signal, strength, stop_loss, take_profit = strategy_func(self.df, i, **kwargs)
            
            # 执行交易
            if signal == Signal.BUY and pm.shares == 0:
                buy_price = price * (1 + self.slippage)
                pm.buy(date, buy_price, strength)
                
            elif signal == Signal.SELL and pm.shares > 0:
                sell_price = price * (1 - self.slippage)
                pm.sell(date, sell_price, '策略信号')
            
            # 止损/止盈检查
            if pm.shares > 0 and (stop_loss or take_profit):
                if stop_loss and price <= pm.avg_cost * (1 - stop_loss):
                    pm.sell(date, price * (1 - self.slippage), f'止损({stop_loss*100:.0f}%)')
                elif take_profit and price >= pm.avg_cost * (1 + take_profit):
                    pm.sell(date, price * (1 - self.slippage), f'止盈({take_profit*100:.0f}%)')
            
            # 更新净值
            pm.update_equity(date, price)
        
        # 回测结束平仓
        last_price = self.df.iloc[-1]['close']
        last_date = str(self.df.iloc[-1]['trade_date'])
        pm.close_all(last_date, last_price, '回测结束')
        
        # 计算结果
        return self._calc_result(pm, strategy_name)
    
    def _calc_result(self, pm: PositionManager, strategy_name: str) -> BacktestResult:
        """计算回测指标"""
        result = BacktestResult(strategy_name=strategy_name)
        result.trades = pm.trades
        
        # 收益
        total_return = (pm.equity_history[-1] - self.initial_capital) / self.initial_capital * 100
        result.total_return = total_return
        
        # 年化收益
        days = len(pm.equity_history)
        annual_return = ((pm.equity_history[-1] / self.initial_capital) ** (252 / max(days, 1)) - 1) * 100
        result.annual_return = annual_return
        
        # 最大回撤
        result.max_drawdown = pm.max_drawdown
        
        # Sharpe Ratio
        daily_returns = pd.Series(pm.equity_history).pct_change().dropna()
        if len(daily_returns) > 1 and daily_returns.std() > 0:
            sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)
            result.sharpe_ratio = sharpe
        
        # 交易统计
        result.total_trades = len(pm.trades)
        winning = [t for t in pm.trades if t.pnl > 0]
        losing = [t for t in pm.trades if t.pnl <= 0]
        result.winning_trades = len(winning)
        result.losing_trades = len(losing)
        result.win_rate = len(winning) / max(len(pm.trades), 1) * 100
        
        if pm.trades:
            result.avg_holding_days = np.mean([t.holding_days for t in pm.trades])
        
        if winning:
            result.avg_win = np.mean([t.pnl_pct for t in winning])
            result.largest_win = max(t.pnl_pct for t in winning)
        
        if losing:
            result.avg_loss = np.mean([t.pnl_pct for t in losing])
            result.largest_loss = min(t.pnl_pct for t in losing)
        
        if winning and losing:
            total_win = sum(t.pnl for t in winning)
            total_loss = abs(sum(t.pnl for t in losing))
            result.profit_factor = total_win / max(total_loss, 1)
        
        result.equity_curve = pm.equity_history
        
        return result


# ========================================
# 策略定义
# ========================================

def strategy_ma_crossover(df, idx, fast=5, slow=20, **kwargs):
    """双均线交叉策略"""
    signal = Signal.HOLD
    strength = 0.5
    stop_loss = None
    take_profit = None
    
    if idx < slow:
        return signal, strength, stop_loss, take_profit
    
    ma_fast_curr = df.iloc[idx][f'ma{fast}']
    ma_slow_curr = df.iloc[idx][f'ma{slow}']
    ma_fast_prev = df.iloc[idx-1][f'ma{fast}']
    ma_slow_prev = df.iloc[idx-1][f'ma{slow}']
    
    # 金叉买入
    if ma_fast_prev <= ma_slow_prev and ma_fast_curr > ma_slow_curr:
        signal = Signal.BUY
        strength = min(1.0, (ma_fast_curr - ma_slow_curr) / ma_slow_curr * 10)
        stop_loss = 0.08  # 8%止损
        take_profit = 0.20  # 20%止盈
    
    # 死叉卖出
    elif ma_fast_prev >= ma_slow_prev and ma_fast_curr < ma_slow_curr:
        signal = Signal.SELL
    
    return signal, strength, stop_loss, take_profit


def strategy_macd(df, idx, **kwargs):
    """MACD金叉/死叉策略"""
    signal = Signal.HOLD
    strength = 0.5
    stop_loss = None
    take_profit = None
    
    if idx < 35:
        return signal, strength, stop_loss, take_profit
    
    dif_curr = df.iloc[idx]['dif']
    dea_curr = df.iloc[idx]['dea']
    dif_prev = df.iloc[idx-1]['dif']
    dea_prev = df.iloc[idx-1]['dea']
    
    # 金叉买入
    if dif_prev <= dea_prev and dif_curr > dea_curr:
        signal = Signal.BUY
        strength = min(1.0, abs(dif_curr) / df.iloc[idx]['close'] * 5)
        stop_loss = 0.10
        take_profit = 0.25
    
    # 死叉卖出
    elif dif_prev >= dea_prev and dif_curr < dea_curr:
        signal = Signal.SELL
    
    return signal, strength, stop_loss, take_profit


def strategy_rsi(df, idx, period=12, oversold=30, overbought=70, **kwargs):
    """RSI超买超卖策略"""
    signal = Signal.HOLD
    strength = 0.5
    stop_loss = None
    take_profit = None
    
    if idx < 30:
        return signal, strength, stop_loss, take_profit
    
    rsi_curr = df.iloc[idx][f'rsi{period}']
    rsi_prev = df.iloc[idx-1][f'rsi{period}']
    
    # 从超卖区反弹买入
    if rsi_prev < oversold and rsi_curr >= oversold:
        signal = Signal.BUY
        strength = min(1.0, (oversold - rsi_prev) / 10)
        stop_loss = 0.08
        take_profit = 0.15
    
    # 从超买区回落卖出
    elif rsi_prev > overbought and rsi_curr <= overbought:
        signal = Signal.SELL
    
    return signal, strength, stop_loss, take_profit


def strategy_kdj(df, idx, **kwargs):
    """KDJ策略"""
    signal = Signal.HOLD
    strength = 0.5
    stop_loss = None
    take_profit = None
    
    if idx < 15:
        return signal, strength, stop_loss, take_profit
    
    k_curr = df.iloc[idx]['k']
    d_curr = df.iloc[idx]['d']
    k_prev = df.iloc[idx-1]['k']
    d_prev = df.iloc[idx-1]['d']
    
    # K上穿D买入（低位金叉更佳）
    if k_prev <= d_prev and k_curr > d_curr and k_curr < 50:
        signal = Signal.BUY
        strength = min(1.0, (50 - k_curr) / 25)
        stop_loss = 0.08
        take_profit = 0.20
    
    # K下穿D卖出（高位死叉）
    elif k_prev >= d_prev and k_curr < d_curr and k_curr > 70:
        signal = Signal.SELL
    
    return signal, strength, stop_loss, take_profit


def strategy_boll(df, idx, **kwargs):
    """布林带策略"""
    signal = Signal.HOLD
    strength = 0.5
    stop_loss = None
    take_profit = None
    
    if idx < 25:
        return signal, strength, stop_loss, take_profit
    
    close = df.iloc[idx]['close']
    upper = df.iloc[idx]['boll_upper']
    lower = df.iloc[idx]['boll_lower']
    mid = df.iloc[idx]['boll_mid']
    
    prev_close = df.iloc[idx-1]['close']
    prev_lower = df.iloc[idx-1]['boll_lower']
    prev_upper = df.iloc[idx-1]['boll_upper']
    
    # 从下轨反弹买入
    if prev_close <= prev_lower and close > lower:
        signal = Signal.BUY
        strength = 0.6
        stop_loss = 0.06
        take_profit = 0.15
    
    # 触及上轨卖出
    elif close >= upper:
        signal = Signal.SELL
    
    return signal, strength, stop_loss, take_profit


def strategy_combined(df, idx, **kwargs):
    """多指标综合策略（需至少2个指标同时确认）"""
    signal = Signal.HOLD
    strength = 0.5
    stop_loss = None
    take_profit = None
    
    if idx < 60:
        return signal, strength, stop_loss, take_profit
    
    buy_signals = 0
    sell_signals = 0
    
    # 1. MA趋势
    ma20 = df.iloc[idx]['ma20']
    ma60 = df.iloc[idx]['ma60']
    close = df.iloc[idx]['close']
    
    if close > ma20 > ma60:
        buy_signals += 0.5
    elif close < ma20 < ma60:
        sell_signals += 0.5
    
    # 2. MACD
    if df.iloc[idx]['dif'] > df.iloc[idx]['dea']:
        buy_signals += 0.5
    else:
        sell_signals += 0.5
    
    # 3. RSI
    rsi = df.iloc[idx]['rsi12']
    if rsi < 40:
        buy_signals += 1.0  # RSI低位加分
    elif rsi > 75:
        sell_signals += 1.0  # RSI高位加分
    
    # 4. KDJ
    if df.iloc[idx]['k'] > df.iloc[idx]['d'] and df.iloc[idx]['k'] < 50:
        buy_signals += 0.5
    elif df.iloc[idx]['k'] < df.iloc[idx]['d'] and df.iloc[idx]['k'] > 70:
        sell_signals += 0.5
    
    # 综合判断
    if buy_signals >= 2.0:
        signal = Signal.BUY
        strength = min(1.0, buy_signals / 3.0)
        stop_loss = 0.08
        take_profit = 0.20
    
    elif sell_signals >= 2.0:
        signal = Signal.SELL
    
    return signal, strength, stop_loss, take_profit


def strategy_atr_trailing(df, idx, atr_mult=3.0, **kwargs):
    """ATR跟踪止损策略"""
    signal = Signal.HOLD
    strength = 0.5
    stop_loss = None
    take_profit = None
    
    if idx < 60:
        return signal, strength, stop_loss, take_profit
    
    close = df.iloc[idx]['close']
    ma20 = df.iloc[idx]['ma20']
    ma60 = df.iloc[idx]['ma60']
    atr = df.iloc[idx]['atr']
    
    # 趋势向上时买入
    if close > ma20 > ma60:
        signal = Signal.BUY
        strength = min(1.0, (close - ma60) / ma60 * 5)
        stop_loss = atr_mult * atr / close  # ATR倍数止损
        take_profit = atr_mult * 2 * atr / close  # 2倍ATR止盈
    
    return signal, strength, stop_loss, take_profit


if __name__ == '__main__':
    print("量化回测引擎已加载，支持7种策略")
    print("运行 run_backtest.py 执行完整回测")
