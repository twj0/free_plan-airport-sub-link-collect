import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def get_subscription(email, password):
    """
    Uses Selenium to log in, purchase the free plan, and get the subscription link for wwn.
    Includes advanced anti-detection measures.
    """
    logging.info("正在为 [华夏联盟] 初始化 Selenium WebDriver (高级反检测模式)...")
    
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("user-agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'")
    
    # Anti-detection measures
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = None # Initialize driver to None
    try:
        driver = webdriver.Chrome(options=options)
        
        # Execute script to hide navigator.webdriver property
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            '''
        })

        wait = WebDriverWait(driver, 30) # 30 second wait time

        # 1. Login
        login_url = "https://www.huaxia.cyou/#/login"
        logging.info(f"正在导航到登录页面: {login_url}")
        driver.get(login_url)

        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='email']"))).send_keys(email)
        driver.find_element(By.CSS_SELECTOR, "input[type='password']").send_keys(password)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        
        logging.info("登录表单已提交。等待跳转...")
        wait.until(EC.url_contains('/stage/dashboard'))
        logging.info("登录成功，已进入用户主页。")

        # 2. Purchase Plan
        purchase_url = "https://www.huaxia.cyou/#/stage/buysubs/order?id=12"
        logging.info(f"正在导航到购买页面: {purchase_url}")
        driver.get(purchase_url)

        # Click the "下单" (Place Order) button
        order_button_xpath = "//button[.//span[text()='下单']]"
        wait.until(EC.element_to_be_clickable((By.XPATH, order_button_xpath))).click()
        logging.info("已点击下单按钮。")

        # Click the "结账" (Checkout) button on the next page
        checkout_button_xpath = "//button[.//span[text()='结账']]"
        wait.until(EC.element_to_be_clickable((By.XPATH, checkout_button_xpath))).click()
        logging.info("已点击结账按钮。")
        
        # Wait for the "支付成功" (Payment Successful) confirmation
        wait.until(EC.visibility_of_element_located((By.XPATH, "//*[contains(text(), '支付成功')]")))
        logging.info("购买流程成功。")

        # 3. Get Subscription Link
        logging.info("正在获取订阅链接...")
        driver.get("https://www.huaxia.cyou/#/stage/dashboard") # Go back to dashboard
        
        # Click the button to show the subscription link
        copy_button_xpath = "//button[.//span[text()='复制订阅']]"
        wait.until(EC.element_to_be_clickable((By.XPATH, copy_button_xpath)))
        
        # Find the input field that contains the subscription link
        input_xpath = "//input[contains(@value, 'api/v1/client/subscribe')]"
        sub_link = wait.until(EC.visibility_of_element_located((By.XPATH, input_xpath))).get_attribute('value')

        if not sub_link:
            raise NoSuchElementException("无法找到包含订阅链接的输入框")

        logging.info("成功获取到订阅链接！")
        return sub_link

    except (TimeoutException, NoSuchElementException) as e:
        logging.error(f"[华夏联盟] 使用Selenium时发生错误: {e}")
        if driver:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            screenshot_path = f"huaxia_error_{timestamp}.png"
            html_path = f"huaxia_error_{timestamp}.html"
            try:
                driver.save_screenshot(screenshot_path)
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(driver.page_source)
                logging.info(f"已保存截图到: {screenshot_path}")
                logging.info(f"已保存页面源码到: {html_path}")
            except Exception as save_e:
                logging.error(f"保存调试文件时出错: {save_e}")
        return None
    finally:
        if driver:
            driver.quit()
            logging.info("Selenium WebDriver 已关闭。")
