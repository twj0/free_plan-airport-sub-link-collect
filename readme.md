[![Daily Subscription Update (Blue2sea)](https://github.com/twj0/free_plan-airport-sub-link-collect/actions/workflows/daily_update.yml/badge.svg)](https://github.com/twj0/free_plan-airport-sub-link-collect/actions/workflows/daily_update.yml)
[![Weekly Subscription Update](https://github.com/twj0/free_plan-airport-sub-link-collect/actions/workflows/weekly_update.yml/badge.svg)](https://github.com/twj0/free_plan-airport-sub-link-collect/actions/workflows/weekly_update.yml)



---

```markdown


[![Update Subscriptions](https://github.com/twj0/free_plan-airport-sub-link-collect/actions/workflows/weekly_update.yml/badge.svg)](https://github.com/twj0/free_plan-airport-sub-link-collect/actions/workflows/weekly_update.yml)

一个通过 GitHub Actions 自动聚合多个来源的订阅链接，并生成一个单一、强大的 Clash 配置文件的项目。




本项目生成的最终sub文件位于:
```
https://raw.githubusercontent.com/twj0/free_plan-airport-sub-link-collect/main/merged_subscription.yaml
```



## 🔧 如何部署自己的版本

如果您想搭建自己的订阅聚合器，可以按照以下步骤操作：

1.  **Fork 本仓库** 到您自己的 GitHub 账户。

2.  **准备客户端脚本**: 在 `clients/` 目录下，为您想要聚合的网站编写相应的客户端脚本。每个脚本需要提供一个 `get_subscription(email, password)` 函数，返回该网站的原始订阅链接URL。

3.  **配置 `main.py`**:
    - 在 `TASKS` 字典中，添加或修改您的任务配置，包括 `tag` (节点前缀) 和对应的 `func` (处理函数)。

4.  **配置 `base.yaml`**:
    - 这是您的 Clash 配置文件模板。根据您的偏好，修改 `proxy-groups` 和 `rules`。
    - 使用 `[AUTO]` 占位符来自动填充所有节点。
    - 使用 `[SITE:任务名]` 占位符来创建按来源分类的代理组 (例如 `[SITE:dabai]`)。

5.  **设置 GitHub Secrets**:
    - 在您 Fork 后的仓库中，进入 `Settings` > `Secrets and variables` > `Actions`。
    - 点击 `New repository secret`，为每个需要登录的网站添加对应的 `_EMAIL` 和 `_PASSWORD`。例如：
      - `DABAI_EMAIL`: 大白网站的邮箱
      - `DABAI_PASSWORD`: 大白网站的密码
      - `IKUUU_EMAIL`: ikuuu网站的邮箱
      - `IKUUU_PASSWORD`: ikuuu网站的密码
      - ...以此类推。

6.  **启用 GitHub Actions**:
    - 在仓库的 `Actions` 标签页，启用工作流（Workflows）。
    - 您可以手动触发一次 `Weekly Subscription Update` 来立即测试整个流程。

## ⚠️ 免责声明

- 本项目仅用于技术学习和研究，请勿用于任何非法用途。
- 项目中涉及的脚本和配置仅为示例，用户需自行承担使用风险。
