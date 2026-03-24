// 飞书多维表格同步配置
module.exports = {
  feishu: {
    appId: 'cli_a924dc7790625bd3',
    appSecret: 'KfKqczGdsExKvXMq4m8HafrFc3WQx7t1',
    domain: 'https://open.feishu.cn',
  },
  
  bitable: {
    appToken: 'BFQjbYgHUaaAmwsYdubcZ5hWnc5',
    tableId: 'tblmjBEemH3THeWU',
    
    // 字段映射 - 需要根据实际表格列名调整
    fields: {
      title: '标题',
      content: '内容',
      category: '分类',
      tags: '标签',
      updatedAt: '更新时间',
    },
  },
  
  output: {
    dir: '/home/openclaw/.openclaw/workspace/knowledge',
    byCategory: true,
    filenameFormat: 'title',
  },
  
  sync: {
    pageSize: 500,
    cleanOrphaned: false,
  },
};
