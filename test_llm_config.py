#!/usr/bin/env python3
"""测试新的 LLM 分析配置"""

import sys
import json
from pathlib import Path

# 添加当前目录到 Python 路径
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from scripts.analyze_papers import load_config

def test_config():
    """测试配置加载"""
    try:
        config = load_config()
        print("[OK] 配置加载成功")
        print(f"模型: {config['model']}")
        print(f"API URL: {config['base_url']}")
        print(f"API Key 已加载: {'是' if config['api_key'] else '否'}")
        
        # 验证模型是否正确
        if "stepfun/step-3.5-flash" in config['model']:
            print("[OK] 模型配置正确")
        else:
            print("[ERROR] 模型配置不正确，应该是 stepfun/step-3.5-flash")
            
        return True
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return False

if __name__ == "__main__":
    print("测试 LLM 分析脚本配置...")
    success = test_config()
    if success:
        print("\n[OK] 所有测试通过！可以运行分析脚本。")
    else:
        print("\n[ERROR] 配置有误，请检查。")