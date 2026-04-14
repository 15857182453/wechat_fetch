import pandas as pd
import sqlite3
import time

# 读取底库数据
file_path = "/home/openclaw/.openclaw/workspace/业务对账统计30天明细.xlsx"
print("开始读取底库文件...")
df = pd.read_excel(file_path)
print(f"读取完成，行数: {len(df)}, 列数: {len(df.columns)}")

# 删除旧表（如果存在）以重新导入
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("DROP TABLE IF EXISTS daily_flow_30day")
conn.close()

# 连接数据库
db_path = "/home/openclaw/.openclaw/workspace/business_flow.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 创建新表
print("创建数据表...")
cursor.execute('''
CREATE TABLE IF NOT EXISTS daily_flow_30day (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT,
    trans_no TEXT,
    refund_batch_no TEXT,
    biz_order_no TEXT,
    pay_method TEXT,
    pay_status TEXT,
    institution TEXT,
    institution_code TEXT,
    province TEXT,
    oper_person TEXT,
    ye_wu_lei_mu TEXT,
    ye_wu_zi_lei_mu TEXT,
    yewu_leixing TEXT,
    yewu_wancheng_shijian TEXT,
    caiwu_ruzhang_shijian TEXT,
    shoukuan_shanghu TEXT,
    order_amount REAL,
    amount REAL,
    created_at TEXT
)
''')

# 插入数据
print("开始插入数据...")
start_time = time.time()

# 转换列名匹配现有表结构
df['业务完成时间'] = pd.to_datetime(df['业务完成时间'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
df['财务入账时间'] = pd.to_datetime(df['财务入账时间'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
df['交易时间'] = pd.to_datetime(df['交易时间'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')

# 插入数据
for i, row in df.iterrows():
    cursor.execute('''
        INSERT INTO daily_flow_30day 
        (order_id, trans_no, refund_batch_no, biz_order_no, pay_method, pay_status, 
         institution, institution_code, province, oper_person, ye_wu_lei_mu, 
         ye_wu_zi_lei_mu, yewu_leixing, yewu_wancheng_shijian, caiwu_ruzhang_shijian,
         shoukuan_shanghu, order_amount, amount, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        str(row['商户订单号']) if pd.notna(row['商户订单号']) else None,
        str(row['交易流水号']) if pd.notna(row['交易流水号']) else None,
        str(row['退费批次号']) if pd.notna(row['退费批次号']) else None,
        str(row['业务订单号']) if pd.notna(row['业务订单号']) else None,
        str(row['支付方式/账号']) if pd.notna(row['支付方式/账号']) else None,
        str(row['收退标识']) if pd.notna(row['收退标识']) else None,
        str(row['机构名称']) if pd.notna(row['机构名称']) else None,
        str(row['机构编码']) if pd.notna(row['机构编码']) else None,
        str(row['所在省份']) if pd.notna(row['所在省份']) else None,
        str(row['运营负责人']) if pd.notna(row['运营负责人']) else None,
        str(row['业绩类目']) if pd.notna(row['业绩类目']) else None,
        str(row['业绩子类目']) if pd.notna(row['业绩子类目']) else None,
        str(row['业务类型']) if pd.notna(row['业务类型']) else None,
        str(row['业务完成时间']) if pd.notna(row['业务完成时间']) else None,
        str(row['财务入账时间']) if pd.notna(row['财务入账时间']) else None,
        str(row['收款商户']) if pd.notna(row['收款商户']) else None,
        float(row['订单金额']) if pd.notna(row['订单金额']) else None,
        float(row['实际支付金额']) if pd.notna(row['实际支付金额']) else None,
        str(row['交易时间']) if pd.notna(row['交易时间']) else None,
    ))

conn.commit()
print(f"插入完成，耗时: {time.time() - start_time:.2f}秒")

# 检查插入结果
cursor.execute("SELECT COUNT(*) FROM daily_flow_30day")
count = cursor.fetchone()[0]
print(f"数据库总行数: {count}")

conn.close()
print("导入完成！")
