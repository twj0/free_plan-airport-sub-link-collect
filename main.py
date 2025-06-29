import os
import logging
import sys  # <--- IMPORT SYS MODULE
from clients.unified_client import UnifiedApiClient
from clients.browser_client import BrowserAutomationClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- SITE_CONFIGS remains the same ---
SITE_CONFIGS = {
    "louwangzhiyu": {
        "client_type": "api",
        "name": "漏网之鱼",
        "base_url": "https://ch.louwangzhiyu.xyz",
        "login_path": "/api/v1/passport/auth/login",
        "login_method": "data",
        "success_check": lambda r: 'data' in r and r['data'].get('auth_data'),
        "auth_from_key": ['data', 'auth_data'],
        "sub_method": "api",
        "sub_api_path": "/api/v1/user/getSubscribe"
    },
    "dabai": {
        "client_type": "browser",
        "name": "大白",
        "base_url": "https://www.dabai.in",
        "login_path": "/auth/login",
        "selectors": {
            "email": "#email",
            "password": "#passwd",
            "login_button": "#login",
            "post_login_success": "a[href='/user/logout']"
        },
        "sub_html_selector_key": "data-clipboard-text"
    },
    "ikuuu": {
        "client_type": "browser",
        "name": "ikuuu",
        "base_url": "https://ikuuu.one",
        "login_path": "/auth/login",
        "selectors": {
            "email": "#email",
            "password": "#passwd",
            "login_button": "#login",
            "post_login_success": "a[href='/user/logout']"
        },
        "sub_html_selector_key": "data-clipboard-text"
    },
    "wwn": {
        "client_type": "api",
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

CLIENT_MAP = {
    "api": UnifiedApiClient,
    "browser": BrowserAutomationClient
}

def main():
    all_subscriptions = []
    any_browser_failed = False  # <--- ADD A FLAG TO TRACK BROWSER FAILURES

    for site_key, config in SITE_CONFIGS.items():
        logging.info(f"--- 开始处理网站: {config['name']} ---")
        email = os.environ.get(f"{site_key.upper()}_EMAIL")
        password = os.environ.get(f"{site_key.upper()}_PASSWORD")
        if not email or not password:
            logging.warning(f"跳过 {config['name']}，因未设置Secrets。")
            continue
        try:
            client_class = CLIENT_MAP[config['client_type']]
            api_client = client_class(email=email, password=password, config=config)
            
            if api_client.login():
                sub_link = api_client.get_subscription_link()
                if sub_link:
                    logging.info(f"成功获取 {config['name']} 的订阅链接。")
                    all_subscriptions.append(sub_link)
            elif config['client_type'] == 'browser':
                # If login fails AND it was a browser client, set the flag
                any_browser_failed = True

        except Exception as e:
            logging.error(f"处理 {config['name']} 时发生严重错误: {e}")
            if config['client_type'] == 'browser':
                any_browser_failed = True

    if all_subscriptions:
        unique_links = sorted(list(set(all_subscriptions)))
        with open("subscriptions.txt", "w", encoding="utf-8") as f:
            for link in unique_links:
                f.write(link + "\n")
        logging.info(f"--- {len(unique_links)}条唯一的订阅链接已成功写入 subscriptions.txt！ ---")
    else:
        logging.warning("--- 未能获取到任何订阅链接，文件未更新。 ---")

    # <--- ADD FINAL CHECK ---
    # If any browser client failed, exit with an error code to make the Action fail
    if any_browser_failed:
        logging.error("一个或多个浏览器客户端操作失败。正在以错误状态退出以触发工件上传。")
        sys.exit(1)

if __name__ == "__main__":
    main()