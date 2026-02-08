#!/usr/bin/env python3
"""查询 OpenRouter API 使用情况和剩余配额"""

import json
import requests
from pathlib import Path

def load_config():
    home = Path.home()
    config_path = home / ".openclaw" / "openclaw.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    with open(config_path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)
    openrouter = cfg["models"]["providers"]["openrouter"]
    return {
        "api_key": openrouter["apiKey"],
        "base_url": openrouter["baseUrl"]
    }

def check_usage():
    config = load_config()
    api_key = config["api_key"]
    base_url = config["base_url"]

    # 查询密钥信息
    key_info_url = "https://openrouter.ai/api/v1/key"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        resp = requests.get(key_info_url, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # 提取关键信息
        key_data = data.get("data", {})
        print("=" * 60)
        print("OpenRouter API 使用情况")
        print("=" * 60)
        print(f"API 密钥标签: {key_data.get('label', 'N/A')}")
        print(f"是否免费套餐: {key_data.get('is_free_tier', False)}")
        print()
        print("[*] 额度限制:")
        print(f"  总限制 (limit): {key_data.get('limit', 'N/A')}")
        print(f"  剩余额度 (limit_remaining): {key_data.get('limit_remaining', 'N/A')}")
        print(f"  限制重置类型 (limit_reset): {key_data.get('limit_reset', 'N/A')}")
        print(f"  包含 BYOK: {key_data.get('include_byok_in_limit', False)}")
        print()
        print("[*] 使用情况:")
        print(f"  总使用量 (usage): {key_data.get('usage', 0)}")
        print(f"  今日使用 (usage_daily): {key_data.get('usage_daily', 0)}")
        print(f"  本周使用 (usage_weekly): {key_data.get('usage_weekly', 0)}")
        print(f"  本月使用 (usage_monthly): {key_data.get('usage_monthly', 0)}")
        print()
        print("[*] BYOK 使用:")
        print(f"  BYOK 总使用: {key_data.get('byok_usage', 0)}")
        print(f"  BYOK 今日: {key_data.get('byok_usage_daily', 0)}")
        print(f"  BYOK 本周: {key_data.get('byok_usage_weekly', 0)}")
        print(f"  BYOK 本月: {key_data.get('byok_usage_monthly', 0)}")
        print("=" * 60)

        # 计算剩余百分比
        limit = key_data.get('limit')
        remaining = key_data.get('limit_remaining')
        if limit and remaining is not None:
            pct = (remaining / limit) * 100
            print(f"剩余额度: {remaining}/{limit} ({pct:.1f}%)")

            if remaining <= 0:
                print("[!] 警告: API 额度已用尽！")
            elif remaining < limit * 0.1:
                print("[!] 警告: API 额度不足 10%！")
            elif remaining < limit * 0.5:
                print("[i] 提示: API 额度剩余少于 50%")
        else:
            print("额度信息: 无限制 (unlimited)")

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print("[!] 认证失败: API Key 无效")
        elif e.response.status_code == 402:
            print("[!] 余额不足: 账户余额为负")
        else:
            print(f"[!] HTTP 错误: {e}")
    except Exception as e:
        print(f"[!] 查询失败: {e}")

if __name__ == "__main__":
    check_usage()
