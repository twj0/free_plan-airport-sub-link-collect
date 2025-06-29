import logging
from playwright.sync_api import sync_playwright, TimeoutError

class BrowserAutomationClient:
    """
    一个使用Playwright驱动真实浏览器进行操作的客户端，
    增加了更稳健的等待和失败时自动截图的调试功能。
    """
    def __init__(self, email, password, config):
        self.email = email
        self.password = password
        self.config = config
        self.base_url = config['base_url']
        self.page = None
        self.browser = None
        self.playwright = None

    def login(self) -> bool:
        logging.info(f"正在使用Playwright(浏览器模式)尝试登录 {self.config['name']}...")
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=True)
            self.page = self.browser.new_page()
            
            logging.info("浏览器已启动，正在导航到登录页面...")
            self.page.goto(f"{self.base_url}{self.config['login_path']}", timeout=60000)

            # ADDED: 在操作前等待页面稳定，并截取一张初始图用于调试
            self.page.wait_for_load_state('networkidle', timeout=15000)
            self.page.screenshot(path=f"debug_{self.config['name']}_1_initial_page.png")

            # 等待登录表单的关键元素变得可见
            email_selector = self.config['selectors']['email']
            password_selector = self.config['selectors']['password']
            
            logging.info(f"等待元素 '{email_selector}' 出现...")
            self.page.wait_for_selector(email_selector, state='visible', timeout=20000)
            
            logging.info("填写登录表单...")
            self.page.fill(email_selector, self.email)
            self.page.fill(password_selector, self.password)
            
            # 点击前截图
            self.page.screenshot(path=f"debug_{self.config['name']}_2_before_click.png")
            self.page.click(self.config['selectors']['login_button'])

            # 等待登录成功的标志出现
            success_selector = self.config['selectors']['post_login_success']
            logging.info(f"等待登录成功标志 '{success_selector}' 出现...")
            self.page.wait_for_selector(success_selector, timeout=15000)
            
            self.page.screenshot(path=f"debug_{self.config['name']}_3_login_success.png")
            logging.info("Playwright登录成功！")
            return True

        except TimeoutError as e:
            logging.error(f"Playwright操作超时: {e}")
            self.page.screenshot(path=f"debug_{self.config['name']}_4_timeout_failure.png")
            return False
        except Exception as e:
            logging.error(f"Playwright登录时发生未知错误: {e}")
            if self.page:
                self.page.screenshot(path=f"debug_{self.config['name']}_5_unknown_failure.png")
            return False

    def get_subscription_link(self) -> str | None:
        if not self.page:
            logging.error("Playwright页面未初始化，无法获取订阅链接。")
            return None
        
        logging.info("正在用户中心页面寻找订阅链接...")
        try:
            selector_key = self.config['sub_html_selector_key']
            link_element = self.page.locator(f"[{selector_key}*='/link/']").first
            sub_link = link_element.get_attribute(selector_key)
            
            if sub_link:
                logging.info("通过Playwright成功找到订阅链接！")
                return sub_link
            else:
                logging.error("在页面中未能定位到订阅链接元素。")
                return None
        except Exception as e:
            logging.error(f"Playwright寻找订阅链接时出错: {e}")
            return None
        finally:
            # 确保浏览器在所有操作后关闭
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()