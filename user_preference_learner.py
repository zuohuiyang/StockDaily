#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户偏好学习系统 - 学习和适应用户交互偏好
"""

import json
import os
from datetime import datetime
from typing import Dict, Any

class UserPreferenceLearner:
    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.preference_file = f"memory/user_preferences_{user_id}.json"
        self.preferences = self._load_preferences()
        
    def _load_preferences(self) -> Dict[str, Any]:
        """加载用户偏好"""
        if os.path.exists(self.preference_file):
            try:
                with open(self.preference_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            'response_style': 'detailed',  # detailed, concise, balanced
            'detail_level': 0.7,          # 0.0-1.0
            'preferred_format': 'markdown', # markdown, plain, table
            'notification_frequency': 'normal', # low, normal, high
            'last_interaction': None,
            'interaction_count': 0,
            'feedback_score': 0.0,
            'preferred_topics': ['investment', 'performance', 'analysis']
        }
    
    def _save_preferences(self):
        """保存用户偏好"""
        os.makedirs('memory', exist_ok=True)
        with open(self.preference_file, 'w', encoding='utf-8') as f:
            json.dump(self.preferences, f, ensure_ascii=False, indent=2)
    
    def update_from_interaction(self, interaction_data: Dict[str, Any]):
        """从交互中学习用户偏好"""
        self.preferences['interaction_count'] += 1
        self.preferences['last_interaction'] = datetime.now().isoformat()
        
        # 分析用户反馈
        if 'explicit_feedback' in interaction_data:
            feedback = interaction_data['explicit_feedback']
            if feedback == 'too_detailed':
                self.preferences['response_style'] = 'concise'
                self.preferences['detail_level'] = max(0.1, self.preferences['detail_level'] - 0.2)
            elif feedback == 'not_detailed_enough':
                self.preferences['response_style'] = 'detailed'
                self.preferences['detail_level'] = min(1.0, self.preferences['detail_level'] + 0.2)
            elif feedback == 'good':
                self.preferences['feedback_score'] = min(1.0, self.preferences['feedback_score'] + 0.1)
        
        # 分析交互模式
        if 'response_time_preference' in interaction_data:
            if interaction_data['response_time_preference'] == 'fast':
                self.preferences['detail_level'] = max(0.1, self.preferences['detail_level'] - 0.1)
            elif interaction_data['response_time_preference'] == 'thorough':
                self.preferences['detail_level'] = min(1.0, self.preferences['detail_level'] + 0.1)
        
        self._save_preferences()
    
    def get_adapted_response_params(self) -> Dict[str, Any]:
        """获取适应性响应参数"""
        return {
            'style': self.preferences['response_style'],
            'detail_level': self.preferences['detail_level'],
            'format': self.preferences['preferred_format'],
            'topics': self.preferences['preferred_topics']
        }
    
    def generate_personalized_response(self, base_content: str, analysis_data: Dict[str, Any]) -> str:
        """生成个性化响应"""
        params = self.get_adapted_response_params()
        detail_level = params['detail_level']
        
        if detail_level < 0.3:
            # 简洁模式
            return self._generate_concise_response(base_content, analysis_data)
        elif detail_level > 0.7:
            # 详细模式
            return self._generate_detailed_response(base_content, analysis_data)
        else:
            # 平衡模式
            return self._generate_balanced_response(base_content, analysis_data)
    
    def _generate_concise_response(self, base_content: str, analysis_data: Dict[str, Any]) -> str:
        """生成简洁响应"""
        total_value = analysis_data.get('total_value', 0)
        recommendations = analysis_data.get('recommendations', [])
        
        lines = []
        lines.append("📈 投资组合简报")
        lines.append(f"总资产: {total_value:.2f} CNY")
        
        if recommendations:
            lines.append("主要建议:")
            for rec in recommendations[:2]:  # 只显示前2条建议
                lines.append(f"• {rec}")
        
        return "\n".join(lines)
    
    def _generate_detailed_response(self, base_content: str, analysis_data: Dict[str, Any]) -> str:
        """生成详细响应"""
        # 返回完整内容
        return base_content
    
    def _generate_balanced_response(self, base_content: str, analysis_data: Dict[str, Any]) -> str:
        """生成平衡响应"""
        # 返回中等详细程度的内容
        lines = base_content.split('\n')
        if len(lines) > 20:
            # 如果内容太长，截取关键部分
            key_sections = []
            current_section = []
            
            for line in lines:
                if line.startswith('# ') or line.startswith('## '):
                    if current_section:
                        key_sections.extend(current_section)
                        current_section = []
                    current_section.append(line)
                elif line.strip():
                    current_section.append(line)
            
            if current_section:
                key_sections.extend(current_section)
            
            return '\n'.join(key_sections[:15]) + "\n\n[查看更多详情请要求详细报告]"
        else:
            return base_content

def main():
    """测试函数"""
    learner = UserPreferenceLearner("test_user")
    
    # 模拟交互
    interaction_data = {
        'explicit_feedback': 'good',
        'response_time_preference': 'thorough'
    }
    
    learner.update_from_interaction(interaction_data)
    
    # 生成个性化响应
    base_content = "# 投资报告\n详细内容..."
    analysis_data = {'total_value': 16037.22, 'recommendations': ['建议1', '建议2']}
    
    personalized_response = learner.generate_personalized_response(base_content, analysis_data)
    print(personalized_response)

if __name__ == "__main__":
    main()