#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
纳里健康对账报表 API 自动导出（完整版）
使用 AES 加密/解密，无需浏览器
"""

import requests
import json
import os
import base64
import hashlib
import uuid
import time
from datetime import datetime, timedelta
from Crypto.Cipher import AES

# ================= 配置 =================
CONFIG = {
    'api_url': 'https://yypt.ngarihealth.com/ehealth-opbase/openapi/gateway',
    'session_id': '11c884d6-56c3-40b1-b76a-d15c895b729b',
    'csrf_tk': '851915b0-de1e-4755-833f-f8adf1605fb4164238428',
    'aes_key': 'ms4gxansxo459uom',  # 从工具中提取的密钥
    'ca_key': 'ngari-eeop',
    'download_dir': '/mnt/c/Users/44238/Desktop/业务对账数据/自动导出',
}
# ===========================================

class AESCipher:
    """AES ECB 加密/解密"""
    
    def __init__(self, key):
        self.key = key.encode('utf-8')
        self.cipher = AES.new(self.key, AES.MODE_ECB)
    
    def pad(self, data):
        """PKCS7 填充"""
        block_size = 16
        pad_len = block_size - len(data) % block_size
        return data + bytes([pad_len] * pad_len)
    
    def unpad(self, data):
        """去除 PKCS7 填充"""
        return data[:-data[-1]]
    
    def encrypt(self, data):
        """加密"""
        padded = self.pad(data.encode('utf-8'))
        encrypted = self.cipher.encrypt(padded)
        return base64.b64encode(encrypted).decode('utf-8')
    
    def decrypt(self, encrypted_data):
        """解密"""
        decoded = base64.b64decode(encrypted_data)
        decrypted = self.cipher.decrypt(decoded)
        return self.unpad(decrypted).decode('utf-8')

class NgariExporter:
    """纳里健康报表导出器"""
    
    def __init__(self):
        self.aes = AESCipher(CONFIG['aes_key'])
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Origin': 'https://yypt.ngarihealth.com',
            'Referer': 'https://yypt.ngarihealth.com/',
            'X-Ca-Key': CONFIG['ca_key'],
            'X-Service-Id': 'opexport.exportService',
            'X-Service-Method': 'exportFinanceBillOrderExcel',
            'X-Service-Encrypt': '1',
            'csrfTk': CONFIG['csrf_tk'],
            'Encoding': 'utf-8',
        })
        self.session.cookies.set('SESSION', CONFIG['session_id'], domain='yypt.ngarihealth.com')
        
        os.makedirs(CONFIG['download_dir'], exist_ok=True)
    
    def _generate_headers(self, encrypted_body):
        """生成签名请求头"""
        nonce = str(uuid.uuid4()) + str(int(time.time() * 1000))
        timestamp = str(int(time.time() * 1000))
        
        # 计算 Content-MD5
        content_md5 = hashlib.md5(encrypted_body.encode('utf-8')).hexdigest()
        
        self.session.headers.update({
            'X-Ca-Nonce': nonce,
            'X-Ca-Timestamp': timestamp,
            'X-Content-MD5': content_md5,
        })
    
    def export(self, start_date=None, end_date=None):
        """
        导出报表
        start_date: 开始日期 YYYY-MM-DD
        end_date: 结束日期 YYYY-MM-DD
        """
        if not start_date:
            start_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = start_date
        
        print(f"📅 导出日期范围：{start_date} 到 {end_date}")
        
        # 构造请求参数 (需要根据实际 API 格式调整)
        request_data = {
            'startDate': start_date,
            'endDate': end_date,
            'type': '业务分账明细',  # 根据实际参数调整
        }
        
        # 加密请求体
        json_str = json.dumps(request_data, ensure_ascii=False)
        encrypted_body = self.aes.encrypt(json_str)
        
        print(f"🔐 已加密请求: {encrypted_body[:50]}...")
        
        # 生成签名头
        self._generate_headers(encrypted_body)
        
        # 发送请求
        try:
            print(f"🌐 发送请求到: {CONFIG['api_url']}")
            response = self.session.post(CONFIG['api_url'], data=encrypted_body)
            
            print(f"📥 响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                # 检查是否是加密响应
                content_type = response.headers.get('Content-Type', '')
                
                if 'json' in content_type:
                    # JSON 响应（可能是加密的）
                    resp_json = response.json()
                    print(f"📦 响应内容: {json.dumps(resp_json, ensure_ascii=False)[:200]}")
                    
                    # 尝试解密
                    if isinstance(resp_json, dict) and 'data' in resp_json:
                        try:
                            decrypted = self.aes.decrypt(resp_json['data'])
                            print(f"🔓 解密成功: {decrypted[:200]}")
                        except:
                            print("ℹ️ 响应不需要解密")
                    
                elif 'application/octet-stream' in content_type or 'excel' in content_type:
                    # 文件下载
                    filename = f"业务对账明细_{start_date}_{end_date}.xlsx"
                    filepath = os.path.join(CONFIG['download_dir'], filename)
                    
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
                    
                    print(f"✅ 文件已保存: {filepath}")
                    print(f"📄 文件大小: {len(response.content) / 1024:.1f} KB")
                else:
                    print(f"📄 响应内容类型: {content_type}")
                    print(f"内容: {response.text[:500]}")
            else:
                print(f"❌ 请求失败: {response.status_code}")
                print(f"响应: {response.text[:500]}")
        
        except Exception as e:
            print(f"❌ 请求异常: {e}")

if __name__ == '__main__':
    print("="*60)
    print("📊 纳里健康对账报表 API 导出工具")
    print("="*60)
    print(f"\n🌐 API: {CONFIG['api_url']}")
    print(f"🔑 AES 密钥: {CONFIG['aes_key']}")
    print(f"📁 保存目录：{CONFIG['download_dir']}")
    print("\n" + "="*60)
    
    exporter = NgariExporter()
    exporter.export()
