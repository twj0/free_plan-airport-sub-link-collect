import os
import logging
from clients.unified_client import UnifiedApiClient
# 导入新的浏览器客户端
from clients.browser_client import BrowserAutomationClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 为每个网站定义配置
SITE_CONFIGS = {
    # ... (louwangzhiyu 和 wwn 的配置保持不变)
    "louwangzhiyu": {
        "client_type": "api", # 指定客户端类型
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
        "client_type": "browser", # 指定使用浏览器客户端
        "name": "大白",
        "base_url": "https://www.dabai.in",
        "login_path": "/auth/login",
        # 定义Playwright需要的CSS选择器
        "selectors": {
            "email": "#email",
            "password": "#passwd",
            "login_button": "#login",
            "post_login_success": "a[href='/user/logout']" # 等待“登出”按钮出现，证明登录成功
        },
        "sub_html_selector_key": "data-clipboard-text"
    },
    "ikuuu": {
        "client_type": "browser", # 指定使用浏览器客户端
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
        "client_type": "api", # 指定客户端类型
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

# 建立客户端类型与类的映射
CLIENT_MAP = {
    "api": UnifiedApiClient,
    "browser": BrowserAutomationClient
}

def main():
    all_subscriptions = []
    for site_key, config in SITE_CONFIGS.items():
        logging.info(f"--- 开始处理网站: {config['name']} ---")
        email = os.environ.get(f"{site_key.upper()}_EMAIL")
        password = os.environ.get(f"{site_key.upper()}_PASSWORD")
        if not email or not password:
            logging.warning(f"跳过 {config['name']}，因未设置Secrets。")
            continue
        try:
            # 根据配置动态选择客户端
            client_class = CLIENT_MAP[config['client_type']]
            api_client = client_class(email=email, password=password, config=config)
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
        logging.info(f"--- {len(unique_links)}条唯一的订阅链接已写入 subscriptions.txt！ ---")
    else:
        logging.warning("--- 未能获取到任何订阅链接，文件未更新。 ---")

if __name__ == "__main__":
    main()