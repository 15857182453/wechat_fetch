// 飞书多维表格同步配置
// 复制此文件为 config.js 并填入你的配置

module.exports = {
  // 飞书应用配置
  feishu: {
    appId: 'cli_xxxxxxxxxxxxx',           // 从飞书开放平台获取
    appSecret: 'xxxxxxxxxxxxxxxxxxxxxxxx', // 从飞书开放平台获取
    domain: 'https://open.feishu.cn',      // 国内用这个，国际用 https://open.larksuite.com
  },
  
  // 多维表格配置
  bitable: {
    // 从 URL 获取：https://xxx.feishu.cn/base/bascnXXXXX?table=tblXXXXX
    appToken: 'bascnxxxxxxxxxxxxx',
    tableId: 'tblxxxxxxxxxxxxxx',
    
    // 字段映射（根据你的表格实际列名调整）
    fields: {
      title: '标题',      // 必填：知识库标题
      content: '内容',    // 必填：知识库内容
      category: '分类',   // 可选：用于分类存储
      tags: '标签',       // 可选：用于标签
      updatedAt: '更新时间', // 可选：最后更新时间
    },
  },
  
  // 输出配置
  output: {
    dir: '/home/openclaw/.openclaw/workspace/knowledge',
    byCategory: true,           // 是否按分类创建子目录
    filenameFormat: 'title',    // 'title' 或 'id'
  },
  
  // 同步配置
  sync: {
    pageSize: 500,
    cleanOrphaned: false,       // 是否删除本地有但表格中没有的文件
  },
};
