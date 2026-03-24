#!/usr/bin/env node
/**
 * 测试新的飞书多维表格
 */

const axios = require('axios');

const CONFIG = {
  appId: 'cli_a924dc7790625bd3',
  appSecret: 'KfKqczGdsExKvXMq4m8HafrFc3WQx7t1',
  appToken: 'BKABw6CJriaeYtkE9v9cjy4wneg',
  tableId: 'tblhWgNl1uLYa4GL',
  domains: [
    'https://open.feishu.cn',
    'https://open.larksuite.com',
  ],
};

async function main() {
  console.log('🚀 测试新的飞书多维表格');
  console.log('='.repeat(50));
  console.log(`App Token: ${CONFIG.appToken}`);
  console.log(`Table ID: ${CONFIG.tableId}`);
  console.log();
  
  let accessToken = null;
  let usedDomain = null;
  
  // 尝试多个域名获取 Token
  for (const domain of CONFIG.domains) {
    try {
      console.log(`📝 尝试域名：${domain}`);
      const tokenRes = await axios.post(`${domain}/open-apis/auth/v3/tenant_access_token/internal`, {
        app_id: CONFIG.appId,
        app_secret: CONFIG.appSecret,
      });
      
      if (tokenRes.data.code === 0 && tokenRes.data.tenant_access_token) {
        accessToken = tokenRes.data.tenant_access_token;
        usedDomain = domain;
        console.log(`✓ Token 获取成功 (域名：${domain})\n`);
        break;
      } else {
        console.log(`✗ Token 失败：${tokenRes.data.msg}\n`);
      }
    } catch (err) {
      console.log(`✗ 请求失败：${err.message}\n`);
    }
  }
  
  if (!accessToken) {
    console.error('❌ 所有域名都无法获取 Token');
    process.exit(1);
  }
  
  // 测试获取表格记录
  console.log('📊 尝试获取表格数据...\n');
  
  const testUrls = [
    `${usedDomain}/open-apis/bitable/v1/apps/${CONFIG.appToken}/tables/${CONFIG.tableId}/records`,
    `${usedDomain}/open-apis/bitable/v1/apps/${CONFIG.appToken}/tables/${CONFIG.tableId}`,
    `${usedDomain}/open-apis/bitable/v1/apps/${CONFIG.appToken}/tables`,
  ];
  
  for (const url of testUrls) {
    try {
      console.log(`🔗 测试：${url}`);
      const res = await axios.get(url, {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
        params: { page_size: 5 },
      });
      
      if (res.data.code === 0) {
        console.log('✅ 成功！\n');
        console.log('📋 返回数据预览：');
        
        if (res.data.data.items) {
          console.log(`   记录数：${res.data.data.items.length}`);
          
          if (res.data.data.items.length > 0) {
            console.log('\n   字段名：');
            const firstRecord = res.data.data.items[0];
            if (firstRecord.fields) {
              Object.keys(firstRecord.fields).forEach(fieldName => {
                console.log(`   - ${fieldName}`);
              });
            }
            
            console.log('\n   第一条数据预览：');
            console.log('   ' + JSON.stringify(firstRecord.fields, null, 2).split('\n').join('\n   '));
          }
        } else {
          console.log('   ' + JSON.stringify(res.data.data, null, 2).substring(0, 500));
        }
        
        console.log('\n✅ 可以开始同步知识库了！\n');
        return;
      } else {
        console.log(`❌ 失败：${res.data.msg} (code: ${res.data.code})\n`);
      }
    } catch (err) {
      const status = err.response?.status;
      const msg = err.response?.data?.msg || err.message;
      console.log(`❌ 失败：HTTP ${status} - ${msg}\n`);
    }
  }
  
  console.error('❌ 所有 API 端点都失败了');
  console.error('\n💡 请检查：');
  console.error('   1. 应用是否有 bitable 相关权限');
  console.error('   2. 应用是否已发布');
  console.error('   3. 多维表格是否对应用可见\n');
  process.exit(1);
}

main();
