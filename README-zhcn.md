# 免费机场节点订阅链接收集器

这是一个用于自动登录多个机场网站，获取其免费节点的订阅链接，并将所有节点合并到一个Clash订阅文件中的Python项目。

## ✨ 功能特性

- **多站点支持**: 内置了多个机场的客户端，可轻松扩展。
- **自动登录**: 模拟登录网站，自动处理签到、购买免费套餐等操作。
- **智能解析**: 能够解析Clash (YAML) 和 Base64 编码的多种节点格式 (SS, Vmess, Trojan)。
- **配置合并**: 将获取到的所有节点自动合并到一个预设的Clash配置文件模板中。
- **灵活配置**: 支持两种凭据配置方式：
    1.  **本地测试**: 通过 `用户名和密码.json` 文件快速进行本地调试。
    2.  **持续集成**: 通过环境变量在 GitHub Actions 等CI/CD环境中安全地运行。
- **详细日志**: 记录详细的运行日志，方便追踪问题。
- **出错截图**: 对于使用浏览器模拟的客户端 (如ikuuu)，在出错时会自动保存截图和页面源码，便于调试。

## 📂 项目结构

```
.
├── .github/workflows/      # GitHub Actions 配置文件
│   ├── daily_update.yml
│   └── weekly_update.yml
├── clients/                # 存放所有机场客户端的目录
│   ├── __init__.py
│   ├── dabai_client.py
│   ├── huaxia_client.py
│   ├── ikuuu_client.py
│   └── louwangzhiyu_client.py
├── .gitignore
├── base.yaml               # Clash的基础配置模板文件
├── main.py                 # 项目主程序
├── merged_subscription.yaml  # 最终生成的合并订阅文件
├── requirements.txt        # Python依赖列表
├── 用户名和密码.json         # (可选) 用于本地测试的凭据文件
└── README-zhcn.md          # 本文档
```

- **`main.py`**: 项目的入口和主逻辑，负责调度各个客户端、解析内容和生成最终配置。
- **`clients/`**: 核心目录，每个文件对应一个机场的客户端实现。要添加新的机场，主要就是在此目录下添加新文件。
- **`base.yaml`**: Clash的模板配置文件。脚本会将所有获取到的节点填入此文件的 `proxies` 部分，并根据 `proxy-groups` 的占位符 (`[AUTO]`, `[SITE:...]`) 自动创建代理组。
- **`merged_subscription.yaml`**: 脚本成功运行后生成的最终Clash订阅文件，可以直接使用。
- **`用户名和密码.json`**: **仅用于本地测试**。为了方便调试，脚本被修改为可以从此文件读取凭据。此文件不应上传到GitHub。
- **`.github/workflows/`**: GitHub Actions的配置文件，用于实现自动化每日/每周更新。

## 🚀 如何使用

### 1. 环境准备

- 安装 [Python 3](https://www.python.org/)
- 确保 `pip` 可用

### 2. 安装依赖

在项目根目录下打开命令行，运行：
```bash
pip install -r requirements.txt
```
这会自动安装 `requests`, `pyyaml`, `beautifulsoup4`, `selenium` 等所有必需的库。

### 3. 配置凭据

你有两种方式来配置机场的登录凭据：

**方式一：本地测试 (推荐)**

1.  在项目根目录下，找到 `用户名和密码.json` 文件（如果不存在，请创建一个）。
2.  参照以下格式，填入您在各个网站的邮箱和密码：

    ```json
    {
      "ikuuu": {
        "username1": "your_ikuuu_email@example.com",
        "password1": "your_ikuuu_password",
        "username2": "your_ikuuu_email2@example.com",
        "password2": "your_ikuuu_password2"

      },
      "大白": {
        "username1": "your_dabai_email@example.com",
        "password1": "your_dabai_password"
      },
      "华夏联盟": {
        "username1": "your_huaxia_email@example.com",
        "password1": "your_huaxia_password"
      },
      "漏网之鱼": {
        "username1": "your_louwangzhiyu_email@example.com",
        "password1": "your_louwangzhiyu_password"
      }
    }
    ```
    **注意**: JSON的键名（如 "大白"）需要与代码中的中文名对应。

**方式二：生产环境 / GitHub Actions**

在生产环境或CI/CD中，你应该使用环境变量来设置凭据，以确保安全。脚本会优先读取环境变量。

你需要设置以下格式的环境变量：
- `DABAI_EMAIL` / `DABAI_PASSWORD`
- `IKUUU_EMAIL` / `IKUUU_PASSWORD`
- `WWN_EMAIL` / `WWN_PASSWORD`
- `LOUWANGZHIYU_EMAIL` / `LOUWANGZHIYU_PASSWORD`

**方式三：GitHub Actions (多账户支持)**

为了支持单个机场（例如ikuuu）的多个账户，项目引入了新的环境变量格式。当检测到这种格式的环境变量时，程序会自动遍历所有账户并分别获取订阅。

你需要设置以下格式的环境变量：
- `IKUUU_CREDENTIALS`
- `DABAI_CREDENTIALS`
- ...

**格式说明**:
将多个账户的 `邮箱,密码` 用逗号连接，不同账户之间用分号 `;` 分隔。

**示例**:
假设你有两个ikuuu账户，你应该创建一个名为 `IKUUU_CREDENTIALS` 的环境变量，其值为：
```
user1@example.com,password123;user2@another.com,password456
```

**注意**:
- 这种 `_CREDENTIALS` 格式的环境变量**优先级最高**。如果同时设置了 `IKUUU_CREDENTIALS` 和 `IKUUU_EMAIL`，程序将只使用 `IKUUU_CREDENTIALS`。
- 这种方式目前主要用于 GitHub Actions，本地测试请继续使用 `用户名和密码.json` 文件。

### 4. 运行脚本

配置好凭据后，在项目根目录运行：
```bash
python main.py weekly
```
脚本会依次执行所有任务，并将结果保存在 `merged_subscription.yaml` 文件中。

## 🛠️ 各客户端现状

在最近一次测试中，各个客户端的状态如下：

| 客户端 | 状态 | 备注 |
| :--- | :--- | :--- |
| **大白 (dabai)** | ✅ **工作正常** | 能够稳定登录并获取节点。 |
| **华夏联盟 (wwn)** | ❌ **获取失败** | 登录成功，但其提供的订阅链接返回空内容。 |
| **ikuuu** | ❌ **不稳定** | 网站前端复杂且有不稳定的弹窗，导致Selenium模拟登录时常失败。 |
| **漏网之鱼** | ❌ **获取失败** | 网站有高级的反爬虫机制，无法通过简单请求登录。 |


