import logging
import asyncio
from playwright.async_api import async_playwright, TimeoutError

class BrowserAutomationClient:
    """
    The definitive version of the browser client.
    It uses press_sequentially to simulate human typing and bypass anti-bot measures.
    """
    def __init__(self, email, password, config):
        self.email = email
        self.password = password
        self.config = config
        self.base_url = config['base_url']
        self.result = None

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
                password_selector = self.config['selectors']['password']
                login_button_selector = self.config['selectors']['login_button']

                logging.info(f"等待元素 '{email_selector}' 出现...")
                await page.wait_for_selector(email_selector, state='visible', timeout=20000)

                logging.info("正在以“人类模式”输入邮箱...")
                # CORRECTED: Use press_sequentially to simulate human typing
                await page.locator(email_selector).press_sequentially(self.email, delay=50) # Small delay between keys

                logging.info("正在以“人类模式”输入密码...")
                # CORRECTED: Use press_sequentially for the password field as well
                await page.locator(password_selector).press_sequentially(self.password, delay=50)
                
                logging.info("点击登录按钮...")
                await page.locator(login_button_selector).click()

                success_selector = self.config['selectors']['post_login_success']
                logging.info(f"等待登录成功标志 '{success_selector}' 出现...")
                await page.wait_for_selector(success_selector, timeout=20000)
                
                logging.info("Playwright登录成功！")
                
                logging.info("正在用户中心页面寻找订阅链接...")
                selector_key = self.config['sub_html_selector_key']
                link_element = page.locator(f"[{selector_key}*='/link/']").first
                sub_link = await link_element.get_attribute(selector_key)
                
                await browser.close()
                
                if sub_link:
                    logging.info(f"通过Playwright成功找到订阅链接！")
                    return sub_link
                else:
                    logging.error("在页面中未能定位到订阅链接元素。")
                    return None

            except Exception as e:
                logging.error(f"Playwright操作时发生错误: {e}")
                # Save a screenshot on any failure for diagnostics
                await page.screenshot(path=f"debug_{self.config['name']}_failure.png")
                await browser.close()
                return None
    
    def login(self) -> bool:
        self.result = asyncio.run(self._async_login())
        return self.result is not None

    def get_subscription_link(self) -> str | None:
        return self.result