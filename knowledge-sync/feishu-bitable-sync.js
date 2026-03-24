#!/usr/bin/env node
/**
 * 飞书多维表格 → OpenClaw 知识库 同步脚本
 * 
 * 用法：
 *   node feishu-bitable-sync.js
 * 
 * 配置：
 *   复制 config.example.js 为 config.js 并填入你的配置
 */

const axios = require('axios');
const fs = require('fs');
const path = require('path');

// ========== 配置区 ==========
const CONFIG = {
  // 飞书应用配置
  feishu: {
    appId: 'YOUR_APP_ID',
    appSecret: 'YOUR_APP_SECRET',
    // 飞书域名（国内用 feishu.cn，国际用 larksuite.com）
    domain: 'https://open.feishu.cn',
  },
  
  // 多维表格配置
  bitable: {
    // 从 URL 获取：https://xxx.feishu.cn/base/bascnXXXXX?table=tblXXXXX
    appToken: 'YOUR_APP_TOKEN',
    tableId: 'YOUR_TABLE_ID',
    // 要同步的字段映射（根据你的表格结构调整）
    fields: {
      title: '标题',      // 知识库标题字段
      content: '内容',    // 知识库内容字段
      category: '分类',   // 分类字段（可选）
      tags: '标签',       // 标签字段（可选）
      updatedAt: '更新时间', // 更新时间字段（可选）
    },
  },
  
  // 输出配置
  output: {
    // 知识库输出目录（相对于工作空间）
    dir: '/home/openclaw/.openclaw/workspace/knowledge',
    // 是否按分类创建子目录
    byCategory: true,
    // 文件名格式：{id}.md 或 {title}.md
    filenameFormat: 'title',
  },
  
  // 同步配置
  sync: {
    // 每次同步的最大记录数
    pageSize: 500,
    // 是否删除本地有但表格中没有的文件
    cleanOrphaned: false,
  },
};
// ===========================

/**
 * 获取飞书 tenant access token
 */
async function getTenantAccessToken() {
  const url = `${CONFIG.feishu.domain}/open-apis/auth/v3/tenant_access_token/internal`;
  const res = await axios.post(url, {
    app_id: CONFIG.feishu.appId,
    app_secret: CONFIG.feishu.appSecret,
  });
  
  if (res.data.code !== 0) {
    throw new Error(`获取 Token 失败：${res.data.msg}`);
  }
  
  return res.data.tenant_access_token;
}

/**
 * 获取多维表格数据
 */
async function getBitableData(accessToken) {
  const records = [];
  let pageToken = null;
  
  do {
    const url = `${CONFIG.feishu.domain}/open-apis/bitable/v1/apps/${CONFIG.bitable.appToken}/tables/${CONFIG.bitable.tableId}/records`;
    const params = {
      page_size: CONFIG.sync.pageSize,
      field_names: Object.values(CONFIG.bitable.fields),
    };
    
    if (pageToken) {
      params.page_token = pageToken;
    }
    
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
    
    console.log(`已获取 ${records.length} 条记录...`);
  } while (pageToken);
  
  return records;
}

/**
 * 将记录转换为 Markdown 文件内容
 */
function recordToMarkdown(record, index) {
  const fields = record.fields;
  const fieldMap = CONFIG.bitable.fields;
  
  const title = fields[fieldMap.title] || `未命名-${index}`;
  const content = fields[fieldMap.content] || '';
  const category = fields[fieldMap.category] || '未分类';
  const tags = Array.isArray(fields[fieldMap.tags]) 
    ? fields[fieldMap.tags].join(', ') 
    : (fields[fieldMap.tags] || '');
  const updatedAt = fields[fieldMap.updatedAt] || new Date().toISOString();
  
  // 构建 Markdown 内容
  let markdown = `---\n`;
  markdown += `title: "${title}"\n`;
  markdown += `category: "${category}"\n`;
  if (tags) {
    markdown += `tags: [${tags.split(',').map(t => `"${t.trim()}"`).join(', ')}]\n`;
  }
  markdown += `updatedAt: "${updatedAt}"\n`;
  markdown += `source: "飞书多维表格"\n`;
  markdown += `---\n\n`;
  
  markdown += `# ${title}\n\n`;
  markdown += `${content}\n`;
  
  return {
    filename: CONFIG.output.filenameFormat === 'title' 
      ? `${title.replace(/[\/\\:*?"<>|]/g, '_')}.md`
      : `${record.record_id}.md`,
    content: markdown,
    category,
  };
}

/**
 * 主函数
 */
async function main() {
  console.log('🚀 开始同步飞书多维表格到知识库...\n');
  
  try {
    // 1. 获取 Access Token
    console.log('📝 获取飞书 Access Token...');
    const accessToken = await getTenantAccessToken();
    console.log('✓ Token 获取成功\n');
    
    // 2. 获取表格数据
    console.log('📊 读取多维表格数据...');
    const records = await getBitableData(accessToken);
    console.log(`✓ 共获取 ${records.length} 条记录\n`);
    
    // 3. 创建输出目录
    if (!fs.existsSync(CONFIG.output.dir)) {
      fs.mkdirSync(CONFIG.output.dir, { recursive: true });
      console.log(`📁 创建知识库目录：${CONFIG.output.dir}\n`);
    }
    
    // 4. 转换并保存文件
    console.log('📝 生成知识库文件...');
    const savedFiles = [];
    
    records.forEach((record, index) => {
      const { filename, content, category } = recordToMarkdown(record, index);
      
      let filePath = path.join(CONFIG.output.dir, filename);
      
      // 如果按分类保存
      if (CONFIG.output.byCategory && category !== '未分类') {
        const categoryDir = path.join(CONFIG.output.dir, category);
        if (!fs.existsSync(categoryDir)) {
          fs.mkdirSync(categoryDir, { recursive: true });
        }
        filePath = path.join(categoryDir, filename);
      }
      
      fs.writeFileSync(filePath, content, 'utf8');
      savedFiles.push(filePath);
    });
    
    console.log(`✓ 成功保存 ${savedFiles.length} 个文件\n`);
    
    // 5. 输出摘要
    console.log('📋 同步完成！');
    console.log(`   知识库目录：${CONFIG.output.dir}`);
    console.log(`   文件数量：${savedFiles.length}`);
    console.log(`   同步时间：${new Date().toLocaleString('zh-CN')}\n`);
    
  } catch (error) {
    console.error('❌ 同步失败:', error.message);
    if (error.response) {
      console.error('   响应:', error.response.data);
    }
    process.exit(1);
  }
}

// 运行
main();
