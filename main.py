import os
import logging
from clients.unified_client import UnifiedApiClient

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# --- 为每个网站定义配置 ---
SITE_CONFIGS = {
    "louwangzhiyu": {
        "name": "漏网之鱼",
        "base_url": "https://ch.louwangzhiyu.xyz",
        "login_path": "/api/v1/passport/auth/login",
        "login_method": "data",
        "success_check": lambda r: 'data' in r and r['data'].get('token'),
        # CORRECTED: Use the correct 'auth_data' for API calls, not the short 'token'
        "auth_from_key": ['data', 'auth_data'],
        "sub_method": "api",
        "sub_api_path": "/api/v1/user/getSubscribe"
    },
    "dabai": {
        "name": "大白",
        "base_url": "https://www.dabai.in",
        "login_path": "/auth/login",
        "login_method": "data",
        "login_is_ajax": True,
        "extra_payload": {"remember_me": "on", "code": ""},
        "success_check": lambda r: r.get('ret') == 1,
        "sub_method": "html",
        "sub_page_path": "/user",
        "sub_html_selector_key": "data-clipboard-text"
    },
    "ikuuu": {
        "name": "ikuuu",
        "base_url": "https://ikuuu.one",
        "login_path": "/auth/login",
        "login_method": "data",
        "login_is_ajax": True,
        "extra_payload": {"host": "ikuuu.one", "code": ""},
        "success_check": lambda r: r.get('ret') == 1,
        "sub_method": "html",
        "sub_page_path": "/user",
        "sub_html_selector_key": "data-clipboard-text"
    },
    "wwn": {
        "name": "华夏联盟",
        "base_url": "https://wwn.trx1.cyou",
        "login_path": "/api/v1/passport/auth/login",
        "login_method": "json",
        "extra_payload": {"captchaData": ""},
        "success_check": lambda r: 'data' in r and r['data'].get('auth_data'),
        "auth_from_key": ['data', 'auth_data'],
        "sub_method": "api",
        "sub_api_path": "/api/v1/user/getSubscribe"
    }
}

# ... (main function remains unchanged) ...
def main():
    all_subscriptions = []
    for site_key, config in SITE_CONFIGS.items():
        logging.info(f"--- 开始处理网站: {config['name']} ---")
        email = os.environ.get(f"{site_key.upper()}_EMAIL")
        password = os.environ.get(f"{site_key.upper()}_PASSWORD")
        if not email or not password:
            logging.warning(f"跳过 {config['name']}，因为未在Secrets中设置 {site_key.upper()}_EMAIL 或 _PASSWORD。")
            continue
        try:
            api_client = UnifiedApiClient(email=email, password=password, config=config)
            if api_client.login():
                sub_link = api_client.get_subscription_link()
                if sub_link:
                    logging.info(f"成功获取 {config['name']} 的订阅链接。")
                    all_subscriptions.append(sub_link)
        except Exception as e:
            logging.error(f"处理 {config['name']} 时发生严重错误: {e}")
    if all_subscriptions:
        unique_links = sorted(list(set(all_subscriptions)))
        with open("subscriptions.txt", "w", encoding="utf-8") as f:
            for link in unique_links:
                f.write(link + "\n")
        logging.info(f"--- {len(unique_links)}条唯一的订阅链接已成功写入 subscriptions.txt！ ---")
    else:
        logging.warning("--- 未能获取到任何订阅链接，文件未更新。 ---")
if __name__ == "__main__":
    main()