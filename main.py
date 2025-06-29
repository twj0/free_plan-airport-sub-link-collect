import os
import sys
import logging
import urllib.parse
import requests
from collections import OrderedDict

# 动态导入所有客户端
from clients import blue2sea_client, dabai_client, ikuuu_client, louwangzhiyu_client, wwn_client

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
OUTPUT_FILE = "merged_subscription.yaml"

# --- 任务定义 ---
# 定义每个任务需要调用的函数以及它在输出文件中的唯一标识符
TASKS = {
    "blue2sea": {
        "id": "blue2sea.com",
        "func": blue2sea_client.get_subscription,
        "needs_creds": False
    },
    "dabai": {
        "id": "dabai.in",
        "func": dabai_client.get_subscription,
        "needs_creds": True
    },
    "ikuuu": {
        "id": "ikuuu.one",
        "func": ikuuu_client.get_subscription,
        "needs_creds": True
    },
    "louwangzhiyu": {
        "id": "louwangzhiyu.xyz",
        "func": louwangzhiyu_client.get_subscription,
        "needs_creds": True
    },
    "wwn": {
        "id": "wwn.trx1.cyou",
        "func": wwn_client.get_subscription,
        "needs_creds": True
    }
}

# --- 订阅转换器配置 ---

SUB_CONVERTER_BACKEND = "subapi.v1.mk"
BASE_CONFIG_URL = "https://raw.githubusercontent.com/twj0/free_plan-airport-sub-link-collect/refs/heads/main/base.yaml" 

def read_existing_subscriptions(filename):
    """读取已有的订阅文件，并将其解析为字典以便更新。"""
    subs = OrderedDict()
    if not os.path.exists(filename):
        return subs
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or '://' not in line:
                continue
            # 通过任务ID来识别和映射已有链接
            for task_name, task_info in TASKS.items():
                if task_info['id'] in line:
                    subs[task_name] = line
                    break
    return subs

def run_tasks(task_names):
    """运行指定的任务并返回获取到的链接字典。"""
    all_links = {}
    for name in task_names:
        task = TASKS[name]
        logging.info(f"--- Running task: {name} ---")
        
        link = None
        if task['needs_creds']:
            email = os.environ.get(f"{name.upper()}_EMAIL")
            password = os.environ.get(f"{name.upper()}_PASSWORD")
            if not email or not password:
                logging.warning(f"Skipping {name}: Credentials not found in GitHub Secrets.")
                continue
            link = task['func'](email, password)
        else:
            link = task['func']()
            
        if link:
            logging.info(f"Success! Fetched link for {name}.")
            all_links[name] = link
        else:
            logging.error(f"Failed to fetch link for {name}.")
            
    return all_links

def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ['daily', 'weekly']:
        print("Usage: python main.py [daily|weekly]")
        sys.exit(1)
        
    run_mode = sys.argv[1]
    
    # 根据运行模式选择要执行的任务
    tasks_to_run = []
    if run_mode == 'daily':
        tasks_to_run = ['blue2sea']
    elif run_mode == 'weekly':
        tasks_to_run = ['dabai', 'ikuuu', 'louwangzhiyu', 'wwn']
        # 1. 获取所有原始订阅链接
    subscription_links = run_tasks(tasks_to_run)
    if not subscription_links:
        logging.warning("未能获取到任何订阅链接，任务终止。")
        return

     # 2. 构建指向订阅转换器的URL
    # 将我们的链接列表用'|'连接起来
    links_str = "|".join(subscription_links)
    
    # URL编码，确保链接中的特殊字符被正确处理
    encoded_links = urllib.parse.quote(links_str)
    encoded_config_url = urllib.parse.quote(BASE_CONFIG_URL)

    final_converter_url = f"https://{SUB_CONVERTER_BACKEND}/sub?target=clash&url={encoded_links}&insert=false&config={encoded_config_url}&emoji=true&new_name=true"
    
    logging.info(f"正在调用订阅转换器: {final_converter_url}")

    # 3. 从转换器获取最终的订阅内容
    try:
        response = requests.get(final_converter_url, timeout=30)
        response.raise_for_status()
        final_subscription_content = response.text

        # 4. 保存到文件
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(final_subscription_content)
        
        logging.info(f"--- 成功生成合并后的订阅文件: {OUTPUT_FILE}！ ---")

    except Exception as e:
        logging.error(f"调用订阅转换器或保存文件时出错: {e}")

if __name__ == "__main__":
    main()