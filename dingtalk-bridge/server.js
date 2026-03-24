/**
 * 钉钉消息回调服务器
 * 接收钉钉群消息 → 转发给 OpenClaw → 发送回复回钉钉
 */

const express = require('express');
const crypto = require('crypto');
const axios = require('axios');

const app = express();
app.use(express.json());

// ========== 配置区 ==========
const CONFIG = {
  // 钉钉应用配置
  dingtalk: {
    appKey: 'YOUR_APP_KEY',
    appSecret: 'YOUR_APP_SECRET',
    agentId: 'YOUR_AGENT_ID',
  },
  
  // OpenClaw 配置
  openclaw: {
    // OpenClaw 的 HTTP 接口或消息队列地址
    endpoint: 'http://localhost:3000/api/message',
  },
  
  // 服务器配置
  server: {
    port: 3001,
    // 钉钉回调验证用
    token: 'YOUR_CALLBACK_TOKEN',
    encodingAesKey: 'YOUR_ENCODING_AES_KEY',
  },
};
// ===========================

// 获取钉钉 access_token
async function getDingTalkAccessToken() {
  const url = 'https://oapi.dingtalk.com/gettoken';
  const res = await axios.get(url, {
    params: {
      appkey: CONFIG.dingtalk.appKey,
      appsecret: CONFIG.dingtalk.appSecret,
    },
  });
  return res.data.access_token;
}

// 发送消息到钉钉
async function sendToDingTalk(conversationId, content) {
  const accessToken = await getDingTalkAccessToken();
  const url = 'https://oapi.dingtalk.com/topapi/message/corpconversation/asyncsend_v2';
  
  await axios.post(url, {
    agent_id: CONFIG.dingtalk.agentId,
    userid_list: '@all', // 或者指定用户
    msgtype: 'text',
    text: {
      content: content,
    },
  }, {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
  });
}

// 验证钉钉回调签名
function verifySignature(req) {
  const signature = req.headers['x-dingtalk-signature'];
  const timestamp = req.headers['x-dingtalk-timestamp'];
  const token = CONFIG.server.token;
  
  const signStr = `${timestamp}\n${token}`;
  const expectedSig = crypto
    .createHmac('sha256', token)
    .update(signStr)
    .digest('base64');
  
  return signature === expectedSig;
}

// 钉钉回调入口
app.post('/dingtalk/callback', async (req, res) => {
  // 验证签名
  if (!verifySignature(req)) {
    return res.status(401).json({ error: 'Invalid signature' });
  }
  
  const { eventType, chatbotUserId, conversationId, text } = req.body;
  
  console.log(`[钉钉消息] 类型: ${eventType}, 用户: ${chatbotUserId}, 内容: ${text}`);
  
  // 如果是@机器人的消息
  if (eventType === 'chatbot_message' && text) {
    try {
      // 转发给 OpenClaw 处理
      const openclawResponse = await axios.post(CONFIG.openclaw.endpoint, {
        source: 'dingtalk',
        conversationId,
        message: text,
        userId: chatbotUserId,
      });
      
      // 发送回复回钉钉
      if (openclawResponse.data.reply) {
        await sendToDingTalk(conversationId, openclawResponse.data.reply);
        console.log(`[回复已发送] ${openclawResponse.data.reply}`);
      }
      
      res.json({ success: true });
    } catch (error) {
      console.error('[处理失败]', error);
      res.status(500).json({ error: 'Processing failed' });
    }
  } else {
    res.json({ success: true });
  }
});

// 健康检查
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// 启动服务器
app.listen(CONFIG.server.port, () => {
  console.log(`🤖 钉钉桥接服务器运行在 http://localhost:${CONFIG.server.port}`);
  console.log(`回调 URL: http://YOUR_PUBLIC_IP:${CONFIG.server.port}/dingtalk/callback`);
});
