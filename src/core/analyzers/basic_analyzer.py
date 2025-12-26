"""
基础文本分析器模块 - 提供不依赖外部API的简单文本分析功能
"""
import re
from typing import List, Dict, Any
import jieba
import jieba.analyse
from collections import Counter
from src.utils.logging import logger

async def perform_basic_analysis(text: str, options: List[str]) -> Dict[str, Any]:
    """
    执行基础文本分析，不依赖外部API
    
    参数:
        text: 要分析的文本内容
        options: 要执行的分析选项列表 ['summary', 'keywords', 'statistics', 'sentiment']
        
    返回:
        包含各种分析结果的字典
    """
    logger.info(f"开始执行基础文本分析，选择的选项: {options}")
    
    if not text or len(text.strip()) == 0:
        logger.warning("文本内容为空，无法进行分析")
        return {"error": "文本内容为空"}
    
    result = {}
    
    # 基本文本统计
    if "statistics" in options or "basic_stats" in options:
        logger.info("执行基础统计分析")
        stats = analyze_text_statistics(text)
        result["statistics"] = stats
    
    # 关键词提取
    if "keywords" in options:
        logger.info("执行关键词提取")
        keywords = extract_keywords(text)
        result["keywords"] = keywords
    
    # 简单摘要（提取重要句子）
    if "summary" in options:
        logger.info("执行文本摘要")
        summary = generate_summary(text)
        result["summary"] = summary
    
    # 简单的情感分析
    if "sentiment" in options:
        logger.info("执行简单情感分析")
        sentiment = simple_sentiment_analysis(text)
        result["sentiment"] = sentiment
    
    # 词频分析
    if "word_frequency" in options:
        logger.info("执行词频分析")
        word_freq = analyze_word_frequency(text)
        result["word_frequency"] = word_freq
    
    # 记录完成的分析种类
    result["analyzed_options"] = options
    result["analysis_type"] = "basic"
    
    logger.info("基础文本分析完成")
    return result

def analyze_text_statistics(text: str) -> Dict[str, Any]:
    """分析文本的基本统计信息"""
    char_count = len(text)
    word_count = len(re.findall(r'\b\w+\b', text))
    
    # 计算中文词数（使用jieba分词）
    chinese_words = list(jieba.cut(text))
    chinese_word_count = len(chinese_words)
    
    # 句子数
    sentences = re.split(r'[。！？.!?]+', text)
    sentence_count = len([s for s in sentences if len(s.strip()) > 0])
    
    # 段落数
    paragraphs = text.split('\n\n')
    paragraph_count = len([p for p in paragraphs if len(p.strip()) > 0])
    
    return {
        "character_count": char_count,
        "word_count": max(word_count, chinese_word_count),  # 取较大的词数
        "sentence_count": sentence_count,
        "paragraph_count": paragraph_count,
        "average_sentence_length": round(char_count / max(sentence_count, 1), 2),
        "average_paragraph_length": round(char_count / max(paragraph_count, 1), 2)
    }

def extract_keywords(text: str, topk: int = 10) -> List[Dict[str, Any]]:
    """提取文本中的关键词"""
    # 使用jieba的TextRank算法提取关键词
    keywords_textrank = jieba.analyse.textrank(text, topK=topk, withWeight=True)
    
    # 使用TF-IDF算法提取关键词
    keywords_tfidf = jieba.analyse.extract_tags(text, topK=topk, withWeight=True)
    
    # 合并结果（取权重较高的）
    keywords_dict = {}
    for word, weight in keywords_textrank:
        keywords_dict[word] = {"word": word, "weight": weight, "method": "textrank"}
    
    for word, weight in keywords_tfidf:
        if word in keywords_dict:
            # 如果TF-IDF权重更大，更新
            if weight > keywords_dict[word]["weight"]:
                keywords_dict[word] = {"word": word, "weight": weight, "method": "tfidf"}
        else:
            keywords_dict[word] = {"word": word, "weight": weight, "method": "tfidf"}
    
    # 转换为列表并排序
    keywords_list = list(keywords_dict.values())
    keywords_list.sort(key=lambda x: x["weight"], reverse=True)
    
    # 只返回前topk个
    return keywords_list[:topk]

def generate_summary(text: str, sentence_count: int = 3) -> str:
    """生成文本摘要（提取重要句子）"""
    # 分句
    sentences = re.split(r'[。！？.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 0]
    
    if len(sentences) <= sentence_count:
        return text
    
    # 为每个句子计算重要性得分（基于关键词的简单方法）
    keywords = [kw["word"] for kw in extract_keywords(text, topk=20)]
    
    sentence_scores = []
    for sentence in sentences:
        score = 0
        for keyword in keywords:
            if keyword in sentence:
                score += 1
        # 偏好中等长度的句子
        length_factor = min(1.0, len(sentence) / 100)  # 句子长度影响因子
        score *= length_factor
        sentence_scores.append((sentence, score))
    
    # 选择得分最高的句子
    sentence_scores.sort(key=lambda x: x[1], reverse=True)
    summary_sentences = [s[0] for s in sentence_scores[:sentence_count]]
    
    # 按原文顺序排列
    ordered_summary = []
    for sentence in sentences:
        if sentence in summary_sentences:
            ordered_summary.append(sentence)
            if len(ordered_summary) >= sentence_count:
                break
    
    return "。".join(ordered_summary) + "。"

def simple_sentiment_analysis(text: str) -> Dict[str, Any]:
    """进行简单的情感分析（基于关键词匹配）"""
    # 简单的情感词典（示例）
    positive_words = ["喜欢", "好", "优秀", "出色", "精彩", "美好", "快乐", "优质", 
                     "卓越", "精彩", "满意", "开心", "高兴", "成功", "美妙"]
    negative_words = ["糟糕", "失望", "差", "坏", "不满", "痛苦", "悲伤", "遗憾", 
                     "失败", "苦恼", "困难", "反对", "厌恶", "不好", "讨厌"]
    
    # 分词
    words = list(jieba.cut(text))
    
    # 计算积极和消极词的出现次数
    positive_count = sum(1 for word in words if word in positive_words)
    negative_count = sum(1 for word in words if word in negative_words)
    
    # 确定主导情感
    total = positive_count + negative_count
    if total == 0:
        sentiment = "neutral"
        confidence = 0.5
    else:
        positive_ratio = positive_count / total
        if positive_ratio > 0.6:
            sentiment = "positive"
            confidence = positive_ratio
        elif positive_ratio < 0.4:
            sentiment = "negative"
            confidence = 1 - positive_ratio
        else:
            sentiment = "neutral"
            confidence = 0.5
    
    return {
        "sentiment": sentiment,
        "confidence": round(confidence, 2),
        "positive_count": positive_count,
        "negative_count": negative_count,
        "method": "basic_keyword_matching"  # 说明使用的方法
    }

def analyze_word_frequency(text: str, top_n: int = 20) -> List[Dict[str, Any]]:
    """分析词频"""
    # 分词
    words = list(jieba.cut(text))
    
    # 过滤掉停用词和标点符号
    stopwords = set(["的", "了", "和", "是", "在", "我", "有", "这", "你", "也", "都", "就", "不", "与", "之", "着"])
    filtered_words = [word for word in words if len(word) > 1 and word not in stopwords]
    
    # 统计词频
    word_counter = Counter(filtered_words)
    
    # 转换为列表
    word_freq_list = [{"word": word, "count": count} for word, count in word_counter.most_common(top_n)]
    
    return word_freq_list 