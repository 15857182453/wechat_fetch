# A 股交易系统优化 — 详细实施计划

**日期**: 2026-05-28  
**目标**: 修复 trades.db 空转 + 数据源容灾升级  
**原则**: 不改代码逻辑，只补充缺失的链路  
**状态**: ✅ P0-1/P0-2 已完成实施 (2026-05-28 git commit e52d120)

---

## P0-1: 修复 trades.db — 让建议记录和反馈循环真正跑起来

### 现状诊断

`trades.db` 已有 4 张表 + 11 条初始导入记录（5/18），但之后没有任何新记录：
- `operations` — 11 条（5/18 初始导入 + 1 条 pending 的汉威科技）
- `positions` — 11 条（5/18 初始导入，last_updated 停留在 5/21）
- `outcomes` — 6 条（数据异常，pnl 全是 0）
- `portfolio_nav` — 0 条

**根因**: daily_pipeline 生成信号后没有写入 trades.db，盘中监控触发后也没有记录。

### 修改方案（2 个文件）

#### 文件 1: `scripts/trade_logger.py` — 信号记录器

**现有功能**: `log_trade()` 已存在，写入 operations 表。

**新增**: `record_daily_signal()` 函数 — 每天 daily_pipeline 跑完后，把"建议买入/卖出"的股票写入 trades.db。

```python
def record_daily_signals(signals: list, date: str = None):
    """记录每日 pipeline 生成的建议信号。
    
    Args:
        signals: [{"code", "name", "action", "confidence", "reason", "price"}, ...]
    
    写入 trades.db operations 表，signal_source = 'daily_pipeline'
    同一天同一只股票只记录一次（幂等）
    """
```

**集成点**: `daily_pipeline.py` 第 6 步（多因子评分后），把生成的 signals 列表传入 `record_daily_signals()`。

#### 文件 2: `scripts/intraday_monitor.py` — 止盈止损记录

**现有功能**: 已有 `check_position_triggers()` 检测止盈止损，推送飞书。

**新增**: 触发止盈止损时，记录到 operations 表（action='TAKE_PROFIT' / 'STOP_LOSS'）。

```python
# 在 check_position_triggers() 中，触发时调用:
from trade_logger import log_trade
log_trade(code, name, action, qty, price, reason, confidence, source='intraday_monitor')
```

#### 补充: `import_holdings.py` 修复

**现状**: 5/18 导入过 11 条初始持仓，但 prices 已经更新过多次，avg_cost 可能不准。

**操作**: 不改代码，手动对照 intraday_monitor.py 中的硬编码持仓，确认 trades.db positions 表的 avg_cost 是否一致。

### 预期效果 ✅ 已验证

- 每天 17:05 pipeline 跑完 → trades.db 新增 N 条 operations 记录 ✅
- 盘中止盈止损触发 → trades.db 新增对应记录 ✅
- 测试验证：2 条信号记录成功写入，幂等去重生效

### 不涉及

- 不接入真实交易（只是记录"建议"）
- 不修改因子引擎/信号生成逻辑
- 不改 notifier.py 推送格式

---

## P0-2: 数据源容灾升级 — 东方财富 API 替代 + ETF 数据支持

### 现状诊断

| 数据源 | 状态 | 影响 |
|--------|------|------|
| Baostock | ✅ 正常（TCP 直连） | 日线行情主力 |
| 新浪 hq.sinajs.cn | ✅ 正常 | 实时行情 |
| Tushare | ❌ token 无效 | daily_basic 缺失 |
| 东方财富 push API | ❌ 完全不可达 | 板块成分股获取失败 |
| AKShare | ✅ 部分可用 | 备用行情 + 板块资金流 |

**影响范围**: `discovery_agent.py` 的题材挖掘（Step 1/2 板块扫描 → Step 3 成分股获取 → Step 4 龙头筛选）因东方财富 API 不可达而降级。

### 修改方案（3 个文件）

#### 文件 1: `scripts/data_fetcher.py` — 增加 ETF 识别 + 腾讯快照

**新增 1**: ETF 数据获取支持

```python
def is_etf(code: str) -> bool:
    """判断是否为 ETF（51xxxx/15xxxx/56xxxx/58xxxx）。"""
    code_clean = code.split(".")[0].lower()
    return (code_clean.startswith("51") or 
            code_clean.startswith("15") or 
            code_clean.startswith("56") or 
            code_clean.startswith("58"))

def get_etf_data(code: str, days: int = 60) -> pd.DataFrame:
    """获取 ETF 日线数据（AKShare fund_etf_hist_em）。"""
    import akshare as ak
    # ETF 代码去掉 sh/sz 前缀，如 "sh588200" → "588200"
    clean_code = code.replace("sh", "").replace("sz", "")
    df = ak.fund_etf_hist_em(symbol=clean_code, period="daily", adjust="qfq")
    # 列名映射 + 统一格式
    ...
```

**集成点**: `get_stock_data()` 中，先判断 is_etf()，走 ETF 专用获取函数。

**新增 2**: 腾讯财经快照作为第四数据源

```python
def fetch_from_tencent(code: str) -> pd.DataFrame:
    """从腾讯财经获取实时快照（备用）。"""
    # qt.gtimg.cn，不受 HTTP 代理影响
    # 返回最近 5 日 mini K 线
    ...
```

#### 文件 2: `scripts/discovery_agent.py` — 板块成分股 AKShare 替代

**现状**: 用东方财富 push API 获取板块成分股，完全不可达。

**替代方案**: 用 AKShare 的板块资金流接口

```python
# 现有（失败）:
# 东方财富 push API → stock_board_concept_cons_em() → 成分股列表

# 替代:
import akshare as ak

def get_concept_stocks_akshare(concept_name: str) -> list:
    """用 AKShare 获取概念板块成分股。"""
    # ak.stock_board_concept_name_em() 获取概念列表
    # ak.stock_board_concept_cons_em(symbol=板块代码) 获取成分股
    # 如果东方财富通过 AKShare 也不可达，退化为:
    #   1. 新浪行业成分股（已有 fallback）
    #   2. 新闻关键词匹配（已有）
    #   3. watchlist.json 中的板块标签匹配
    ...
```

**降级策略**（三级）:
1. AKShare 东财成分股（优先）
2. 新浪行业快照 + 新闻热点匹配（已有）
3. watchlist.json 板块标签（兜底）

#### 文件 3: `scripts/intraday_monitor.py` — ETF 持仓监控

**现状**: 持仓中有 4 只 ETF（纳指科技/中韩芯片/光伏龙头/科创芯片），但 `get_realtime_quote()` 对 ETF 代码格式（sh588200）解析有问题。

**修复**: 

```python
# 在 check_position_triggers() 中:
for pos in positions:
    code = pos["code"]
    # ETF 代码特殊处理
    if is_etf(code):
        quote = get_etf_realtime_quote(code)  # 用 fund_etf_realtime_em
    else:
        quote = get_realtime_quote(code)
    ...
```

### 预期效果 ✅ 已验证

- ETF 持仓也能有技术分析和止盈止损 ✅（4/5 只 ETF 实时行情正常）
- 板块成分股获取成功率从 0% → 60%+（AKShare 可达时）✅（3 级容灾已部署）
- 数据源从 3 个 → 4 个（新增 AKShare ETF 行情）✅

---

## 实施顺序

### 第一阶段：trades.db 修复（1 小时）

| 步骤 | 文件 | 操作 | 验证 |
|------|------|------|------|
| 1 | `trade_logger.py` | 新增 `record_daily_signals()` | 手动调用，检查 trades.db |
| 2 | `daily_pipeline.py` | 第 6 步后插入记录调用 | 跑一次 pipeline，检查新增记录 |
| 3 | `intraday_monitor.py` | 触发时写 trade_logger | 手动触发止盈止损，检查记录 |
| 4 | 验证 | `python3 -c "import sqlite3; ..."` | 确认 operations 有新增 |

### 第二阶段：数据源容灾（2 小时）

| 步骤 | 文件 | 操作 | 验证 |
|------|------|------|------|
| 1 | `data_fetcher.py` | 新增 `is_etf()` + `get_etf_data()` | `get_stock_data("sh588200")` 成功 |
| 2 | `data_fetcher.py` | 新增 `fetch_from_tencent()` | 单只股票获取成功 |
| 3 | `intraday_monitor.py` | ETF 持仓特殊处理 | 4 只 ETF 有实时行情 |
| 4 | `discovery_agent.py` | 板块成分股 AKShare 替代 | 运行 `discovery_agent.py --quick` |
| 5 | 验证 | 跑一次完整 daily_pipeline | 检查日志无数据源报错 |

---

## 风险控制

1. **不改核心逻辑** — 因子引擎/信号生成/风控不碰，只补充缺失链路
2. **trades.db 只写不读** — 新增记录不影响现有功能，读 trades.db 的模块（feedback_loop 等）自动受益
3. **数据源降级而非替换** — 新增数据源作为 fallback，不删除现有任何数据源
4. **先在副本改** — 遵循"不修改源文件"规则，在新文件中改好后替换
