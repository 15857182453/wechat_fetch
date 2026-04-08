#!/usr/bin/env python3
"""
多医院微信公众号数据抓取 + GrowingIO 自动上报
通过配置文件批量处理多个医院的数据

使用方法:
    python3 run_hospitals.py              # 执行所有医院（默认最近7天）
    python3 run_hospitals.py --days 14    # 执行所有医院最近14天
    python3 run_hospitals.py --hospital "医院1名称"  # 指定医院
    python3 run_hospitals.py --start 2026-03-01 --end 2026-03-30  # 指定日期范围
    python3 run_hospitals.py --dry-run    # 仅抓取不上传

配置文件: hospitals.yml
"""

import yaml
import os
import sys
import datetime
import subprocess
import json
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = "/home/openclaw/.openclaw/workspace"

def load_config(config_path):
    """加载医院配置文件"""
    # 支持绝对路径和相对路径
    if os.path.isabs(config_path):
        full_path = config_path
    else:
        # 相对路径相对于 SCRIPT_DIR
        full_path = os.path.join(SCRIPT_DIR, config_path)
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"❌ 配置文件未找到: {full_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"❌ 配置文件格式错误: {e}")
        sys.exit(1)

def run_single_hospital(hospital_config, args):
    """为单个医院执行数据抓取"""
    hospital_name = hospital_config['name']
    output_dir = hospital_config.get('output_dir', 'logs')
    hospital_logs_dir = os.path.join(WORKSPACE_DIR, output_dir, 'logs')
    
    # 确保日志目录存在
    os.makedirs(hospital_logs_dir, exist_ok=True)
    
    print(f"\n{'='*60}")
    print(f"🏥 开始处理: {hospital_name}")
    print(f"📊 输出目录: {output_dir}")
    print(f"{'='*60}")
    
    # 构建命令参数
    config_json = json.dumps(hospital_config, ensure_ascii=False)
    
    cmd_args = [
        sys.executable,
        os.path.join(SCRIPT_DIR, "templates", "wechat_fetch_hospital.py"),
        "--config", config_json,
    ]
    
    # 日期范围参数
    if hasattr(args, 'today') and args.today:
        cmd_args.append("--today")
    elif args.start and args.end:
        cmd_args.extend(["--start", args.start, "--end", args.end])
    elif args.days:
        cmd_args.extend(["--days", str(args.days)])
    else:
        # 默认使用配置中的默认值或7天
        cmd_args.extend(["--days", str(args.days)])
    
    # dry-run 参数
    if args.dry_run:
        cmd_args.append("--dry-run")
    
    if args.debug:
        cmd_args.append("--debug")
    
    try:
        result = subprocess.run(cmd_args, cwd=SCRIPT_DIR)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ {hospital_name} 执行失败: {e}")
        return False

def send_summary_notification(success_count, fail_count, total_count, dry_run=False):
    """发送汇总通知"""
    markdown_content = f"""# 📊 多医院微信数据抓取汇总
    
## 📈 执行统计
**✅ 成功: {success_count}**
**❌ 失败: {fail_count}**
**🏥 总计: {total_count}**

## 📅 执行时间
**{datetime.date.today().strftime('%Y年%m月%d日')}**

## ⚙️ 执行模式
**{'Dry-run 模式（仅抓取不上传）' if dry_run else '正常模式'}**"""

    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": "📊 多医院微信数据抓取汇总",
            "text": markdown_content
        }
    }
    
    print(f"\n🔔 汇总通知已生成")

def main():
    parser = argparse.ArgumentParser(
        description="多医院微信公众号数据抓取 + GrowingIO 自动上报",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
配置文件: hospitals.yml
示例:
  python3 run_hospitals.py              # 执行所有医院（默认最近7天）
  python3 run_hospitals.py --days 30    # 执行所有医院最近30天
  python3 run_hospitals.py --hospital "医院1名称"  # 指定医院
  python3 run_hospitals.py --start 2026-03-01 --end 2026-03-30  # 指定日期范围
  python3 run_hospitals.py --today      # 抓取今天的数据
  python3 run_hospitals.py --dry-run    # 仅抓取不上传
        """
    )
    
    parser.add_argument("--config", default="hospitals.yml", help="配置文件路径（相对于脚本目录）")
    parser.add_argument("--days", type=int, default=30, help="抓取最近N天")
    parser.add_argument("--start", type=str, help="开始日期 YYYY-MM-DD")
    parser.add_argument("--end", type=str, help="结束日期 YYYY-MM-DD")
    parser.add_argument("--today", action="store_true", help="仅抓取今天")
    parser.add_argument("--dry-run", action="store_true", help="仅抓取不上报")
    parser.add_argument("--debug", action="store_true", help="调试模式")
    parser.add_argument("--hospital", type=str, help="指定医院名称（不指定则全部执行）")
    
    args = parser.parse_args()
    
    # 验证日期参数
    if args.start and args.end:
        try:
            datetime.datetime.strptime(args.start, "%Y-%m-%d")
            datetime.datetime.strptime(args.end, "%Y-%m-%d")
        except ValueError:
            print("❌ 日期格式错误，请使用 YYYY-MM-DD 格式")
            sys.exit(1)
    
    # 加载配置
    print(f"📋 加载配置文件: {args.config}")
    config = load_config(args.config)
    
    # 确定执行的医院列表
    hospitals = config.get('hospitals', [])
    
    if args.hospital:
        hospitals = [h for h in hospitals if h['name'] == args.hospital]
        if not hospitals:
            print(f"❌ 未找到医院: {args.hospital}")
            print(f"   可选医院: {[h['name'] for h in config.get('hospitals', [])]}")
            return
        print(f"🎯 指定执行: {args.hospital}")
    else:
        print(f"📋 共 {len(hospitals)} 家医院待处理")
    
    # 执行每个医院
    success_count = 0
    fail_count = 0
    
    for i, hospital in enumerate(hospitals, 1):
        print(f"\n[{i}/{len(hospitals)}] ")
        if run_single_hospital(hospital, args):
            success_count += 1
        else:
            fail_count += 1
    
    # 汇总报告
    print(f"\n{'='*60}")
    print(f"📊 执行汇总")
    print(f"{'='*60}")
    print(f"✅ 成功: {success_count}")
    print(f"❌ 失败: {fail_count}")
    print(f"🏥 总计: {len(hospitals)}")
    
    # 发送汇总通知
    send_summary_notification(success_count, fail_count, len(hospitals), args.dry_run)

if __name__ == "__main__":
    main()
