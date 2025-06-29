import os
import sys
import logging
import requests
import yaml
import base64
from urllib.parse import urlparse

# --- 配置区域 ---
from clients import blue2sea_client, dabai_client, ikuuu_client, louwangzhiyu_client, wwn_client

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
OUTPUT_FILE = "merged_subscription.yaml"
BASE_CONFIG_FILE = "base.yaml"

TASKS = {
    "dabai":        {"tag": "[大白]",       "func": dabai_client.get_subscription,       "needs_creds": True},
    "ikuuu":        {"tag": "[ikuuu]",      "func": ikuuu_client.get_subscription,      "needs_creds": True},
    "wwn":          {"tag": "[华夏联盟]",     "func": wwn_client.get_subscription,     "needs_creds": True},
    "louwangzhiyu": {"tag": "[漏网之鱼]", "func": louwangzhiyu_client.get_subscription, "needs_creds": True},

}

def get_content_from_url(url):
    if not url: return None
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        logging.error(f"下载内容失败: {url}, 错误: {e}")
        return None

def parse_subscription_content(content):
    """
    解析订阅内容。支持Clash (YAML) 格式和Base64编码的节点列表。
    返回一个节点字典列表。
    """
    if not content: return []
    
    try:
        # CHANGED: 增加净化步骤，将所有Tab字符替换为2个空格，以修复格式错误的YAML。
        sanitized_content = content.replace('\t', '  ')
        data = yaml.safe_load(sanitized_content)
        if isinstance(data, dict) and 'proxies' in data and isinstance(data['proxies'], list):
            return data['proxies']
    except (yaml.YAMLError, AttributeError):
        try:
            content = ''.join(content.split())
            decoded_content = base64.b64decode(content).decode('utf-8')
            # 此处可以扩展为解析URI链接，但目前简化处理
            logging.warning("内容被识别为Base64，但当前版本不支持解析其中的URI。")
            return []
        except Exception:
            # 如果两种方式都失败了，静默处理，返回空列表
            logging.error("内容既不是有效的YAML(即使净化后)也不是Base64。")
            return []
            
    return []

def run_tasks_and_get_nodes(task_names):
    """
    运行指定的任务，获取、解析并标记所有节点。
    返回一个包含所有带标签节点的列表。
    """
    all_tagged_nodes = []
    for name in task_names:
        if name not in TASKS: continue
        
        task = TASKS[name]
        logging.info(f"--- 正在运行任务: {task['tag']} ---")

        raw_subscription_url = None
        if task['needs_creds']:
            email = os.environ.get(f"{name.upper()}_EMAIL")
            password = os.environ.get(f"{name.upper()}_PASSWORD")
            if not email or not password:
                logging.warning(f"跳过 {name}: 未在Secrets中设置凭据。")
                continue
            raw_subscription_url = task['func'](email, password)
        else:
            raw_subscription_url = task['func']()

        if not raw_subscription_url:
            logging.error(f"未能获取到 {name} 的订阅链接。")
            continue

        content = get_content_from_url(raw_subscription_url)
        if not content: continue

        nodes = parse_subscription_content(content)
        
        for node in nodes:
            if isinstance(node, dict) and 'name' in node:
                node['name'] = f"{task['tag']} {node['name']}"
        
        all_tagged_nodes.extend(nodes)
        logging.info(f"成功处理了 {len(nodes)} 个来自 {task['tag']} 的节点。")

    return all_tagged_nodes

def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ['daily', 'weekly']:
        print("用法: python main.py [daily|weekly]")
        sys.exit(1)
        
    run_mode = sys.argv[1]
    tasks_to_run = ['blue2sea'] if run_mode == 'daily' else ['dabai', 'ikuuu', 'wwn', 'louwangzhiyu']

    all_nodes = run_tasks_and_get_nodes(tasks_to_run)
    if not all_nodes:
        logging.warning("未能获取到任何节点，本次不更新订阅文件。")
        sys.exit(0)

    try:
        with open(BASE_CONFIG_FILE, 'r', encoding='utf-8') as f:
            base_config = yaml.safe_load(f)
    except Exception as e:
        logging.error(f"无法加载基础配置文件 '{BASE_CONFIG_FILE}': {e}")
        sys.exit(1)

    base_config['proxies'] = all_nodes
    all_node_names = [node['name'] for node in all_nodes if 'name' in node]

    categorized_node_names = {key: [] for key in TASKS.keys()}
    for node_name in all_node_names:
        for task_key, task_info in TASKS.items():
            if node_name.startswith(task_info['tag']):
                categorized_node_names[task_key].append(node_name)
                break

    for group in base_config.get('proxy-groups', []):
        new_proxies = []
        for proxy_name in group.get('proxies', []):
            if proxy_name == "[AUTO]":
                new_proxies.extend(all_node_names)
            elif proxy_name.startswith("[SITE:"):
                site_key = proxy_name.replace("[SITE:", "").replace("]", "")
                new_proxies.extend(categorized_node_names.get(site_key, []))
            else:
                new_proxies.append(proxy_name)
        group['proxies'] = new_proxies

    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(base_config, f, sort_keys=False, allow_unicode=True)
        logging.info(f"🎉 成功生成合并后的订阅文件: {OUTPUT_FILE}！")
    except Exception as e:
        logging.error(f"写入最终配置文件时出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()