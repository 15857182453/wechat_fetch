// 配置文件 - 复制为 config.js 并填入你的配置

module.exports = {
  // 钉钉应用配置（从钉钉开放平台获取）
  dingtalk: {
    appKey: 'dingxxxxxxxxxxxxxx',
    appSecret: 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
    agentId: '123456789',
  },
  
  // OpenClaw 配置
  openclaw: {
    // 如果用本地 OpenClaw
    endpoint: 'http://localhost:3000/api/message',
    
    // 如果用远程 OpenClaw，改成公网地址
    // endpoint: 'https://your-openclaw-server.com/api/message',
  },
  
  // 服务器配置
  server: {
    port: 3001,
    // 回调 Token（自己设置，用于验证钉钉回调）
    token: 'your_callback_token_here',
    // AES 加密密钥（钉钉要求）
    encodingAesKey: 'your_aes_key_here',
  },
};
