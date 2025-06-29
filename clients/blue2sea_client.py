import requests
import logging
from bs4 import BeautifulSoup

def get_subscription():
    """
    访问 Blue2sea 网站并抓取公开的订阅链接。
    """
    url = "https://blue2sea.com/order/querySubscriptionLink/%20"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    logging.info(f"正在访问: {url}")

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'lxml')
        
        # 优先尝试 `<code>` 标签
        code_tag = soup.find('code')
        if code_tag:
            logging.info("通过 `<code>` 标签找到了订阅链接。")
            return code_tag.get_text(strip=True)

        # 如果找不到，尝试备用方案
        p_elements = soup.select('p.fs-5.col-md-8')
        for p_tag in p_elements:
            full_text = p_tag.get_text(strip=True)
            link_prefix = "公共订阅链接为："
            if full_text.startswith(link_prefix):
                 logging.info("通过 `<p>` 标签找到了订阅链接。")
                 return full_text.replace(link_prefix, "").strip()

        logging.error("未能找到订阅链接。")
        return None

    except Exception as e:
        logging.error(f"处理 blue2sea 时出错: {e}")
        return None