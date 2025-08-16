import requests
import logging
from bs4 import BeautifulSoup

class DabaiApiClient:
    """
    一个用于与 dabai.in 网站API交互的客户端类。
    """
    def __init__(self, email, password):
        self.base_url = "https://ab.dabai.in"
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
        self.session.get(login_url) # 获取初始cookie
        payload = {'email': self.email, 'passwd': self.password, 'remember_me': 'on', 'code': ''}
        response = self.session.post(login_url, data=payload)
        response.raise_for_status()
        if response.json().get('ret') == 1:
            logging.info("登录 dabai.in 成功！")
            return True
        logging.error(f"登录 dabai.in 失败: {response.json().get('msg')}")
        return False

    def purchase_free_plan(self, shop_id=31) -> bool:
        """ 购买免费套餐以续期账户 """
        logging.info(f"正在为商品ID {shop_id} 执行免费购买操作...")
        buy_url = f"{self.base_url}/user/buy"
        payload = {
            'coupon': '',
            'shop': shop_id,
            'autorenew': 0,
            'disableothers': 1
        }
        # 需要更新Referer头
        headers = self.session.headers.copy()
        headers['Referer'] = f"{self.base_url}/user/shop"
        response = self.session.post(buy_url, data=payload, headers=headers)
        response.raise_for_status()
        response_data = response.json()
        if response_data.get('ret') == 1:
            logging.info(f"免费购买成功: {response_data.get('msg')}")
            return True
        # 已经购买过的情况
        elif '你已购买过此商品' in response_data.get('msg', ''):
            logging.info("本月已购买过此商品，无需重复操作。")
            return True
        else:
            logging.error(f"免费购买失败: {response_data.get('msg')}")
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
        client = DabaiApiClient(email, password)
        if client.login():
            # 登录后执行购买操作
            if client.purchase_free_plan():
                # 购买成功或已购买，则获取订阅链接
                return client.get_subscription_link()
            else:
                logging.error("因免费购买失败，无法获取订阅链接。")
                return None
        return None
    except Exception as e:
        logging.error(f"处理 dabai.in 时出错: {e}")
        return None