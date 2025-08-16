import logging
import time
import base64
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def get_subscription(email, password):
    """
    使用 Selenium 驱动无头浏览器来登录 ikuuu.de 并获取订阅链接。
    这是为了绕过高级的 Cloudflare 保护。
    """
    logging.info("正在初始化 Selenium WebDriver...")
    
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36")

    driver = None
    try:
        service = Service()
        driver = webdriver.Chrome(service=service, options=options)
        # 增加总等待时间以应对慢速网络
        wait = WebDriverWait(driver, 60) 

        # 1. 访问登录页面
        login_url = "https://ikuuu.de/auth/login"
        logging.info(f"正在导航到登录页面: {login_url}")
        driver.get(login_url)

        logging.info("等待登录表单加载完成...")
        
        # 2. 填充登录表单
        email_input = wait.until(EC.presence_of_element_located((By.ID, "email")))
        logging.info("成功定位到邮箱输入框。")
        email_input.send_keys(email)

        passwd_input = driver.find_element(By.ID, "password")
        passwd_input.send_keys(password)
        
        # 3. 点击登录按钮
        login_button = driver.find_element(By.CLASS_NAME, "login")
        login_button.click()
        logging.info("已提交登录表单。")

        # 4. 等待登录成功并跳转到用户中心
        wait.until(EC.url_contains("/user"))
        logging.info("登录成功，已跳转到用户中心。")

        # 5. 优化弹窗处理逻辑
        logging.info("正在检查并关闭所有可能的弹窗...")
        try:
            # 使用一个较短的等待时间专门用于查找弹窗按钮
            popup_wait = WebDriverWait(driver, 10)
            
            # 构建一个强大的XPath来查找所有可能的确认/关闭按钮
            # 它会查找任何包含 "read", "知道了", "已读" (不区分大小写) 的 <button> 或 <a> 元素
            close_button_xpath = (
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'read') or "
                "contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '知道了') or "
                "contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '已读')] | "
                "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'read') or "
                "contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '知道了') or "
                "contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '已读')]"
            )
            
            # 查找所有匹配的按钮
            close_buttons = popup_wait.until(EC.presence_of_all_elements_located((By.XPATH, close_button_xpath)))
            
            for button in close_buttons:
                try:
                    if button.is_displayed() and button.is_enabled():
                        logging.info(f"找到并点击了一个弹窗关闭按钮，文本为: '{button.text}'")
                        driver.execute_script("arguments[0].click();", button)
                        time.sleep(1) # 点击后稍作等待
                except Exception as e:
                    logging.debug(f"点击按钮时出错 (可能是元素已消失): {e}")

            logging.info("弹窗处理完成。")
            
        except TimeoutException:
            logging.info("在10秒内未找到任何需要关闭的弹窗。")
        except Exception as e:
            logging.warning(f"处理弹窗时发生未知错误: {e}")

        # 6. 尝试每日签到
        logging.info("正在尝试执行每日签到...")
        try:
            # 使用更通用的定位器来找到签到按钮，因为ID可能会变化
            # 常见的签到按钮可能包含 "checkin", "docheckin" 等关键词
            checkin_button_locator = (By.CSS_SELECTOR, "a[onclick*='checkin'], button[onclick*='checkin'], #checkin, .checkin")
            
            checkin_button = wait.until(EC.element_to_be_clickable(checkin_button_locator))
            
            # 使用JS点击以确保执行
            driver.execute_script("arguments[0].click();", checkin_button)
            logging.info("成功点击签到按钮。")
            
            # 短暂等待，让签到结果的提示信息有机会加载
            time.sleep(3)
            
        except TimeoutException:
            logging.info("未找到可点击的签到按钮，可能已经签到过了。")
        except Exception as e:
            logging.warning(f"执行签到时发生意外错误: {e}")

        # 7. 点击Clash订阅下拉菜单
        logging.info("正在点击Clash订阅下拉菜单...")
        dropdown_toggle_locator = (By.ID, "dropdownMenuButton")
        dropdown_toggle = wait.until(EC.element_to_be_clickable(dropdown_toggle_locator))
        dropdown_toggle.click()
        logging.info("Clash订阅下拉菜单已点击。")

        # 8. 获取并解码订阅链接
        logging.info("正在获取并解码Clash订阅链接...")
        copy_link_locator = (By.CSS_SELECTOR, "a.copy-text[data-clipboard-text-encoded]")
        copy_link_element = wait.until(EC.presence_of_element_located(copy_link_locator))
        
        encoded_link = copy_link_element.get_attribute('data-clipboard-text-encoded')
        
        if encoded_link:
            try:
                # 使用-和_安全的解码方式
                decoded_link = base64.urlsafe_b64decode(encoded_link + '===').decode('utf-8')
                logging.info(f"成功获取并解码订阅链接！")
                return decoded_link
            except (base64.binascii.Error, UnicodeDecodeError) as e:
                logging.error(f"Base64解码失败: {e}")
                return None
        else:
            logging.error("未能找到编码后的订阅链接属性。")
            return None

    except (TimeoutException, NoSuchElementException) as e:
        logging.error(f"操作超时或未能找到页面元素: {e.msg}")
        logging.error(f"页面标题是: {driver.title if driver else 'N/A'}")
        if driver:
            # 保存截图和页面源码以供调试
            screenshot_path = "ikuuu_final_error.png"
            pagesource_path = "ikuuu_final_error.html"
            driver.save_screenshot(screenshot_path)
            with open(pagesource_path, "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            logging.info(f"已保存截图到: {screenshot_path}")
            logging.info(f"已保存页面源码到: {pagesource_path}")
        return None
    except Exception as e:
        logging.error(f"处理 ikuuu.one 时发生未知错误: {e}", exc_info=True)
        return None
    finally:
        if driver:
            driver.quit()
            logging.info("Selenium WebDriver 已关闭。")
