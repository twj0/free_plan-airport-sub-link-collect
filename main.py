import os
import sys
import logging
from collections import OrderedDict

# 动态导入所有客户端
from clients import blue2sea_client, dabai_client, ikuuu_client, louwangzhiyu_client, wwn_client

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
OUTPUT_FILE = "subscriptions.txt"

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
    new_links = {}
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
            new_links[name] = link
        else:
            logging.error(f"Failed to fetch link for {name}.")
            
    return new_links

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

    # 核心逻辑
    existing_subs = read_existing_subscriptions(OUTPUT_FILE)
    newly_fetched_subs = run_tasks(tasks_to_run)
    
    # 更新订阅字典，用新获取的链接覆盖旧的
    final_subs = existing_subs
    final_subs.update(newly_fetched_subs)
    
    # 写入文件
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for task_name, link in final_subs.items():
            f.write(link + "\n")
            
    logging.info(f"--- Subscription file '{OUTPUT_FILE}' updated successfully! ---")

if __name__ == "__main__":
    main()