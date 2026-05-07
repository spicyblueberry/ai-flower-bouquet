"""
RAG花语知识检索引擎（轻量版）
不依赖外网下载，使用关键词匹配
"""

import json
import os
from typing import List, Dict, Any

class FlowerRAGEngine:
    def __init__(self, knowledge_path: str = None):
        """初始化RAG引擎，加载知识库"""
        # 自动查找文件路径（适配你的文件夹结构）
        if knowledge_path is None:
            # 获取当前文件所在目录（backend）
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # 你的文件在 backend/knowledge_base/ 里
            knowledge_path = os.path.join(current_dir, "knowledge_base", "flower_knowledge.json")
        
        try:
            with open(knowledge_path, "r", encoding="utf-8") as f:
                self.flower_data = json.load(f)
            print(f"[RAG] 已加载 {len(self.flower_data)} 种花材，使用关键词匹配模式")
        except FileNotFoundError:
            print(f"[RAG] 错误：找不到文件 {knowledge_path}")
            self.flower_data = []
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """关键词匹配检索"""
        if not self.flower_data:
            return []
            
        query = query.lower()
        keywords = set(query.replace("、", " ").split())
        
        scored_flowers = []
        for flower in self.flower_data:
            score = 0
            search_text = (
                flower.get("name", "") + flower.get("color", "") + flower.get("language", "") + 
                " ".join(flower.get("occasion", [])) + " ".join(flower.get("target", [])) +
                flower.get("style", "") + flower.get("description", "")
            ).lower()
            
            for kw in keywords:
                if kw in search_text:
                    score += 1
            
            if score > 0:
                scored_flowers.append((score, flower))
        
        # 按分数排序
        scored_flowers.sort(key=lambda x: x[0], reverse=True)
        
        # 取前 top_k 个，只返回 flower 对象
        results = []
        for i in range(min(top_k, len(scored_flowers))):
            results.append(scored_flowers[i][1].copy())
        
        return results


if __name__ == "__main__":
    engine = FlowerRAGEngine()
    results = engine.search("送女朋友 粉色 浪漫 日常惊喜")
    print("\n=== 检索结果 ===")
    for r in results:
        print(f"{r['name']} - {r['language']}")