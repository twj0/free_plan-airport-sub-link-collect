import requests
import logging
from bs4 import BeautifulSoup

class IkuuuApiClient:
    """
    一个用于与 ikuuu.one 网站API交互的客户端类。
    """
    def __init__(self, email, password):
        self.base_url = "https://ikuuu.one"
        self.email = email
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{self.base_url}/auth/login",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
        })

    def login(self) -> bool:
        login_url = f"{self.base_url}/auth/login"
        payload = {'host': 'ikuuu.one', 'email': self.email, 'passwd': self.password, 'code': ''}
        response = self.session.post(login_url, data=payload)
        response.raise_for_status()
        if response.json().get('ret') == 1:
            logging.info("登录 ikuuu.one 成功！")
            return True
        logging.error(f"登录 ikuuu.one 失败: {response.json().get('msg')}")
        return False

    def get_subscription_link(self) -> str | None:
        user_dashboard_url = f"{self.base_url}/user"
        page_headers = self.session.headers.copy()
        page_headers.pop('X-Requested-With', None)
        response = self.session.get(user_dashboard_url, headers=page_headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')
        copy_button = soup.find(lambda tag: tag.has_attr('data-clipboard-text') and '/link/' in tag['data-clipboard-text'])
        if copy_button:
            return copy_button['data-clipboard-text']
        return None

def get_subscription(email, password):
    """主调用函数，封装客户端操作。"""
    try:
        client = IkuuuApiClient(email, password)
        if client.login():
            return client.get_subscription_link()
        return None
    except Exception as e:
        logging.error(f"处理 ikuuu.one 时出错: {e}")
        return None