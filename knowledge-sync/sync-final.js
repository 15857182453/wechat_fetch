#!/usr/bin/env node
/**
 * 飞书多维表格 → OpenClaw 知识库同步脚本（最终版）
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
    appToken: 'BKABw6CJriaeYtkE9v9cjy4wneg',
    tableId: 'tblhWgNl1uLYa4GL',
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

function recordToMarkdown(record, index) {
  const fields = record.fields;
  
  const title = fields['标题'] || `文档-${index + 1}`;
  const content = fields['文章内容'] || '';
  const summary = fields['文章总结'] || '';
  const summaryKimi = fields['文章总结 kimi'] || '';
  const url = fields['文章地址'] || '';
  const coverImage = fields['封面地址'] || '';
  const publishTime = fields['发表时间'] || '';
  
  let md = `---\n`;
  md += `title: "${title}"\n`;
  if (publishTime) md += `publishDate: "${publishTime}"\n`;
  if (url) md += `url: "${url}"\n`;
  if (coverImage) md += `coverImage: "${coverImage}"\n`;
  md += `source: "飞书多维表格"\n`;
  md += `syncTime: "${new Date().toISOString()}"\n`;
  md += `---\n\n`;
  
  md += `# ${title}\n\n`;
  
  if (coverImage) {
    md += `![封面](${coverImage})\n\n`;
  }
  
  if (summaryKimi) {
    md += `## 📝 AI 摘要\n\n`;
    md += `${summaryKimi}\n\n`;
  } else if (summary) {
    md += `## 📝 摘要\n\n`;
    md += `${summary}\n\n`;
  }
  
  if (content) {
    md += `## 📄 正文\n\n`;
    md += `${content}\n\n`;
  }
  
  if (url) {
    md += `---\n\n`;
    md += `原文链接：${url}\n`;
  }
  
  const filename = `${title.replace(/[\/\\:*?"<>|]/g, '_')}.md`;
  
  return { filename, content: md };
}

async function main() {
  console.log('🚀 飞书多维表格 → OpenClaw 知识库同步\n');
  console.log('='.repeat(50));
  
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
      const { filename, content } = recordToMarkdown(record, index);
      const filePath = path.join(CONFIG.output.dir, filename);
      fs.writeFileSync(filePath, content, 'utf8');
      savedFiles.push(filePath);
      
      // 显示进度
      if ((index + 1) % 10 === 0 || index === records.length - 1) {
        console.log(`   已保存 ${index + 1}/${records.length} 个文件`);
      }
    });
    
    console.log(`\n✓ 成功保存 ${savedFiles.length} 个文件\n`);
    console.log('📋 同步完成！');
    console.log('='.repeat(50));
    console.log(`📂 知识库目录：${CONFIG.output.dir}`);
    console.log(`📄 文件数量：${savedFiles.length}`);
    console.log(`⏰ 同步时间：${new Date().toLocaleString('zh-CN')}\n`);
    
    // 显示前 5 个文件
    console.log('📋 最新文件预览：');
    savedFiles.slice(0, 5).forEach(file => {
      console.log(`   - ${path.basename(file)}`);
    });
    console.log();
    
  } catch (error) {
    console.error('❌ 同步失败:', error.message);
    if (error.response?.data) {
      console.error('   详情:', error.response.data);
    }
    process.exit(1);
  }
}

main();
