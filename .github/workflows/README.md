四家店跟款 GitHub Actions 抓取器
作用：用 GitHub Actions 的境外 runner 定时抓取 cotitoc.com / viqzes.com / bestjas.com / storekyloe.co.uk，
避开本机 IP 被 Cloudflare / Shopify 限流的问题。

你只需做三件事
1. 在 GitHub 上创建空仓库
打开 https://github.com/new ，仓库名随便（例如 store-radar-actions），不要初始化 README。

2. 把这些文件推上去
在本目录打开 Git Bash / PowerShell，运行：


# 如果还没初始化 git
 git init
 git add .
 git commit -m "init store radar fetcher"

# 把下面 URL 换成你自己的仓库地址
 git branch -M main
 git remote add origin https://github.com/<你的用户名>/<仓库名>.git
 git push -u origin main
3. 打开两个 GitHub 设置
Actions 权限：仓库 → Settings → Actions → General → Workflow permissions → 选 Read and write permissions（让 workflow 能写 gh-pages 分支）。
Pages 源：仓库 → Settings → Pages → Source → 选 Deploy from a branch → Branch 选 gh-pages → / (root) → Save。
第一次推完代码后，去 Actions 标签页手动触发一次 Fetch four stores，等它跑完。之后每 6 小时自动跑一次。

怎么看结果
看板地址：https://<你的用户名>.github.io/<仓库名>/
原始数据：https://<你的用户名>.github.io/<仓库名>/data/<store>/latest.json
调试日志：每次 run 的 Actions 日志里会打印 status / 商品数 / 错误。
如果某次失败
GitHub Actions 的 runner IP 也可能被风控，但 schedule 会自动重试。你可以在 fetch.py 里调：

HEADERS 里的 User-Agent
fetch() 里的重试次数和退避
每家店的入口 URL（STORES 字典）
限制
这是绕开「本机 IP 被封」的免费方案，不保证 100% 成功，但比本地死磕稳定得多。
如果 GitHub runner 也被 Cloudflare 大规模拦截，再考虑加 ScraperAPI/代理（需要 API key）。

目录

