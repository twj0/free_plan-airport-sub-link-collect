import requests
import logging

import urllib.parse
class WwnApiClient:
    """
    一个用于与 wwn.trx1.cyou 网站API交互的客户端类。
    """
    def __init__(self, email, password):
        self.base_url = "https://wwn.trx1.cyou/api/v1"
        self.email = email
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://wwn.trx1.cyou/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
        })
        self.auth_token = None

    def login(self) -> bool:
        login_url = f"{self.base_url}/passport/auth/login"
        payload = {"email": self.email, "password": self.password, "captchaData": ""}
        try:
            response = self.session.post(login_url, json=payload)
            response.raise_for_status() 
            response_data = response.json()
            if 'data' in response_data and response_data['data'].get('auth_data'):
                self.auth_token = response_data['data']['auth_data']
                self.session.headers['Authorization'] = self.auth_token
                logging.info("登录 wwn.trx1.cyou 成功！")
                return True
            logging.error(f"登录 wwn.trx1.cyou 失败: {response_data.get('message', '未知错误')}")
            return False
        except Exception as e:
            logging.error(f"登录 wwn.trx1.cyou 时出错: {e}")
            return False
            
    def get_subscription_info(self):
        if not self.auth_token: return None
        subscribe_url_api = f"{self.base_url}/user/getSubscribe"
        try:
            response = self.session.get(subscribe_url_api)
            response.raise_for_status()
            subscribe_data = response.json()
            if 'data' in subscribe_data:
                return subscribe_data.get('data')
            return None
        except Exception as e:
            logging.error(f"获取 wwn.trx1.cyou 订阅信息时出错: {e}")
            return None

def get_subscription(email, password):
    """主调用函数，封装客户端操作并净化URL。"""
    try:
        client = WwnApiClient(email, password)
        if client.login():
            sub_data = client.get_subscription_info()
            if sub_data and sub_data.get('subscribe_url'):
                dirty_url = sub_data['subscribe_url']
                
                clean_url = dirty_url.strip().rstrip(',')
                
                converter_backend = "suburl.v1.mk"
                # 构建最终的、稳定的转换器URL
                encoded_url = urllib.parse.quote(clean_url.strip().rstrip(','))
                
                # target=clash&list=true可以返回一个更干净的节点列表YAML
                final_url = f"https://{converter_backend}/sub?target=clash&list=true&url={encoded_url}"
                
                logging.info(f"为 [华夏联盟] 构建了转换器链接: {final_url}")
                
                return final_url
        return None
    except Exception as e:
        logging.error(f"处理 wwn.trx1.cyou 客户端时出错: {e}")
        return None