#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对账业务总表导入脚本（健壮版）
- 自动检测数据单位（元/万元）
- 数据范围验证
- 自动去重更新
- 详细的错误报告

作者：OpenClaw
最后更新：2026-04-08
"""

import pandas as pd
import sqlite3
import os
import sys
from datetime import datetime

# ========== 配置 ==========
DB_PATH = '/home/openclaw/.openclaw/workspace/business_flow.db'
TABLE_NAME = 'duizhang_summary_2026'
WORKSPACE = '/home/openclaw/.openclaw/workspace/'

# 数据验证阈值（万元）
MIN_DAILY_FLOW = 0.1      # 最小日流水：1000 元
MAX_DAILY_FLOW = 10000    # 最大日流水：10 亿元
MIN_RATIO = -10.0         # 最小环比：-1000%（Excel 中是比率，-10 = -1000%）
MAX_RATIO = 100.0         # 最大环比：+10000%
# =========================


def find_excel_file():
    """查找新流水 2026.xlsx 文件（排除临时文件）"""
    for f in os.listdir(WORKSPACE):
        if f.startswith('新流水') and '2026' in f and f.endswith('.xlsx') and not f.startswith('~$'):
            return os.path.join(WORKSPACE, f)
    raise FileNotFoundError("找不到新流水 2026.xlsx 文件")


def detect_unit(df, column_name, sample_row=4):
    """
    检测数据列的单位（元或万元）
    
    判断逻辑：
    - 如果值 > 10000，很可能是"元"
    - 如果值 < 10000，很可能是"万元"
    """
    sample_value = df.iloc[sample_row][column_name]
    if pd.isna(sample_value):
        return 'unknown'
    
    if sample_value > 10000:
        return '元'
    elif sample_value < 100:
        return '万元'
    else:
        # 边界情况，打印警告
        print(f"⚠️  警告：{column_name} 列的样本值 {sample_value} 在边界范围，假设为'元'")
        return '元'


def validate_record(row, date_str):
    """验证单条记录的数据合理性"""
    errors = []
    
    daily_flow = row.get('daily_total_flow', 0)
    if daily_flow < MIN_DAILY_FLOW:
        errors.append(f"日流水 {daily_flow:.4f}万 < 最小值 {MIN_DAILY_FLOW}万")
    elif daily_flow > MAX_DAILY_FLOW:
        errors.append(f"日流水 {daily_flow:.4f}万 > 最大值 {MAX_DAILY_FLOW}万")
    
    ratio = row.get('daily_flow_ratio', 0)
    if ratio < MIN_RATIO:
        errors.append(f"环比 {ratio:.2%} < 最小值 {MIN_RATIO:.0%}")
    elif ratio > MAX_RATIO:
        errors.append(f"环比 {ratio:.2%} > 最大值 {MAX_RATIO:.0%}")
    
    # 检查各分项之和是否接近总计（允许 1% 误差）
    sub_items = [
        row.get('ywul_class_flow', 0),
        row.get('chufang_flow', 0),
        row.get('tiujian_flow', 0),
        row.get('jianguan_flow', 0),
        row.get('disanfang_flow', 0),
        row.get('xinli_flow', 0),
        row.get('zhifu_flow', 0),
        row.get('yuancheng_flow', 0),
        row.get('huiyuan_flow', 0),
        row.get('disanfang_tj_flow', 0),
        row.get('shangcheng_flow', 0),
    ]
    sub_total = sum(sub_items)
    if sub_total > 0 and daily_flow > 0:
        diff = abs(sub_total - daily_flow) / daily_flow
        if diff > 0.01:  # 1% 误差
            errors.append(f"分项之和 {sub_total:.2f}万 与总计 {daily_flow:.2f}万 差异 {diff:.1%}")
    
    return errors


def import_data():
    """主导入函数"""
    print("=" * 70)
    print("📊 对账业务总表导入（健壮版）")
    print("=" * 70)
    print()
    
    # 查找文件
    excel_file = find_excel_file()
    print(f"📁 Excel 文件：{excel_file}")
    
    # 读取数据
    print("📖 读取 Excel...")
    df = pd.read_excel(excel_file, header=None, skiprows=4)
    print(f"   读取到 {len(df):,} 行")
    
    # 重命名列
    df.columns = [
        '日期', '咨询流水', '咨询订单', '处方流水', '处方订单', 
        '体检流水', '体检订单', '健管流水', '健管订单',
        '第三方流水', '第三方订单', '心理流水', '心理订单',
        '支付流水', '支付订单', '远程流水', '远程订单',
        '会员流水', '会员订单', '第三方体检流水', '第三方体检订单',
        '商城流水', '商城订单',
        '日总流水', '日流水增量', '日流水环比', 'extra1', 'extra2'
    ]
    
    # 清理数据
    df = df[df['日期'].notna()]
    df = df[df['日期'] != '总计']
    df['日期'] = pd.to_datetime(df['日期'], errors='coerce')
    df = df[df['日期'].notna()]
    df['日期'] = df['日期'].dt.strftime('%Y-%m-%d')
    
    print(f"   有效数据：{len(df)} 天")
    print()
    
    # 检测单位
    print("🔍 检测数据单位...")
    unit = detect_unit(df, '日总流水')
    print(f"   日总流水单位：{unit}")
    
    if unit == '元':
        print("   ✅ 将自动转换为万元")
        conversion_factor = 10000
    elif unit == '万元':
        print("   ✅ 单位正确，无需转换")
        conversion_factor = 1
    else:
        print("   ⚠️  无法确定单位，假设为'元'")
        conversion_factor = 10000
    
    print()
    
    # 构建记录
    print("💾 处理数据...")
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    records = []
    validation_errors = []
    
    for idx, row in df.iterrows():
        record = {
            'date': row['日期'],
            # 所有流水列：元 → 万元
            'ywul_class_flow': float(row['咨询流水']) / conversion_factor if pd.notna(row['咨询流水']) else 0.0,
            'ywul_class_orders': int(row['咨询订单']) if pd.notna(row['咨询订单']) else 0,
            'chufang_flow': float(row['处方流水']) / conversion_factor if pd.notna(row['处方流水']) else 0.0,
            'chufang_orders': int(row['处方订单']) if pd.notna(row['处方订单']) else 0,
            'tiujian_flow': float(row['体检流水']) / conversion_factor if pd.notna(row['体检流水']) else 0.0,
            'tiujian_orders': int(row['体检订单']) if pd.notna(row['体检订单']) else 0,
            'jianguan_flow': float(row['健管流水']) / conversion_factor if pd.notna(row['健管流水']) else 0.0,
            'jianguan_orders': int(row['健管订单']) if pd.notna(row['健管订单']) else 0,
            'disanfang_flow': float(row['第三方流水']) / conversion_factor if pd.notna(row['第三方流水']) else 0.0,
            'disanfang_orders': int(row['第三方订单']) if pd.notna(row['第三方订单']) else 0,
            'xinli_flow': float(row['心理流水']) / conversion_factor if pd.notna(row['心理流水']) else 0.0,
            'xinli_orders': int(row['心理订单']) if pd.notna(row['心理订单']) else 0,
            'zhifu_flow': float(row['支付流水']) / conversion_factor if pd.notna(row['支付流水']) else 0.0,
            'zhifu_orders': int(row['支付订单']) if pd.notna(row['支付订单']) else 0,
            'yuancheng_flow': float(row['远程流水']) / conversion_factor if pd.notna(row['远程流水']) else 0.0,
            'yuancheng_orders': int(row['远程订单']) if pd.notna(row['远程订单']) else 0,
            'huiyuan_flow': float(row['会员流水']) / conversion_factor if pd.notna(row['会员流水']) else 0.0,
            'huiyuan_orders': int(row['会员订单']) if pd.notna(row['会员订单']) else 0,
            'disanfang_tj_flow': float(row['第三方体检流水']) / conversion_factor if pd.notna(row['第三方体检流水']) else 0.0,
            'disanfang_tj_orders': int(row['第三方体检订单']) if pd.notna(row['第三方体检订单']) else 0,
            'shangcheng_flow': float(row['商城流水']) / conversion_factor if pd.notna(row['商城流水']) else 0.0,
            'shangcheng_orders': int(row['商城订单']) if pd.notna(row['商城订单']) else 0,
            'daily_total_flow': float(row['日总流水']) / conversion_factor if pd.notna(row['日总流水']) else 0.0,
            'daily_flow_increment': float(row['日流水增量']) / conversion_factor if pd.notna(row['日流水增量']) else 0.0,
            'daily_flow_ratio': float(row['日流水环比']) if pd.notna(row['日流水环比']) else 0.0,
            'created_at': now
        }
        
        # 验证
        errors = validate_record(record, record['date'])
        if errors:
            for err in errors:
                validation_errors.append(f"{record['date']}: {err}")
        
        records.append(record)
        
        if (idx + 1) % 20 == 0:
            print(f"   已处理 {idx + 1:,}/{len(df):,} 行...")
    
    # 报告验证错误
    if validation_errors:
        print()
        print("⚠️  数据验证警告:")
        for err in validation_errors[:10]:  # 只显示前 10 条
            print(f"   - {err}")
        if len(validation_errors) > 10:
            print(f"   ... 还有 {len(validation_errors) - 10} 条警告")
        print()
    
    print()
    
    # 连接数据库
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 检查重复
    cursor.execute(f"SELECT date, COUNT(*) FROM {TABLE_NAME} GROUP BY date HAVING COUNT(*) > 1")
    duplicates = cursor.fetchall()
    if duplicates:
        print(f"⚠️  发现 {len(duplicates)} 个重复日期，将自动更新...")
    
    # 插入数据
    insert_sql = f"""
    INSERT OR REPLACE INTO {TABLE_NAME} (
        date, ywul_class_flow, ywul_class_orders, chufang_flow, chufang_orders,
        tiujian_flow, tiujian_orders, jianguan_flow, jianguan_orders,
        disanfang_flow, disanfang_orders, xinli_flow, xinli_orders,
        zhifu_flow, zhifu_orders, yuancheng_flow, yuancheng_orders,
        huiyuan_flow, huiyuan_orders, disanfang_tj_flow, disanfang_tj_orders,
        shangcheng_flow, shangcheng_orders, daily_total_flow,
        daily_flow_increment, daily_flow_ratio, created_at
    ) VALUES (
        :date, :ywul_class_flow, :ywul_class_orders, :chufang_flow, :chufang_orders,
        :tiujian_flow, :tiujian_orders, :jianguan_flow, :jianguan_orders,
        :disanfang_flow, :disanfang_orders, :xinli_flow, :xinli_orders,
        :zhifu_flow, :zhifu_orders, :yuancheng_flow, :yuancheng_orders,
        :huiyuan_flow, :huiyuan_orders, :disanfang_tj_flow, :disanfang_tj_orders,
        :shangcheng_flow, :shangcheng_orders, :daily_total_flow,
        :daily_flow_increment, :daily_flow_ratio, :created_at
    )
    """
    
    # 先获取已有日期
    cursor.execute(f"SELECT date FROM {TABLE_NAME}")
    existing_dates = set(row[0] for row in cursor.fetchall())
    
    # 只导入新日期（增量模式）
    new_records = [r for r in records if r['date'] not in existing_dates]
    
    if not new_records:
        print("ℹ️  没有新数据需要导入（所有日期已存在）")
        print(f"📊 数据库现有 {len(existing_dates)} 条记录")
        conn.close()
        return
    
    # 插入新记录
    cursor.executemany(insert_sql, new_records)
    conn.commit()
    
    print(f"➕ 新增 {len(new_records)} 条记录")
    print(f"📊 数据库现有 {len(existing_dates) + len(new_records)} 条记录")
    
    # 显示新增的日期
    print("\n📅 新增日期:")
    for r in sorted(new_records, key=lambda x: x['date']):
        print(f"   {r['date']}: 总计¥{r['daily_total_flow']:.2f}万")
    
    # 删除未来日期的空数据（可选，一般不需要）
    # cursor.execute(f"""
    # DELETE FROM {TABLE_NAME}
    # WHERE date >= date('now') AND daily_total_flow = 0
    # """)
    # deleted = cursor.rowcount
    # if deleted > 0:
    #     print(f"🗑️  删除 {deleted} 条未来日期的空记录")
    # conn.commit()
    
    # 验证结果
    print()
    print("📊 验证导入结果...")
    cursor.execute(f'SELECT COUNT(*) FROM {TABLE_NAME}')
    total = cursor.fetchone()[0]
    print(f"   表中总记录数：{total:,} 条")
    
    cursor.execute(f'SELECT MIN(date), MAX(date) FROM {TABLE_NAME}')
    min_date, max_date = cursor.fetchone()
    print(f"   日期范围：{min_date} ~ {max_date}")
    
    cursor.execute(f'SELECT SUM(daily_total_flow) FROM {TABLE_NAME}')
    total_flow = cursor.fetchone()[0]
    print(f"   累计流水：¥{total_flow:,.2f}万元")
    
    # 显示最新 7 天
    print()
    print("📋 最新 7 天数据:")
    cursor.execute(f'''
    SELECT date, daily_total_flow, chufang_flow, ywul_class_flow
    FROM {TABLE_NAME}
    ORDER BY date DESC
    LIMIT 7
    ''')
    for row in cursor.fetchall():
        print(f"  {row[0]}: 总计¥{row[1]:.2f}万，处方¥{row[2]:.2f}万，咨询¥{row[3]:.2f}万")
    
    conn.close()
    
    print()
    print("=" * 70)
    print("✅ 数据导入完成！")
    print("=" * 70)
    print()


if __name__ == '__main__':
    try:
        import_data()
    except Exception as e:
        print(f"\n❌ 导入失败：{e}")
        sys.exit(1)
