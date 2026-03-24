#!/usr/bin/env python3
"""
手动触发微信公众号数据上传
关键词：公众号数据上传
"""

import subprocess
import sys
import os

def run_upload():
    """执行数据上传"""
    script_dir = "/home/openclaw/.openclaw/workspace/media-crawler"
    cmd = [
        "/usr/bin/python3",
        os.path.join(script_dir, "wechat_fetch.py"),
        "--start", "2026-02-14",
        "--end", "2026-02-14"
    ]
    
    print("🚀 开始运行数据上传...")
    print(f"📅 日期范围：2026-02-14 至 2026-02-14")
    print()
    
    try:
        result = subprocess.run(cmd, capture_output=False, text=True, cwd=script_dir)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ 错误：{e}")
        return False

if __name__ == "__main__":
    run_upload()
