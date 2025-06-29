import os
import sys
import logging
import requests
import yaml  # 需要 PyYAML 库
import base64
from urllib.parse import urlparse

# --- 配置区域 ---
# 将客户端导入的语句放在这里
from clients import blue2sea_client, dabai_client, ikuuu_client, louwangzhiyu_client, wwn_client

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
OUTPUT_FILE = "merged_subscription.yaml"
BASE_CONFIG_FILE = "base.yaml"

# 任务定义：将每个任务与它的处理函数和唯一标识符关联起来
# 'tag' 将作为节点名称的前缀
TASKS = {
    "dabai":        {"tag": "[大白]",       "func": dabai_client.get_subscription,       "needs_creds": True},
    "ikuuu":        {"tag": "[ikuuu]",      "func": ikuuu_client.get_subscription,      "needs_creds": True},
    "wwn":          {"tag": "[华夏联盟]",     "func": wwn_client.get_subscription,     "needs_creds": True},
    "louwangzhiyu": {"tag": "[漏网之鱼]", "func": louwangzhiyu_client.get_subscription, "needs_creds": True},
    "blue2sea":     {"tag": "[Blue2sea]",   "func": blue2sea_client.get_subscription,   "needs_creds": False},
}

def get_content_from_url(url):
    """从URL下载内容，支持HTTP和文件路径。"""
    if url.startswith('http'):
        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logging.error(f"下载内容失败: {url}, 错误: {e}")
            return None
    elif os.path.exists(url):
        with open(url, 'r', encoding='utf-8') as f:
            return f.read()
    return None

def parse_subscription_content(content):
    """
    解析订阅内容。支持Clash (YAML) 格式和Base64编码的节点列表。
    返回一个节点字典列表。
    """
    try:
        # 尝试作为YAML解析 (Clash配置)
        data = yaml.safe_load(content)
        if isinstance(data, dict) and 'proxies' in data and isinstance(data['proxies'], list):
            return data['proxies']
    except (yaml.YAMLError, AttributeError):
        # 如果YAML解析失败，尝试作为Base64解码
        try:
            # 移除内容中的所有空白字符
            content = ''.join(content.split())
            decoded_content = base64.b64decode(content).decode('utf-8')
            # 此时我们有了一个节点URI列表，但这需要进一步解析，暂时简化处理
            # 这是一个可以未来扩展的地方
            logging.warning("内容被识别为Base64，但当前版本不支持解析其中的URI。")
            return []
        except (base64.binascii.Error, UnicodeDecodeError) as e:
            logging.error(f"内容既不是有效的YAML也不是Base64: {e}")
            return []
    return []

def run_tasks_and_get_nodes(task_names):
    """
    运行指定的任务，获取、解析并标记所有节点。
    返回一个包含所有带标签节点的列表。
    """
    all_tagged_nodes = []
    for name in task_names:
        if name not in TASKS:
            continue
        
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
        if not content:
            continue

        nodes = parse_subscription_content(content)
        
        # 为每个节点打上来源标签
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

    # 1. 运行任务并获取所有处理过的节点
    all_nodes = run_tasks_and_get_nodes(tasks_to_run)
    if not all_nodes:
        logging.warning("未能获取到任何节点，本次不更新订阅文件。")
        sys.exit(0)

    # 2. 加载基础配置模板
    try:
        with open(BASE_CONFIG_FILE, 'r', encoding='utf-8') as f:
            base_config = yaml.safe_load(f)
    except Exception as e:
        logging.error(f"无法加载基础配置文件 '{BASE_CONFIG_FILE}': {e}")
        sys.exit(1)

    # 3. 将节点注入模板
    base_config['proxies'] = all_nodes
    all_node_names = [node['name'] for node in all_nodes if 'name' in node]

    # 4. 智能填充代理组
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

    # 5. 写入最终的配置文件
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            # 使用yaml.dump来确保输出是有效的YAML格式
            # sort_keys=False 保持原始顺序，allow_unicode=True 支持中文
            yaml.dump(base_config, f, sort_keys=False, allow_unicode=True)
        logging.info(f"🎉 成功生成合并后的订阅文件: {OUTPUT_FILE}！")
    except Exception as e:
        logging.error(f"写入最终配置文件时出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()