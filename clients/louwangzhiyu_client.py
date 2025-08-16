import requests
import logging
from urllib.parse import quote

def get_subscription(email, password):
    """
    Logs in to louwangzhiyu and retrieves the subscription link using direct HTTP requests.
    """
    logging.info("正在为 [漏网之鱼] 使用HTTP请求进行登录...")
    session = requests.Session()

    # 1. Login request
    login_url = "https://hg.owokkvsxks.store/api/v1/passport/auth/login"
    
    encoded_email = quote(email)
    encoded_password = quote(password)
    
    login_headers = {
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://hg.owokkvsxks.store',
        'referer': 'https://hg.owokkvsxks.store/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
    }
    
    login_data = f'email={encoded_email}&password={encoded_password}'

    try:
        logging.info("发送登录请求...")
        response = session.post(login_url, headers=login_headers, data=login_data, timeout=30)
        response.raise_for_status()
        login_json = response.json()
        
        # CORRECTED LOGIC: Check for 'status' and 'auth_data'
        if login_json.get("status") != "success" or not login_json.get("data", {}).get("auth_data"):
            logging.error(f"[漏网之鱼] 登录失败: {login_json.get('message', '响应中没有找到auth_data')}")
            logging.error(f"服务器响应: {login_json}")
            return None
            
        auth_token = login_json["data"]["auth_data"]
        logging.info("登录成功，获取到authorization token。")

    except requests.exceptions.RequestException as e:
        logging.error(f"[漏网之鱼] 登录请求失败: {e}")
        return None
    except ValueError:
        logging.error(f"[漏网之鱼] 解析登录响应JSON失败。响应内容: {response.text[:200]}")
        return None

    # 2. Get subscription link
    sub_url = "https://hg.owokkvsxks.store/api/v1/user/getSubscribe"
    sub_headers = {
        'accept': 'application/json, text/plain, */*',
        'authorization': auth_token,
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
    }

    try:
        logging.info("发送获取订阅链接请求...")
        response = session.get(sub_url, headers=sub_headers, timeout=30)
        response.raise_for_status()
        sub_json = response.json()

        # CORRECTED LOGIC: Assume similar success structure
        if sub_json.get("status") != "success" or not sub_json.get("data", {}).get("subscribe_url"):
            logging.error(f"[漏网之鱼] 获取订阅链接失败: {sub_json.get('message', '响应中没有找到subscribe_url')}")
            logging.error(f"服务器响应: {sub_json}")
            return None
            
        subscription_link = sub_json["data"]["subscribe_url"]
        logging.info(f"成功获取到订阅链接!")
        return subscription_link

    except requests.exceptions.RequestException as e:
        logging.error(f"[漏网之鱼] 获取订阅链接请求失败: {e}")
        return None
    except ValueError:
        logging.error(f"[漏网之鱼] 解析订阅响应JSON失败。响应内容: {response.text[:200]}")
        return None
