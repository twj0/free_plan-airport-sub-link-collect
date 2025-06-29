import logging
import asyncio
from playwright.async_api import async_playwright, TimeoutError

class BrowserAutomationClient:
    """
    一个使用Playwright的Async API驱动真实浏览器的客户端，
    专为在复杂的异步环境（如GitHub Actions）中稳定运行而设计。
    """
    def __init__(self, email, password, config):
        self.email = email
        self.password = password
        self.config = config
        self.base_url = config['base_url']
        # We will manage the page and browser within each async method

    async def _async_login(self):
        """The internal async implementation of the login process."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                logging.info("浏览器已启动，正在导航到登录页面...")
                await page.goto(f"{self.base_url}{self.config['login_path']}", timeout=60000)
                await page.wait_for_load_state('networkidle', timeout=20000)

                email_selector = self.config['selectors']['email']
                logging.info(f"等待元素 '{email_selector}' 出现...")
                await page.wait_for_selector(email_selector, state='visible', timeout=20000)

                logging.info("填写登录表单...")
                await page.fill(email_selector, self.email)
                await page.fill(self.config['selectors']['password'], self.password)
                await page.click(self.config['selectors']['login_button'])

                success_selector = self.config['selectors']['post_login_success']
                logging.info(f"等待登录成功标志 '{success_selector}' 出现...")
                await page.wait_for_selector(success_selector, timeout=20000)
                await page.screenshot(path=f"debug_{self.config['name']}_success.png")

                logging.info("Playwright登录成功！")
                
                # After login, get the subscription link
                logging.info("正在用户中心页面寻找订阅链接...")
                selector_key = self.config['sub_html_selector_key']
                link_element = page.locator(f"[{selector_key}*='/link/']").first
                sub_link = await link_element.get_attribute(selector_key)
                
                await browser.close()
                
                if sub_link:
                    logging.info("通过Playwright成功找到订阅链接！")
                    return sub_link
                else:
                    logging.error("在页面中未能定位到订阅链接元素。")
                    return None

            except Exception as e:
                logging.error(f"Playwright操作时发生错误: {e}")
                await page.screenshot(path=f"debug_{self.config['name']}_failure.png")
                await browser.close()
                return None
    
    # These public methods provide a synchronous interface to our async code
    def login(self) -> bool:
        # This is a placeholder since the real logic is combined now.
        # We run the combined async method and check if it returns a link.
        self.result = asyncio.run(self._async_login())
        return self.result is not None



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