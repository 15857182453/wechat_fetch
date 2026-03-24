#!/usr/bin/env node
/**
 * 测试知识库问答效果
 */

const fs = require('fs');
const path = require('path');

const KNOWLEDGE_DIR = '/home/openclaw/.openclaw/workspace/knowledge';

// 搜索知识库
function searchKnowledge(query, limit = 3) {
  const files = fs.readdirSync(KNOWLEDGE_DIR);
  const results = [];
  
  const queryLower = query.toLowerCase();
  
  for (const file of files) {
    if (!file.endsWith('.md')) continue;
    
    const filePath = path.join(KNOWLEDGE_DIR, file);
    const content = fs.readFileSync(filePath, 'utf8');
    
    // 简单的相关性评分
    let score = 0;
    const contentLower = content.toLowerCase();
    
    // 检查关键词匹配
    const queryWords = queryLower.split(/\s+/).filter(w => w.length > 1);
    for (const word of queryWords) {
      const matches = contentLower.split(word).length - 1;
      if (matches > 0) {
        score += matches * 2;
      }
      
      // 标题匹配权重更高
      if (file.toLowerCase().includes(word)) {
        score += 10;
      }
    }
    
    if (score > 0) {
      results.push({
        file,
        score,
        content: content.substring(0, 500), // 只取前 500 字符
        fullPath: filePath,
      });
    }
  }
  
  // 按分数排序
  return results.sort((a, b) => b.score - a.score).slice(0, limit);
}

// 提取答案
function extractAnswer(query, articleContent) {
  // 查找包含问题关键词的段落
  const paragraphs = articleContent.split(/\n\n+/);
  const relevantParagraphs = [];
  
  const queryWords = query.split(/[\s,?！]+/).filter(w => w.length > 2);
  
  for (const para of paragraphs) {
    let matchCount = 0;
    for (const word of queryWords) {
      if (para.includes(word)) {
        matchCount++;
      }
    }
    
    if (matchCount >= 1 && para.length > 20) {
      relevantParagraphs.push(para);
    }
  }
  
  return relevantParagraphs.slice(0, 3).join('\n\n');
}

// 主函数
function testQA(question) {
  console.log('\n' + '='.repeat(60));
  console.log(`🤔 问题：${question}`);
  console.log('='.repeat(60));
  
  // 搜索相关知识
  const results = searchKnowledge(question);
  
  if (results.length === 0) {
    console.log('\n❌ 未找到相关知识库内容\n');
    return;
  }
  
  console.log(`\n📚 找到 ${results.length} 篇相关文章:\n`);
  
  results.forEach((result, index) => {
    console.log(`${index + 1}. ${result.file.replace('.md', '')}`);
    console.log(`   相关性评分：${result.score}`);
    console.log(`   路径：${result.fullPath}\n`);
  });
  
  // 生成答案
  console.log('\n' + '-'.repeat(60));
  console.log('💡 参考答案:\n');
  
  const bestMatch = results[0];
  const fullContent = fs.readFileSync(bestMatch.fullPath, 'utf8');
  const answer = extractAnswer(question, fullContent);
  
  console.log(`根据知识库文章 **${bestMatch.file.replace('.md', '')}**：\n`);
  console.log(answer);
  
  console.log('\n' + '-'.repeat(60));
  console.log(`\n📖 完整文章：${bestMatch.fullPath}\n`);
}

// 测试问题
const testQuestions = [
  '肩周炎怎么治疗？',
  '失眠怎么办？',
  '如何预防糖尿病？',
  '中医养生的方法有哪些？',
];

// 运行测试
console.log('\n🧪 知识库问答测试');
console.log('知识库位置:', KNOWLEDGE_DIR);
console.log('文章数量:', fs.readdirSync(KNOWLEDGE_DIR).filter(f => f.endsWith('.md')).length);

const question = process.argv[2] || testQuestions[0];
testQA(question);
