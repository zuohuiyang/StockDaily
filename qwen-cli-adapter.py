#!/usr/bin/env python3
"""
Qwen CLI Adapter for OpenClaw
This script acts as a bridge between OpenClaw's CLI runner and Alibaba Cloud Qwen API.
"""

import sys
import json
import os
from typing import Dict, Any, Optional

# Import required modules
try:
    import requests
except ImportError:
    print("Error: requests module not found. Install with: pip install requests", file=sys.stderr)
    sys.exit(1)

class QwenCliAdapter:
    def __init__(self):
        self.api_key = os.environ.get('DASHSCOPE_API_KEY')
        if not self.api_key:
            print("Error: No API key found. Set DASHSCOPE_API_KEY.", file=sys.stderr)
            sys.exit(1)
        
        self.base_url = "https://coding.dashscope.aliyuncs.com/v1/chat/completions"
    
    def parse_args(self) -> Dict[str, Any]:
        """Parse command line arguments in the format expected by OpenClaw"""
        args = {}
        i = 0
        while i < len(sys.argv[1:]):
            arg = sys.argv[1:][i]
            if arg == '--model' and i + 1 < len(sys.argv[1:]):
                args['model'] = sys.argv[1:][i + 1]
                i += 2
            elif arg == '--append-system-prompt' and i + 1 < len(sys.argv[1:]):
                args['system_prompt'] = sys.argv[1:][i + 1]
                i += 2
            elif arg == '--session-id' and i + 1 < len(sys.argv[1:]):
                args['session_id'] = sys.argv[1:][i + 1]
                i += 2
            elif arg == '-p' and i + 1 < len(sys.argv[1:]):
                # The prompt comes after -p
                args['prompt'] = sys.argv[1:][i + 1]
                i += 2
            else:
                i += 1
        
        return args
    
    def call_qwen_api(self, prompt: str, system_prompt: Optional[str] = None, model: str = "qwen3-max-2026-01-23") -> Dict[str, Any]:
        """Call the Qwen API with the given prompt"""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        # Prepare messages in OpenAI format
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": 4096
        }
        
        try:
            response = requests.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            
            # Extract the response content
            output = result.get('output', {})
            choices = output.get('choices', [])
            if choices and len(choices) > 0:
                message = choices[0].get('message', {})
                content = message.get('content', '')
            else:
                content = ""
            
            return {
                "text": content,
                "session_id": "qwen-session-1",  # Simple session ID
                "usage": {
                    "input_tokens": result.get('usage', {}).get('input_tokens', 0),
                    "output_tokens": result.get('usage', {}).get('output_tokens', 0)
                }
            }
            
        except Exception as e:
            print(f"Error calling Qwen API: {e}", file=sys.stderr)
            return {"text": f"Error: {str(e)}", "session_id": "error-session"}
    
    def run(self):
        """Main execution method"""
        args = self.parse_args()
        
        prompt = args.get('prompt', '')
        system_prompt = args.get('system_prompt')
        model = args.get('model', 'qwen3-max-2026-01-23')
        session_id = args.get('session_id', 'default')
        
        if not prompt:
            print("Error: No prompt provided", file=sys.stderr)
            sys.exit(1)
        
        result = self.call_qwen_api(prompt, system_prompt, model)
        
        # Output in JSON format as expected by OpenClaw
        print(json.dumps(result, ensure_ascii=False))

def main():
    adapter = QwenCliAdapter()
    adapter.run()

if __name__ == "__main__":
    main()
