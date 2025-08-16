import os
import sys
import logging
import requests
import yaml
import base64
import json
from urllib.parse import unquote, urlparse
from typing import Optional, List, Dict, Any

# --- 配置区域 ---
from clients import dabai_client, huaxia_client, ikuuu_client, louwangzhiyu_client

# 配置日志
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('proxy_merger.log', encoding='utf-8')
    ]
)

# 常量定义
OUTPUT_FILE = "merged_subscription.yaml"
BASE_CONFIG_FILE = "base.yaml"
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3

TASKS = {
    "dabai":        {"tag": "[大白]",       "func": dabai_client.get_subscription,       "needs_creds": True},
    "ikuuu":        {"tag": "[ikuuu]",      "func": ikuuu_client.get_subscription,      "needs_creds": True},
    "wwn":          {"tag": "[华夏联盟]",     "func": huaxia_client.get_subscription,     "needs_creds": True},
    "louwangzhiyu": {"tag": "[漏网之鱼]", "func": louwangzhiyu_client.get_subscription, "needs_creds": True},
    




}

def validate_uri_format(uri: str) -> bool:
    """验证URI格式是否有效"""
    if not uri or not isinstance(uri, str):
        return False
    
    supported_protocols = ['ss://', 'vmess://', 'trojan://']
    return any(uri.startswith(protocol) for protocol in supported_protocols)

def safe_base64_decode(encoded_str: str) -> Optional[str]:
    """安全的Base64解码，处理填充问题"""
    try:
        # 添加必要的填充
        missing_padding = len(encoded_str) % 4
        if missing_padding:
            encoded_str += '=' * (4 - missing_padding)
        
        decoded = base64.b64decode(encoded_str).decode('utf-8')
        return decoded
    except Exception as e:
        logging.debug(f"Base64解码失败: {e}")
        return None

def parse_uri(uri: str) -> Optional[Dict[str, Any]]:
    """解析单个节点链接 (ss, vmess, trojan) 并返回Clash格式的字典。"""
    if not validate_uri_format(uri):
        logging.debug(f"无效的URI格式: {uri[:50]}...")
        return None
    
    try:
        if uri.startswith('ss://'):
            return parse_shadowsocks_uri(uri)
        elif uri.startswith('vmess://'):
            return parse_vmess_uri(uri)
        elif uri.startswith('trojan://'):
            return parse_trojan_uri(uri)
    except Exception as e:
        logging.error(f"解析URI失败: '{uri[:40]}...', 错误: {e}")
        return None
    
    return None

def parse_shadowsocks_uri(uri: str) -> Optional[Dict[str, Any]]:
    """解析Shadowsocks URI"""
    try:
        if '#' not in uri:
            logging.warning(f"SS URI缺少节点名称: {uri[:50]}...")
            return None
            
        main_part, name = uri.split('#', 1)
        name = unquote(name).strip()
        
        if not name:
            name = "Unnamed SS Node"
        
        # 解析服务器和端口
        if '@' not in main_part:
            logging.warning(f"SS URI格式错误，缺少@符号: {uri[:50]}...")
            return None
            
        encoded_part, server_part = main_part[5:].rsplit('@', 1)
        
        if ':' not in server_part:
            logging.warning(f"SS URI格式错误，服务器部分缺少端口: {uri[:50]}...")
            return None
            
        server, port_str = server_part.rsplit(':', 1)
        
        # 验证端口
        try:
            port = int(port_str)
            if not (1 <= port <= 65535):
                raise ValueError("端口超出有效范围")
        except ValueError as e:
            logging.warning(f"SS URI端口无效: {port_str}, {e}")
            return None
        
        # 解码认证信息
        decoded_auth = safe_base64_decode(encoded_part)
        if not decoded_auth or ':' not in decoded_auth:
            logging.warning(f"SS URI认证信息解码失败或格式错误: {uri[:50]}...")
            return None
            
        cipher, password = decoded_auth.split(':', 1)
        
        # 验证必要字段
        if not all([cipher, password, server]):
            logging.warning(f"SS URI缺少必要字段: {uri[:50]}...")
            return None
        
        return {
            'name': name,
            'type': 'ss',
            'server': server,
            'port': port,
            'cipher': cipher,
            'password': password
        }
        
    except Exception as e:
        logging.error(f"解析SS URI时发生错误: {e}")
        return None

def parse_vmess_uri(uri: str) -> Optional[Dict[str, Any]]:
    """解析VMess URI"""
    try:
        encoded_part = uri[8:]
        if not encoded_part:
            logging.warning("VMess URI缺少编码部分")
            return None
            
        decoded_json = safe_base64_decode(encoded_part)
        if not decoded_json:
            logging.warning(f"VMess URI Base64解码失败: {uri[:50]}...")
            return None
            
        vmess_data = json.loads(decoded_json)
        
        # 验证必要字段
        required_fields = ['ps', 'add', 'port', 'id']
        for field in required_fields:
            if field not in vmess_data:
                logging.warning(f"VMess配置缺少必要字段: {field}")
                return None
        
        # 验证端口
        try:
            port = int(vmess_data.get('port'))
            if not (1 <= port <= 65535):
                raise ValueError("端口超出有效范围")
        except (ValueError, TypeError):
            logging.warning(f"VMess端口无效: {vmess_data.get('port')}")
            return None
        
        node = {
            'name': vmess_data.get('ps') or 'Unnamed VMess Node',
            'type': 'vmess',
            'server': vmess_data.get('add'),
            'port': port,
            'uuid': vmess_data.get('id'),
            'alterId': int(vmess_data.get('aid', 0)),
            'cipher': vmess_data.get('scy', 'auto'),
            'network': vmess_data.get('net', 'tcp'),
            'tls': vmess_data.get('tls') == 'tls',
        }
        
        # 处理WebSocket配置
        if node['network'] == 'ws':
            node['ws-opts'] = {
                'path': vmess_data.get('path', '/'),
                'headers': {'Host': vmess_data.get('host', node['server'])}
            }
        
        # 处理TLS配置
        if node['tls']:
            node['servername'] = vmess_data.get('host', node['server'])
        
        return node
        
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logging.error(f"解析VMess URI时发生错误: {e}")
        return None

def parse_trojan_uri(uri: str) -> Optional[Dict[str, Any]]:
    """解析Trojan URI"""
    try:
        if '#' not in uri:
            logging.warning(f"Trojan URI缺少节点名称: {uri[:50]}...")
            return None
            
        main_part, name = uri.split('#', 1)
        name = unquote(name).strip()
        
        if not name:
            name = "Unnamed Trojan Node"
        
        # 解析查询参数
        query_params = {}
        if '?' in main_part:
            main_part, query_string = main_part.split('?', 1)
            for param in query_string.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    query_params[key] = unquote(value)
        
        # 解析密码和服务器
        if '@' not in main_part:
            logging.warning(f"Trojan URI格式错误，缺少@符号: {uri[:50]}...")
            return None
            
        password, server_part = main_part[9:].rsplit('@', 1)
        
        if ':' not in server_part:
            logging.warning(f"Trojan URI格式错误，服务器部分缺少端口: {uri[:50]}...")
            return None
            
        server, port_str = server_part.rsplit(':', 1)
        
        # 验证端口
        try:
            port = int(port_str)
            if not (1 <= port <= 65535):
                raise ValueError("端口超出有效范围")
        except ValueError as e:
            logging.warning(f"Trojan URI端口无效: {port_str}, {e}")
            return None
        
        # 验证必要字段
        if not all([password, server]):
            logging.warning(f"Trojan URI缺少必要字段: {uri[:50]}...")
            return None
        
        node = {
            'name': name,
            'type': 'trojan',
            'server': server,
            'port': port,
            'password': password,
            'udp': True
        }
        
        # 处理SNI
        if 'sni' in query_params:
            node['sni'] = query_params['sni']
        elif 'peer' in query_params:
            node['sni'] = query_params['peer']
        
        return node
        
    except Exception as e:
        logging.error(f"解析Trojan URI时发生错误: {e}")
        return None

def get_content_from_url(url: str) -> Optional[str]:
    """从URL获取内容，支持重试机制"""
    if not url or not isinstance(url, str):
        return None
    
    # 清理URL
    cleaned_url = url.strip().rstrip(',')
    
    # 验证URL格式
    try:
        parsed_url = urlparse(cleaned_url)
        if not parsed_url.scheme or not parsed_url.netloc:
            logging.error(f"无效的URL格式: {cleaned_url}")
            return None
    except Exception as e:
        logging.error(f"URL解析失败: {cleaned_url}, 错误: {e}")
        return None
    
    # 重试机制
    for attempt in range(MAX_RETRIES):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(
                cleaned_url, 
                timeout=REQUEST_TIMEOUT,
                headers=headers,
                allow_redirects=True
            )
            response.raise_for_status()
            
            # 检查响应内容
            if not response.text:
                logging.warning(f"从URL获取到空内容: {cleaned_url}")
                return None
                
            logging.info(f"成功从URL获取内容: {cleaned_url} (大小: {len(response.text)} 字符)")
            return response.text
            
        except requests.exceptions.Timeout:
            logging.warning(f"请求超时 (尝试 {attempt + 1}/{MAX_RETRIES}): {cleaned_url}")
        except requests.exceptions.ConnectionError:
            logging.warning(f"连接错误 (尝试 {attempt + 1}/{MAX_RETRIES}): {cleaned_url}")
        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTP错误 {e.response.status_code} (尝试 {attempt + 1}/{MAX_RETRIES}): {cleaned_url}")
        except requests.exceptions.RequestException as e:
            logging.error(f"请求异常 (尝试 {attempt + 1}/{MAX_RETRIES}): {cleaned_url}, 错误: {e}")
        
        if attempt < MAX_RETRIES - 1:
            import time
            time.sleep(2 ** attempt)  # 指数退避
    
    logging.error(f"所有重试都失败了: {cleaned_url}")
    return None

def parse_subscription_content(content: str) -> List[Dict[str, Any]]:
    """解析订阅内容。支持Clash (YAML) 格式和Base64编码的节点列表。"""
    if not content or not isinstance(content, str):
        return []
    
    content = content.strip()
    if not content:
        return []
    
    # 尝试解析为YAML
    try:
        # 净化内容，修复常见的格式问题
        sanitized_content = content.replace('\t', '  ')
        data = yaml.safe_load(sanitized_content)
        
        if isinstance(data, dict) and 'proxies' in data:
            proxies = data.get('proxies')
            if isinstance(proxies, list):
                logging.info(f"成功解析YAML格式，找到 {len(proxies)} 个代理节点")
                return [proxy for proxy in proxies if isinstance(proxy, dict)]
            else:
                logging.warning("YAML中的proxies字段不是列表格式")
                return []
    except yaml.YAMLError as e:
        logging.debug(f"YAML解析失败，尝试Base64解码: {e}")
    except Exception as e:
        logging.debug(f"YAML处理时发生意外错误: {e}")
    
    # 尝试Base64解码
    try:
        # 清理Base64字符串
        clean_content = ''.join(content.split())
        decoded_content = safe_base64_decode(clean_content)
        
        if not decoded_content:
            logging.error("Base64解码失败")
            return []
        
        logging.info(f"成功解码Base64内容 (长度: {len(decoded_content)})")
        
        # 尝试将解码后的内容作为YAML解析
        try:
            nested_data = yaml.safe_load(decoded_content)
            if isinstance(nested_data, dict) and 'proxies' in nested_data:
                proxies = nested_data.get('proxies')
                if isinstance(proxies, list):
                    logging.info(f"Base64内容解析为Clash配置，找到 {len(proxies)} 个代理节点")
                    return [proxy for proxy in proxies if isinstance(proxy, dict)]
        except yaml.YAMLError:
            logging.debug("解码后的内容不是YAML格式，尝试作为URI列表处理")
        
        # 作为URI列表处理
        uris = [line.strip() for line in decoded_content.splitlines() if line.strip()]
        if not uris:
            logging.warning("解码后未找到任何URI")
            return []
        
        nodes = []
        for uri in uris:
            if validate_uri_format(uri):
                node = parse_uri(uri)
                if node:
                    nodes.append(node)
            else:
                logging.debug(f"跳过无效URI: {uri[:50]}...")
        
        logging.info(f"从URI列表解析出 {len(nodes)} 个有效节点")
        return nodes
        
    except Exception as e:
        logging.error(f"Base64内容处理失败: {e}")
        return []

def load_creds_from_json(file_path="user_credentials.json") -> Dict[str, Dict[str, str]]:
    """从JSON文件中加载凭据"""
    if not os.path.exists(file_path):
        return {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 映射JSON中的中文键到TASKS中的任务名
        key_mapping = {
            "大白": "dabai",
            "ikuuu": "ikuuu",
            "华夏联盟": "wwn",
            "漏网之鱼": "louwangzhiyu"
        }

        creds = {}
        for json_key, task_name in key_mapping.items():
            if json_key in data:
                creds[task_name] = {
                    "email": data[json_key].get("username1"),
                    "password": data[json_key].get("password")
                }
        logging.info(f"成功从 {file_path} 加载了 {len(creds)} 个凭据。")
        return creds
    except Exception as e:
        logging.error(f"从JSON文件加载凭据失败: {e}")
        return {}

def run_tasks_and_get_nodes(task_names: List[str]) -> List[Dict[str, Any]]:
    """运行指定的任务，获取、解析并标记所有节点。"""
    if not task_names:
        logging.warning("未指定要运行的任务")
        return []

    all_tagged_nodes = []
    json_creds = load_creds_from_json()

    for name in task_names:
        if name not in TASKS:
            logging.warning(f"未知的任务名称: {name}")
            continue

        task = TASKS[name]
        logging.info(f"--- 正在运行任务: {task['tag']} ---")

        subscription_urls = []
        try:
            if task['needs_creds']:
                # 检查多账户凭据环境变量 (例如 IKUUU_CREDENTIALS)
                multi_creds_env = os.environ.get(f"{name.upper()}_CREDENTIALS")
                
                if multi_creds_env:
                    logging.info(f"找到 {name} 的多账户凭据，将进行遍历...")
                    credentials = [cred.strip().split(',') for cred in multi_creds_env.split(';') if ',' in cred]
                    
                    for i, (email, password) in enumerate(credentials):
                        logging.info(f"正在尝试使用账户 {i+1}: {email}")
                        url = task['func'](email, password)
                        if url:
                            subscription_urls.append(url)
                        else:
                            logging.warning(f"账户 {email} 未能获取到订阅链接。")
                else:
                    # 回退到单账户逻辑 (环境变量或JSON文件)
                    email = os.environ.get(f"{name.upper()}_EMAIL")
                    password = os.environ.get(f"{name.upper()}_PASSWORD")

                    if not email or not password:
                        if name in json_creds and json_creds[name].get("email") and json_creds[name].get("password"):
                            email = json_creds[name]["email"]
                            password = json_creds[name]["password"]
                            logging.info(f"使用JSON文件中的凭据运行任务: {name}")
                        else:
                            logging.warning(f"跳过 {name}: 未在环境变量或JSON文件中找到完整凭据")
                            continue
                    else:
                        logging.info(f"使用环境变量中的凭据运行任务: {name}")
                    
                    url = task['func'](email, password)
                    if url:
                        subscription_urls.append(url)
            else:
                # 不需要凭据的任务
                url = task['func']()
                if url:
                    subscription_urls.append(url)

        except Exception as e:
            logging.error(f"执行任务 {name} 时发生错误: {e}", exc_info=True)
            continue

        if not subscription_urls:
            logging.error(f"未能获取到任何 {name} 的订阅链接")
            continue

        # 遍历所有获取到的订阅链接
        for i, url in enumerate(subscription_urls):
            logging.info(f"正在处理第 {i+1}/{len(subscription_urls)} 个订阅链接: {url}")
            
            content = get_content_from_url(url)
            if not content:
                logging.error(f"未能从链接获取内容: {url}")
                continue

            nodes = parse_subscription_content(content)
            if not nodes:
                logging.warning(f"从链接未解析到任何有效节点: {url}")
                continue

            valid_nodes = 0
            for node in nodes:
                if isinstance(node, dict) and 'name' in node:
                    original_name = node.get('name', 'Unnamed Node')
                    # 为多账户添加后缀以区分
                    account_suffix = f"_{i+1}" if len(subscription_urls) > 1 else ""
                    node['name'] = f"{task['tag']}{account_suffix} {original_name}"
                    valid_nodes += 1
                else:
                    logging.debug(f"跳过无效节点: {node}")
            
            all_tagged_nodes.extend(nodes)
            logging.info(f"成功处理了 {valid_nodes} 个来自 {task['tag']} (账户 {i+1}) 的节点")

    logging.info(f"总共获取到 {len(all_tagged_nodes)} 个节点")
    return all_tagged_nodes

def load_base_config() -> Optional[Dict[str, Any]]:
    """加载基础配置文件"""
    try:
        if not os.path.exists(BASE_CONFIG_FILE):
            logging.error(f"基础配置文件不存在: {BASE_CONFIG_FILE}")
            return None
        
        with open(BASE_CONFIG_FILE, 'r', encoding='utf-8') as f:
            base_config = yaml.safe_load(f)
        
        if not isinstance(base_config, dict):
            logging.error(f"基础配置文件格式错误: {BASE_CONFIG_FILE}")
            return None
        
        logging.info(f"成功加载基础配置文件: {BASE_CONFIG_FILE}")
        return base_config
        
    except yaml.YAMLError as e:
        logging.error(f"基础配置文件YAML格式错误: {e}")
        return None
    except Exception as e:
        logging.error(f"加载基础配置文件时发生错误: {e}")
        return None

def save_final_config(config: Dict[str, Any]) -> bool:
    """保存最终配置文件"""
    try:
        # 创建备份
        if os.path.exists(OUTPUT_FILE):
            backup_file = f"{OUTPUT_FILE}.backup"
            import shutil
            shutil.copy2(OUTPUT_FILE, backup_file)
            logging.info(f"已创建备份文件: {backup_file}")
        
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, sort_keys=False, allow_unicode=True, default_flow_style=False)
        
        logging.info(f"成功生成合并后的订阅文件: {OUTPUT_FILE}")
        return True
        
    except Exception as e:
        logging.error(f"写入最终配置文件时出错: {e}")
        return False

def main():
    """主函数"""
    # 验证命令行参数
    if len(sys.argv) < 2 or sys.argv[1] not in ['daily', 'weekly']:
        print("用法: python main.py [daily|weekly]")
        print("  daily  - 仅运行blue2sea任务")
        print("  weekly - 运行所有需要凭据的任务")
        sys.exit(1)
    
    run_mode = sys.argv[1]
    logging.info(f"开始运行 {run_mode} 模式")
    
    # 确定要运行的任务
    if run_mode == 'daily':
        tasks_to_run = ['blue2sea']
    else:  # weekly
        tasks_to_run = ['dabai', 'ikuuu', 'louwangzhiyu']
    
    logging.info(f"将运行以下任务: {tasks_to_run}")
    
    # 获取所有节点
    all_nodes = run_tasks_and_get_nodes(tasks_to_run)
    if not all_nodes:
        logging.warning("未能获取到任何有效节点，程序退出")
        sys.exit(0)
    
    # 加载基础配置
    base_config = load_base_config()
    if not base_config:
        logging.error("无法加载基础配置文件，程序退出")
        sys.exit(1)
    
    # 更新配置
    base_config['proxies'] = all_nodes
    all_node_names = [node['name'] for node in all_nodes if isinstance(node, dict) and 'name' in node]
    
    # 按来源分类节点名称
    categorized_node_names = {key: [] for key in TASKS.keys()}
    for node_name in all_node_names:
        for task_key, task_info in TASKS.items():
            if node_name.startswith(task_info['tag']):
                categorized_node_names[task_key].append(node_name)
                break
    
    # 更新代理组
    for group in base_config.get('proxy-groups', []):
        if not isinstance(group, dict) or 'proxies' not in group:
            continue
            
        new_proxies = []
        for proxy_name in group.get('proxies', []):
            if proxy_name == "[AUTO]":
                new_proxies.extend(all_node_names)
            elif proxy_name.startswith("[SITE:"):
                site_key = proxy_name.replace("[SITE:", "").replace("]", "")
                new_proxies.extend(categorized_node_names.get(site_key, []))
            else:
                new_proxies.append(proxy_name)
        
        group['proxies'] = new_proxies
    
    # 保存最终配置
    if save_final_config(base_config):
        logging.info("程序执行完成")
        sys.exit(0)
    else:
        logging.error("保存配置文件失败")
        sys.exit(1)

if __name__ == "__main__":
    main()