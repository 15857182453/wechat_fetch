# Tushare Token 配置说明

## 当前状态

- ✅ 已安装 `tushare-finance` skill
- ✅ 已安装依赖 `pandas`, `tushare`
- ⚠️ Token 已接收但需要解密

## Token 已接收

Token (加密): `bd3bf56165eb9bc565b12453f183d7d05c8957268180a6d4f8594f50`

## 下一步操作

### 方案1：用户自行配置 Token (推荐)

1. 访问 https://tushare.pro 注册账号
2. 获取合法的 Token
3. 配置环境变量：
   ```bash
   echo 'export TUSHARE_TOKEN="你的合法Token"' >> ~/.bashrc
   source ~/.bashrc
   ```

### 方案2：提供解密方法

如果 Token 是通过某种加密算法生成的，请提供解密方法或明文 Token。

### 测试配置

配置好 Token 后测试：
```bash
cd /home/openclaw/.openclaw/workspace/skills/tushare-finance
python3 -c "from scripts.api_client import TushareAPI; api = TushareAPI(); df = api.get_stock_daily('000001.SZ', '2024-01-01', '2024-12-31'); print(df.head())"
```

## 错误说明

当前错误：`您没有接口访问权限`

这通常意味着：
- Token 无效或已过期
- Token 所在账号没有开通相关接口权限
- Token 需要解密才能使用

## 支持的接口

基于配置的 Token 权限，可能需要开通：
- 日线行情 (daily)
- 股票列表 (stock_basic)
- 财务指标 (fina_indicator)
- 利润表 (income)
- 指数行情 (index_daily)

## 技术支持

- Tushare 文档: https://tushare.pro/document/2
- 接口权限说明: https://tushare.pro/document/1?doc_id=108
