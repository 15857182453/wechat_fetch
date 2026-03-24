#!/usr/bin/env node
/**
 * 飞书多维表格 → OpenClaw 知识库 增量同步脚本
 * 只同步新增或更新的文章
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
    stateFile: '/home/openclaw/.openclaw/workspace/knowledge-sync/sync-state.json',
  },
};

// 加载同步状态
function loadSyncState() {
  if (fs.existsSync(CONFIG.output.stateFile)) {
    const data = fs.readFileSync(CONFIG.output.stateFile, 'utf8');
    return JSON.parse(data);
  }
  return { syncedRecords: {}, lastSyncTime: null };
}

// 保存同步状态
function saveSyncState(state) {
  state.lastSyncTime = new Date().toISOString();
  fs.writeFileSync(CONFIG.output.stateFile, JSON.stringify(state, null, 2), 'utf8');
}

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
  } while (pageToken);
  
  return records;
}

function recordToMarkdown(record) {
  const fields = record.fields;
  
  const title = fields['标题'] || `文档-${record.record_id}`;
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
  
  return { filename, content: md, recordId: record.record_id };
}

async function main() {
  console.log('🚀 飞书多维表格 → OpenClaw 知识库 增量同步\n');
  console.log('='.repeat(50));
  
  try {
    // 加载同步状态
    const syncState = loadSyncState();
    const syncedCount = Object.keys(syncState.syncedRecords).length;
    console.log(`📊 上次同步：${syncState.lastSyncTime || '从未'}`);
    console.log(`📁 已同步记录：${syncedCount} 条\n`);
    
    console.log('📝 获取 Access Token...');
    const token = await getAccessToken();
    console.log('✓ Token 获取成功\n');
    
    console.log('📊 读取表格数据...');
    const records = await getTableRecords(token);
    console.log(`✓ 共获取 ${records.length} 条记录\n`);
    
    // 创建输出目录
    if (!fs.existsSync(CONFIG.output.dir)) {
      fs.mkdirSync(CONFIG.output.dir, { recursive: true });
    }
    
    // 增量同步
    console.log('🔄 开始增量同步...');
    let newCount = 0;
    let updateCount = 0;
    let skipCount = 0;
    
    records.forEach((record) => {
      const { filename, content, recordId } = recordToMarkdown(record);
      const filePath = path.join(CONFIG.output.dir, filename);
      
      // 检查是否需要更新
      const existingState = syncState.syncedRecords[recordId];
      const fileExists = fs.existsSync(filePath);
      
      if (existingState && existingState.filename === filename && fileExists) {
        // 记录已存在且文件名未变，跳过
        skipCount++;
        return;
      }
      
      // 保存文件
      fs.writeFileSync(filePath, content, 'utf8');
      
      // 更新状态
      syncState.syncedRecords[recordId] = {
        filename,
        syncTime: new Date().toISOString(),
      };
      
      if (!existingState) {
        newCount++;
        console.log(`   ✨ 新增：${filename}`);
      } else {
        updateCount++;
        console.log(`   🔄 更新：${filename}`);
      }
    });
    
    // 保存同步状态
    saveSyncState(syncState);
    
    console.log('\n📋 同步完成！');
    console.log('='.repeat(50));
    console.log(`✨ 新增：${newCount} 篇`);
    console.log(`🔄 更新：${updateCount} 篇`);
    console.log(`⏭️ 跳过：${skipCount} 篇`);
    console.log(`📂 目录：${CONFIG.output.dir}`);
    console.log(`⏰ 时间：${new Date().toLocaleString('zh-CN')}\n`);
    
  } catch (error) {
    console.error('❌ 同步失败:', error.message);
    if (error.response?.data) {
      console.error('   详情:', error.response.data);
    }
    process.exit(1);
  }
}

main();
