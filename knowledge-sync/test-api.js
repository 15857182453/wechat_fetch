#!/usr/bin/env node
/**
 * 测试飞书 API - 详细错误诊断
 */

const axios = require('axios');

const CONFIG = {
  appId: 'cli_a924dc7790625bd3',
  appSecret: 'KfKqczGdsExKvXMq4m8HafrFc3WQx7t1',
  appToken: 'BFQjbYgHUaaAmwsYdubcZ5hWnc5',
  tableId: 'tblmjBEemH3THeWU',
};

async function testAPI(domain, token) {
  console.log(`\n🔍 测试域名：${domain}`);
  console.log('─'.repeat(50));
  
  const tests = [
    {
      name: '获取用户信息',
      url: `${domain}/open-apis/auth/v3/user/info`,
      method: 'get',
    },
    {
      name: '获取多维表格列表',
      url: `${domain}/open-apis/bitable/v1/apps`,
      method: 'get',
    },
    {
      name: '获取指定 Base 信息',
      url: `${domain}/open-apis/bitable/v1/apps/${CONFIG.appToken}`,
      method: 'get',
    },
    {
      name: '获取表格列表',
      url: `${domain}/open-apis/bitable/v1/apps/${CONFIG.appToken}/tables`,
      method: 'get',
    },
    {
      name: '获取表格记录',
      url: `${domain}/open-apis/bitable/v1/apps/${CONFIG.appToken}/tables/${CONFIG.tableId}/records`,
      method: 'get',
      params: { page_size: 1 },
    },
  ];
  
  for (const test of tests) {
    try {
      const config = {
        method: test.method,
        url: test.url,
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        params: test.params || {},
      };
      
      const res = await axios(config);
      
      if (res.data.code === 0) {
        console.log(`✅ ${test.name}: 成功`);
        // 打印部分返回数据帮助调试
        const dataStr = JSON.stringify(res.data.data);
        if (dataStr.length < 200) {
          console.log(`   返回：${dataStr}`);
        } else {
          console.log(`   返回：${dataStr.substring(0, 200)}...`);
        }
      } else {
        console.log(`❌ ${test.name}: ${res.data.msg} (code: ${res.data.code})`);
      }
    } catch (err) {
      const status = err.response?.status;
      const msg = err.response?.data?.msg || err.message;
      console.log(`❌ ${test.name}: HTTP ${status} - ${msg}`);
    }
  }
}

async function main() {
  console.log('🚀 飞书 API 详细诊断');
  console.log('='.repeat(50));
  console.log(`App ID: ${CONFIG.appId}`);
  console.log(`App Token: ${CONFIG.appToken}`);
  console.log(`Table ID: ${CONFIG.tableId}`);
  
  // 获取 Token
  const domains = [
    'https://open.feishu.cn',
    'https://open.larksuite.com',
  ];
  
  for (const domain of domains) {
    try {
      console.log(`\n📝 尝试获取 Token (${domain})...`);
      const tokenRes = await axios.post(`${domain}/open-apis/auth/v3/tenant_access_token/internal`, {
        app_id: CONFIG.appId,
        app_secret: CONFIG.appSecret,
      });
      
      if (tokenRes.data.code === 0 && tokenRes.data.tenant_access_token) {
        const token = tokenRes.data.tenant_access_token;
        console.log(`✓ Token 获取成功`);
        await testAPI(domain, token);
        return;
      } else {
        console.log(`✗ Token 失败：${tokenRes.data.msg}`);
      }
    } catch (err) {
      console.log(`✗ Token 请求失败：${err.message}`);
    }
  }
}

main();
