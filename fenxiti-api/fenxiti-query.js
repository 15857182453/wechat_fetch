#!/usr/bin/env node
/**
 * 分心体数据分析平台 API 查询工具
 * 
 * 支持：事件分析、漏斗分析、留存分析、分布分析
 * 
 * 用法：
 *   node fenxiti-query.js --type event --space WlGk4Daj --id AbQ3l3pY
 *   node fenxiti-query.js --type funnel --space nxGK0Da6 --id J1GlMVDj
 */

const axios = require('axios');
const fs = require('fs');
const path = require('path');

// ========== 配置区 ==========
const CONFIG = {
  // 分心体 API 配置
  fenxiti: {
    baseUrl: 'https://api-portal.fenxiti.com/v1/api',
    token: 'YOUR_TOKEN_HERE',  // TODO: 填入你的 Token
  },
  
  // 输出配置
  output: {
    dir: '/home/openclaw/.openclaw/workspace/fenxiti-api/results',
  },
};
// ===========================

/**
 * 分心体 API 客户端
 */
class FenxitiClient {
  constructor(token) {
    this.baseUrl = CONFIG.fenxiti.baseUrl;
    this.token = token;
    
    this.client = axios.create({
      baseURL: this.baseUrl,
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json',
      },
      params: {
        language: 'CH',
      },
    });
  }
  
  /**
   * 事件分析查询
   */
  async getEventAnalysis(spaceId, analysisId, options = {}) {
    const url = `/projects/${spaceId}/analysis/olap_event/${analysisId}/chartdata`;
    
    const params = {
      forceRefresh: false,
      limit: 1000,
      offset: 0,
      ...options,
    };
    
    const res = await this.client.get(url, { params });
    
    if (res.data.code !== 0) {
      throw new Error(`事件分析查询失败：${res.data.msg}`);
    }
    
    return res.data.data;
  }
  
  /**
   * 漏斗分析查询
   */
  async getFunnelAnalysis(spaceId, analysisId, options = {}) {
    const url = `/projects/${spaceId}/analysis/funnel/${analysisId}/chartdata`;
    
    const params = {
      forceRefresh: false,
      ...options,
    };
    
    const res = await this.client.get(url, { params });
    
    if (res.data.code !== 0) {
      throw new Error(`漏斗分析查询失败：${res.data.msg}`);
    }
    
    return res.data.data;
  }
  
  /**
   * 留存分析查询
   */
  async getRetentionAnalysis(spaceId, analysisId, options = {}) {
    const url = `/projects/${spaceId}/analysis/retention/${analysisId}/chartdata`;
    
    const params = {
      forceRefresh: false,
      ...options,
    };
    
    const res = await this.client.get(url, { params });
    
    if (res.data.code !== 0) {
      throw new Error(`留存分析查询失败：${res.data.msg}`);
    }
    
    return res.data.data;
  }
  
  /**
   * 分布分析查询
   */
  async getFrequencyAnalysis(spaceId, analysisId, options = {}) {
    const url = `/projects/${spaceId}/analysis/frequency/${analysisId}/chartdata`;
    
    const params = {
      forceRefresh: false,
      ...options,
    };
    
    const res = await this.client.get(url, { params });
    
    if (res.data.code !== 0) {
      throw new Error(`分布分析查询失败：${res.data.msg}`);
    }
    
    return res.data.data;
  }
  
  /**
   * 查询所有分析类型
   */
  async queryAll(spaceId, analysisIds) {
    const results = {};
    
    if (analysisIds.event) {
      console.log('📊 查询事件分析...');
      results.event = await this.getEventAnalysis(spaceId, analysisIds.event);
    }
    
    if (analysisIds.funnel) {
      console.log('📊 查询漏斗分析...');
      results.funnel = await this.getFunnelAnalysis(spaceId, analysisIds.funnel);
    }
    
    if (analysisIds.retention) {
      console.log('📊 查询留存分析...');
      results.retention = await this.getRetentionAnalysis(spaceId, analysisIds.retention);
    }
    
    if (analysisIds.frequency) {
      console.log('📊 查询分布分析...');
      results.frequency = await this.getFrequencyAnalysis(spaceId, analysisIds.frequency);
    }
    
    return results;
  }
}

/**
 * 格式化输出结果
 */
function formatResult(type, data) {
  console.log('\n' + '='.repeat(60));
  console.log(`📊 ${type}分析结果`);
  console.log('='.repeat(60));
  
  // 分析信息
  if (data.analysisInfo) {
    const info = data.analysisInfo;
    console.log(`\n📋 分析名称：${info.name}`);
    console.log(`📅 时间范围：${info.startTime} ~ ${info.endTime}`);
    if (info.granularity) {
      console.log(`⏱️ 时间粒度：${info.granularity}`);
    }
    if (info.conversionWindow) {
      console.log(`🔄 转化窗口：${info.conversionWindow} ${info.windowGranularity}`);
    }
  }
  
  // 列名
  if (data.resultHeader) {
    console.log(`\n📑 列名：${data.resultHeader.join(', ')}`);
  }
  
  // 数据行数
  if (data.resultRows) {
    console.log(`📈 数据行数：${data.resultRows.length}`);
    
    // 显示前 5 行
    console.log('\n📋 数据预览（前 5 行）：');
    data.resultRows.slice(0, 5).forEach((row, index) => {
      console.log(`   ${index + 1}. ${row.join(' | ')}`);
    });
  }
  
  // 分页信息
  if (data.paginationInfo) {
    const page = data.paginationInfo;
    console.log(`\n📄 分页：${page.offset}-${page.offset + page.limit} / ${page.totalCount}`);
  }
  
  console.log('='.repeat(60) + '\n');
}

/**
 * 保存结果到文件
 */
function saveResult(type, data) {
  const outputDir = CONFIG.output.dir;
  
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }
  
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const filename = `${type}_${timestamp}.json`;
  const filepath = path.join(outputDir, filename);
  
  fs.writeFileSync(filepath, JSON.stringify(data, null, 2), 'utf8');
  console.log(`💾 结果已保存：${filepath}`);
  
  return filepath;
}

/**
 * 主函数
 */
async function main() {
  const args = process.argv.slice(2);
  
  // 解析参数
  const params = {};
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--type' || args[i] === '-t') {
      params.type = args[++i];
    } else if (args[i] === '--space' || args[i] === '-s') {
      params.space = args[++i];
    } else if (args[i] === '--id' || args[i] === '-i') {
      params.id = args[++i];
    } else if (args[i] === '--token' || args[i] === '-T') {
      params.token = args[++i];
    } else if (args[i] === '--output' || args[i] === '-o') {
      params.output = args[++i];
    } else if (args[i] === '--help' || args[i] === '-h') {
      showHelp();
      return;
    }
  }
  
  // 显示帮助
  if (!params.type || !params.space || !params.id) {
    console.log('❌ 缺少必要参数\n');
    showHelp();
    return;
  }
  
  // 获取 Token
  const token = params.token || CONFIG.fenxiti.token;
  if (!token || token === 'YOUR_TOKEN_HERE') {
    console.log('❌ 请提供 Token\n');
    console.log('获取方式：');
    console.log('  1. 登录分心体平台');
    console.log('  2. 进入 个人中心 > Token 管理');
    console.log('  3. 复制 Token');
    console.log('\n使用方法：');
    console.log('  node fenxiti-query.js --type event --space WlGk4Daj --id AbQ3l3pY --token YOUR_TOKEN\n');
    return;
  }
  
  try {
    console.log('🚀 分心体数据分析查询\n');
    console.log(`类型：${params.type}`);
    console.log(`空间：${params.space}`);
    console.log(`分析：${params.id}\n`);
    
    // 创建客户端
    const client = new FenxitiClient(token);
    
    // 查询
    let result;
    switch (params.type.toLowerCase()) {
      case 'event':
      case 'olap_event':
        result = await client.getEventAnalysis(params.space, params.id);
        formatResult('事件', result);
        break;
        
      case 'funnel':
        result = await client.getFunnelAnalysis(params.space, params.id);
        formatResult('漏斗', result);
        break;
        
      case 'retention':
        result = await client.getRetentionAnalysis(params.space, params.id);
        formatResult('留存', result);
        break;
        
      case 'frequency':
        result = await client.getFrequencyAnalysis(params.space, params.id);
        formatResult('分布', result);
        break;
        
      default:
        console.log(`❌ 未知的分析类型：${params.type}`);
        console.log('支持的类型：event, funnel, retention, frequency');
        return;
    }
    
    // 保存结果
    if (params.output !== 'false') {
      saveResult(params.type, result);
    }
    
  } catch (error) {
    console.error('❌ 查询失败:', error.message);
    if (error.response?.data) {
      console.error('   详情:', error.response.data);
    }
    process.exit(1);
  }
}

/**
 * 显示帮助信息
 */
function showHelp() {
  console.log(`
📊 分心体数据分析查询工具

用法:
  node fenxiti-query.js [选项]

选项:
  -t, --type <类型>     分析类型（必填）
                        event - 事件分析
                        funnel - 漏斗分析
                        retention - 留存分析
                        frequency - 分布分析
  
  -s, --space <ID>      空间 ID（必填）
  -i, --id <ID>         分析 ID（必填）
  -T, --token <Token>   分心体 Token
  -o, --output <文件>   输出文件（默认自动保存）
  -h, --help            显示帮助

示例:
  # 查询事件分析
  node fenxiti-query.js -t event -s WlGk4Daj -i AbQ3l3pY -T YOUR_TOKEN

  # 查询漏斗分析
  node fenxiti-query.js --type funnel --space nxGK0Da6 --id J1GlMVDj

  # 查询留存分析
  node fenxiti-query.js -t retention -s nxGK0Da6 -i wWDrYwGM

获取分析 ID:
  打开分析详情页，从 URL 中获取：
  https://api-portal.fenxiti.com/uba/spaces/{spaceId}/analysis/{type}/{id}

`);
}

main();
