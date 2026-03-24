#!/usr/bin/env node
/**
 * 获取飞书多维表格的元数据（表结构）
 * 用于查看表格有哪些列
 */

const axios = require('axios');

// 配置
const CONFIG = {
  appId: 'cli_a924dc7790625bd3',
  appSecret: 'KfKqczGdsExKvXMq4m8HafrFc3WQx7t1',
  appToken: 'BFQjbYgHUaaAmwsYdubcZ5hWnc5',
  tableId: 'tblmjBEemH3THeWU',
  // 尝试多个域名
  domains: [
    'https://open.feishu.cn',      // 国内版
    'https://open.larksuite.com',  // 国际版
  ],
};

async function main() {
  console.log('🔍 获取飞书多维表格结构...\n');
  
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
        console.log(`✗ Token 获取失败：${tokenRes.data.msg}\n`);
      }
    } catch (err) {
      console.log(`✗ 请求失败：${err.message}\n`);
    }
  }
  
  if (!accessToken) {
    throw new Error('所有域名都 failed 获取 Token，请检查 App ID/Secret 是否正确');
  }
  
  try {
    // 2. 获取表格元数据（尝试多个 API 版本）
    const apiEndpoints = [
      `${usedDomain}/open-apis/bitable/v1/apps/${CONFIG.appToken}/tables/${CONFIG.tableId}/metainfo`,
      `${usedDomain}/open-apis/bitable/v1/apps/${CONFIG.appToken}/tables/${CONFIG.tableId}`,
      `${usedDomain}/open-apis/bitable/v1/apps/${CONFIG.appToken}/tables`,
      `${usedDomain}/open-apis/bitable/v1/apps/${CONFIG.appToken}`,
    ];
    
    let table = null;
    let usedEndpoint = null;
    
    for (const url of apiEndpoints) {
      try {
        console.log(`📊 尝试获取表格结构：${url}`);
        const res = await axios.get(url, {
          headers: {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json',
          },
        });
        
        if (res.data.code === 0) {
          table = res.data.data;
          usedEndpoint = url;
          console.log('✓ 成功获取表格信息\n');
          break;
        }
      } catch (err) {
        console.log(`✗ 失败 (${err.response?.status || 'unknown'}), 尝试下一个...\n`);
      }
    }
    
    if (!table) {
      throw new Error('所有 API 端点都失败了，请检查权限和应用是否已发布');
    }
    
    console.log('\n✅ 表格信息：');
    if (table.name) {
      console.log(`   表格名称：${table.name}`);
    }
    if (table.id) {
      console.log(`   表格 ID: ${table.id}`);
    }
    
    console.log('\n📋 列（字段）信息：');
    console.log('   ┌─────────────────────────────────────────');
    
    if (table.fields && table.fields.length > 0) {
      table.fields.forEach((field, index) => {
        console.log(`   │ ${index + 1}. ${field.name} (${field.type})`);
      });
    } else if (table.tables) {
      // 可能是返回了整个 base 的信息
      console.log('   │ 检测到多个数据表:');
      table.tables.forEach((t, idx) => {
        console.log(`   │   表${idx + 1}: ${t.name} (ID: ${t.id})`);
        if (t.fields) {
          t.fields.forEach((f, fIdx) => {
            console.log(`   │     - ${f.name} (${f.type})`);
          });
        }
      });
    } else {
      console.log('   │ 未获取到字段信息');
      console.log('   │ 返回数据:', JSON.stringify(table, null, 2).substring(0, 500));
    }
    
    console.log('   └─────────────────────────────────────────\n');
    
    console.log('💡 提示：');
    console.log('   将上面的列名填入 config.js 的 fields 配置中');
    console.log('   例如：fields: { title: \'列名\', content: \'列名\' }\n');
    
  } catch (error) {
    console.error('❌ 错误:', error.message);
    if (error.response?.data) {
      console.error('   详情:', JSON.stringify(error.response.data, null, 2));
    }
    console.error('\n⚠️ 请确认：');
    console.error('   1. config.js 中已填入正确的 App ID 和 App Secret');
    console.error('   2. 飞书应用已添加 bitable:app 和 bitable:table 权限');
    console.error('   3. 应用已发布\n');
    process.exit(1);
  }
}

main();
