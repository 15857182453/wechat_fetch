#!/usr/bin/env node
/**
 * 飞书多维表格 → 知识库同步脚本（最终版）
 * 使用正确的 API 端点获取数据
 */

const axios = require('axios');
const fs = require('fs');
const path = require('path');

const CONFIG = {
  feishu: {
    appId: 'cli_a924dc7790625bd3',
    appSecret: 'KfKqczGdsExKvXMq4m8HafrFc3WQx7t1',
    domain: 'https://open.feishu.cn',
  },
  bitable: {
    appToken: 'BFQjbYgHUaaAmwsYdubcZ5hWnc5',
    tableId: 'tblmjBEemH3THeWU',
  },
  output: {
    dir: '/home/openclaw/.openclaw/workspace/knowledge',
  },
};

async function getAccessToken() {
  const res = await axios.post(`${CONFIG.feishu.domain}/open-apis/auth/v3/tenant_access_token/internal`, {
    app_id: CONFIG.feishu.appId,
    app_secret: CONFIG.feishu.appSecret,
  });
  
  if (res.data.code !== 0) {
    throw new Error(`Token 失败：${res.data.msg}`);
  }
  
  return res.data.tenant_access_token;
}

async function getTableRecords(accessToken) {
  const records = [];
  let pageToken = null;
  
  console.log('📊 开始获取表格数据...');
  
  do {
    const url = `${CONFIG.feishu.domain}/open-apis/bitable/v1/apps/${CONFIG.bitable.appToken}/tables/${CONFIG.bitable.tableId}/records`;
    const params = { page_size: 500 };
    if (pageToken) params.page_token = pageToken;
    
    const res = await axios.get(url, {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      params,
    });
    
    if (res.data.code !== 0) {
      throw new Error(`获取数据失败：${res.data.msg}`);
    }
    
    records.push(...res.data.data.items);
    pageToken = res.data.data.page_token;
    
    console.log(`   已获取 ${records.length} 条记录...`);
  } while (pageToken);
  
  return records;
}

function recordToMarkdown(record, index, fieldNames) {
  const fields = record.fields;
  
  // 自动检测字段
  const title = fields['标题'] || fields['Title'] || fields['名称'] || `文档-${index + 1}`;
  const content = fields['内容'] || fields['Content'] || fields['描述'] || fields['正文'] || '';
  const category = fields['分类'] || fields['Category'] || fields['类型'] || '未分类';
  const tags = Array.isArray(fields['标签']) ? fields['标签'].join(', ') : (fields['标签'] || fields['Tags'] || '');
  
  let md = `---\n`;
  md += `title: "${title}"\n`;
  md += `category: "${category}"\n`;
  if (tags) md += `tags: [${tags.split(',').map(t => `"${t.trim()}"`).join(', ')}]\n`;
  md += `source: "飞书多维表格"\n`;
  md += `---\n\n`;
  md += `# ${title}\n\n`;
  md += `${content}\n`;
  
  const filename = `${title.replace(/[\/\\:*?"<>|]/g, '_')}.md`;
  
  return { filename, content: md, category };
}

async function main() {
  console.log('🚀 飞书多维表格 → 知识库同步\n');
  
  try {
    console.log('📝 获取 Access Token...');
    const token = await getAccessToken();
    console.log('✓ Token 获取成功\n');
    
    console.log('📊 读取表格数据...');
    const records = await getTableRecords(token);
    console.log(`✓ 共获取 ${records.length} 条记录\n`);
    
    if (records.length === 0) {
      console.log('⚠️ 表格为空，没有数据可同步\n');
      return;
    }
    
    // 创建输出目录
    if (!fs.existsSync(CONFIG.output.dir)) {
      fs.mkdirSync(CONFIG.output.dir, { recursive: true });
      console.log(`📁 创建目录：${CONFIG.output.dir}\n`);
    }
    
    // 保存文件
    console.log('📝 生成知识库文件...');
    const savedFiles = [];
    
    records.forEach((record, index) => {
      const { filename, content, category } = recordToMarkdown(record, index);
      
      const categoryDir = path.join(CONFIG.output.dir, category);
      if (!fs.existsSync(categoryDir)) {
        fs.mkdirSync(categoryDir, { recursive: true });
      }
      
      const filePath = path.join(categoryDir, filename);
      fs.writeFileSync(filePath, content, 'utf8');
      savedFiles.push(filePath);
    });
    
    console.log(`✓ 成功保存 ${savedFiles.length} 个文件\n`);
    console.log('📋 同步完成！');
    console.log(`   目录：${CONFIG.output.dir}`);
    console.log(`   文件数：${savedFiles.length}`);
    console.log(`   时间：${new Date().toLocaleString('zh-CN')}\n`);
    
  } catch (error) {
    console.error('❌ 同步失败:', error.message);
    if (error.response?.data) {
      console.error('   详情:', error.response.data);
    }
    console.error('\n💡 提示：');
    console.error('   1. 确认应用已重新发布（权限变更后需要新版本）');
    console.error('   2. 等待 3-5 分钟让权限生效');
    console.error('   3. 检查多维表格是否对应用可见\n');
    process.exit(1);
  }
}

main();
