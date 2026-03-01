#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能记忆管理系统 - 自动识别重要事件并管理记忆
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any

class SmartMemoryManager:
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.memory_dir = os.path.join(workspace_path, 'memory')
        self.long_term_memory_path = os.path.join(workspace_path, 'MEMORY.md')
        
        # 确保记忆目录存在
        os.makedirs(self.memory_dir, exist_ok=True)
    
    def identify_important_events(self, conversation_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """识别重要事件"""
        important_events = []
        
        # 关键词识别重要事件
        important_keywords = [
            '记住', '重要', '关键', '必须', '约定', '规则', 
            '优化', '升级', '改进', '问题', '错误', '修复'
        ]
        
        messages = conversation_data.get('messages', [])
        for message in messages:
            content = message.get('content', '')
            sender = message.get('sender', '')
            
            # 检查是否包含重要关键词
            if any(keyword in content for keyword in important_keywords):
                event = {
                    'timestamp': message.get('timestamp', datetime.now().isoformat()),
                    'sender': sender,
                    'content': content,
                    'type': 'important_event',
                    'keywords': [kw for kw in important_keywords if kw in content]
                }
                important_events.append(event)
        
        return important_events
    
    def save_daily_memory(self, events: List[Dict[str, Any]], date: str = None) -> str:
        """保存日常记忆"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        memory_file = os.path.join(self.memory_dir, f'{date}.md')
        
        with open(memory_file, 'a', encoding='utf-8') as f:
            f.write(f"\n## {datetime.now().strftime('%H:%M:%S')} - 智能记忆记录\n")
            for event in events:
                f.write(f"- **{event['sender']}**: {event['content']}\n")
                if event['keywords']:
                    f.write(f"  - 关键词: {', '.join(event['keywords'])}\n")
        
        return memory_file
    
    def update_long_term_memory(self, events: List[Dict[str, Any]]) -> bool:
        """更新长期记忆"""
        try:
            # 读取现有的长期记忆
            existing_content = ""
            if os.path.exists(self.long_term_memory_path):
                with open(self.long_term_memory_path, 'r', encoding='utf-8') as f:
                    existing_content = f.read()
            
            # 准备新的长期记忆内容
            new_content_lines = []
            for event in events:
                # 避免重复添加
                event_content = f"- {event['content']}"
                if event_content not in existing_content:
                    new_content_lines.append(event_content)
            
            if new_content_lines:
                # 追加到长期记忆文件
                with open(self.long_term_memory_path, 'a', encoding='utf-8') as f:
                    f.write("\n## 自动学习的重要信息\n")
                    for line in new_content_lines:
                        f.write(f"{line}\n")
                
                return True
            
            return False
            
        except Exception as e:
            print(f"更新长期记忆失败: {e}")
            return False
    
    def cleanup_old_memories(self, days_to_keep: int = 30) -> int:
        """清理旧的记忆文件"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        cleaned_count = 0
        
        for filename in os.listdir(self.memory_dir):
            if filename.endswith('.md'):
                try:
                    file_date_str = filename.replace('.md', '')
                    file_date = datetime.strptime(file_date_str, '%Y-%m-%d')
                    
                    if file_date < cutoff_date:
                        os.remove(os.path.join(self.memory_dir, filename))
                        cleaned_count += 1
                        
                except ValueError:
                    # 跳过不符合日期格式的文件
                    continue
        
        return cleaned_count
    
    def semantic_search_memory(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """语义搜索记忆"""
        results = []
        
        # 简单的关键词匹配（实际应用中可以使用更复杂的语义搜索）
        search_terms = query.lower().split()
        
        # 搜索日常记忆
        for filename in sorted(os.listdir(self.memory_dir), reverse=True):
            if filename.endswith('.md'):
                file_path = os.path.join(self.memory_dir, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read().lower()
                        
                    # 计算匹配度
                    match_score = sum(1 for term in search_terms if term in content)
                    if match_score > 0:
                        results.append({
                            'file': filename,
                            'score': match_score,
                            'path': file_path
                        })
                        
                        if len(results) >= max_results:
                            break
                            
                except Exception as e:
                    continue
        
        # 按匹配度排序
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:max_results]

def main():
    """测试函数"""
    workspace_path = '/home/admin/.openclaw/workspace-wecom-group-wradsgkqaaewlr5s-tt0mr7r7n1d7ixq'
    manager = SmartMemoryManager(workspace_path)
    
    # 测试数据
    test_conversation = {
        'messages': [
            {
                'timestamp': '2026-02-28T10:30:00',
                'sender': 'YangZuoHui',
                'content': '记住每次回复都要记录耗时'
            },
            {
                'timestamp': '2026-02-28T10:31:00', 
                'sender': 'Assistant',
                'content': '好的，我会记住这个重要规则'
            }
        ]
    }
    
    # 识别重要事件
    events = manager.identify_important_events(test_conversation)
    print(f"识别到 {len(events)} 个重要事件")
    
    # 保存日常记忆
    memory_file = manager.save_daily_memory(events)
    print(f"日常记忆已保存到: {memory_file}")
    
    # 更新长期记忆
    updated = manager.update_long_term_memory(events)
    print(f"长期记忆更新: {'成功' if updated else '无新内容'}")
    
    # 清理旧记忆
    cleaned = manager.cleanup_old_memories(days_to_keep=7)
    print(f"清理了 {cleaned} 个旧记忆文件")
    
    # 测试搜索
    search_results = manager.semantic_search_memory("回复耗时")
    print(f"搜索结果: {len(search_results)} 个匹配")

if __name__ == "__main__":
    main()