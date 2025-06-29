import requests
import logging
from bs4 import BeautifulSoup

class UnifiedApiClient:
    """
    一个统一的、可配置的API客户端，用于处理多个结构相似的网站。
    """
    def __init__(self, email, password, config):
        """
        初始化客户端。

        :param email: 登录邮箱
        :param password: 登录密码
        :param config: 一个包含网站特定配置的字典
        """
        self.email = email
        self.password = password
        self.config = config
        self.base_url = config['base_url']
        
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "en-US,en;q=0.9",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            "Referer": f"{self.base_url}{config.get('login_path', '/auth/login')}"
        })
        # 为需要AJAX的请求添加特定头
        if config.get('login_is_ajax'):
            self.session.headers['X-Requested-With'] = 'XMLHttpRequest'
            
        self.auth_token = None

    def login(self) -> bool:
        login_url = f"{self.base_url}{self.config['login_path']}"
        
        # 构造请求体
        payload = {"email": self.email, "password": self.password}
        # 合并额外的固定字段
        if 'extra_payload' in self.config:
            payload.update(self.config['extra_payload'])

        logging.info(f"正在尝试登录 {self.config.get('name', '')}，用户: {self.email}")
        
        try:
            # 根据配置决定使用 data 还是 json
            if self.config['login_method'] == 'json':
                response = self.session.post(login_url, json=payload)
            else: # 默认为 'data'
                response = self.session.post(login_url, data=payload)
                
            response.raise_for_status()
            response_data = response.json()
            logging.debug(f"登录响应: {response_data}")

            # 根据配置的成功条件进行判断
            success_check = self.config['success_check']
            if success_check(response_data):
                logging.info("登录成功！")
                # 如果需要，提取并设置Auth Token
                if self.config.get('auth_from_key'):
                    key_path = self.config['auth_from_key'] # e.g., ['data', 'auth_data']
                    token_value = response_data
                    for key in key_path:
                        token_value = token_value.get(key, {})
                    self.auth_token = token_value
                    self.session.headers['Authorization'] = self.auth_token
                return True
            else:
                logging.error(f"登录失败: {response_data.get('msg') or response_data.get('message', '未知错误')}")
                return False

        except Exception as e:
            logging.error(f"登录时发生错误: {e}")
            return False

    def get_subscription_link(self) -> str | None:
        method = self.config['sub_method']
        logging.info(f"正在使用 {method} 方式获取订阅链接...")

        try:
            if method == 'api':
                api_path = self.config['sub_api_path']
                response = self.session.get(f"{self.base_url}{api_path}")
                response.raise_for_status()
                sub_data = response.json()
                if sub_data.get('data') and sub_data['data'].get('subscribe_url'):
                    return sub_data['data']['subscribe_url']
                
            elif method == 'html':
                page_path = self.config['sub_page_path']
                # 访问页面时，通常不需要AJAX头
                page_headers = self.session.headers.copy()
                page_headers.pop('X-Requested-With', None)
                response = self.session.get(f"{self.base_url}{page_path}", headers=page_headers)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'lxml')
                
                selector_key = self.config['sub_html_selector_key']
                copy_button = soup.find(lambda tag: tag.has_attr(selector_key) and '/link/' in tag[selector_key])
                if copy_button:
                    return copy_button[selector_key]
            
            logging.error("未能找到订阅链接。")
            return None
            
        except Exception as e:
            logging.error(f"获取订阅链接时出错: {e}")
            return None