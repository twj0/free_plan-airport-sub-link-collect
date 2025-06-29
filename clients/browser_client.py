import logging
from playwright.sync_api import sync_playwright

class BrowserAutomationClient:
    """
    一个使用Playwright驱动真实浏览器进行操作的客户端，
    用于处理需要复杂JavaScript环境的网站。
    """
    def __init__(self, email, password, config):
        self.email = email
        self.password = password
        self.config = config
        self.base_url = config['base_url']
        self.page = None # Playwright的页面对象

    def login(self) -> bool:
        logging.info(f"正在使用Playwright(浏览器模式)尝试登录 {self.config['name']}...")
        try:
            # Playwright的上下文管理器，会自动处理浏览器启动和关闭
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                self.page = browser.new_page()
                self.page.goto(f"{self.base_url}{self.config['login_path']}")

                # 等待页面加载完成，并填写表单
                self.page.fill(self.config['selectors']['email'], self.email)
                self.page.fill(self.config['selectors']['password'], self.password)
                self.page.click(self.config['selectors']['login_button'])

                # 等待登录成功的关键标志出现
                # 这里我们等待用户中心页面的某个特定元素，这是最可靠的方式
                success_selector = self.config['selectors']['post_login_success']
                self.page.wait_for_selector(success_selector, timeout=15000)
                
                logging.info("Playwright登录成功！已跳转到用户中心。")
                return True

        except Exception as e:
            logging.error(f"Playwright登录时发生错误: {e}")
            return False

    def get_subscription_link(self) -> str | None:
        if not self.page:
            logging.error("Playwright页面未初始化，无法获取订阅链接。")
            return None
        
        logging.info("正在用户中心页面寻找订阅链接...")
        try:
            # 链接通常在“复制”按钮的属性里
            selector_key = self.config['sub_html_selector_key']
            # 使用 locator API，更稳定
            link_element = self.page.locator(f"[{selector_key}*='/link/']").first
            sub_link = link_element.get_attribute(selector_key)
            
            if sub_link:
                logging.info("通过Playwright成功找到订阅链接！")
                # Playwright操作完成后，页面和浏览器会被with语句自动关闭
                return sub_link
            else:
                logging.error("在页面中未能定位到订阅链接元素。")
                return None
        except Exception as e:
            logging.error(f"Playwright寻找订阅链接时出错: {e}")
            return None