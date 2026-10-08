#!/usr/bin/env python3
"""从 data/*/latest.json 生成静态看板 public/index.html。"""
import json
import html as htmlmod
from pathlib import Path
from datetime import datetime

DATA_DIR = Path("data")
PUBLIC_DIR = Path("public")
PUBLIC_DIR.mkdir(parents=True, exist_ok=True)


def fmt_ts(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return ts


def build():
    summary = json.loads((DATA_DIR / "summary.json").read_text(encoding="utf-8"))
    stores_html = []

    for handle, meta in summary["stores"].items():
        latest_path = DATA_DIR / handle / "latest.json"
        if not latest_path.exists():
            continue
        data = json.loads(latest_path.read_text(encoding="utf-8"))
        products = data.get("products", [])
        status = data.get("status_code") or meta.get("status", "?")
        error = data.get("error") or meta.get("error")

        status_color = "#15803d" if status == 200 else "#b91c1c"
        status_text = f"HTTP {status}" if status else f"失败: {error or 'unknown'}"

        cards = []
        for p in products[:60]:  # 每店最多显示 60 个
            img_tag = ""
            if p.get("image"):
                img_tag = f'<img src="{htmlmod.escape(p["image"])}" alt="" loading="lazy">'
            else:
                img_tag = '<div class="noimg"></div>'

            title = htmlmod.escape(p.get("title", ""))
            price = htmlmod.escape(p.get("price", "")) or "—"
            product_url = htmlmod.escape(p.get("product_url", ""))
            raw_url = htmlmod.escape(meta.get("url", ""))

            cards.append(
                f"""<div class="card">
                    {img_tag}
                    <div class="ct">
                        <div class="cp">{price}</div>
                        <div class="cn" title="{title}">{title}</div>
                        <a class="ch" href="{product_url}" target="_blank" rel="noreferrer">原站商品页</a>
                    </div>
                </div>"""
            )

        if not cards:
            cards.append(
                '<div class="empty">没有抓到商品。可能是 upstream 返回了风控页/限流页，'
                '可点上方「源 URL」查看 raw HTML 或到 GitHub Actions 日志看详情。</div>'
            )

        json_url = f"data/{handle}/latest.json"
        stores_html.append(
            f"""<section class="store" id="{handle}">
                <div class="store-header">
                    <h2>{htmlmod.escape(handle)}</h2>
                    <div class="meta">
                        <span class="status" style="color:{status_color};border-color:{status_color}">{status_text}</span>
                        <span>抓取时间: {fmt_ts(data.get('fetched_at', ''))}</span>
                        <span>商品数: {len(products)}</span>
                        <a href="{htmlmod.escape(meta.get('url', ''))}" target="_blank" rel="noreferrer">源 URL</a>
                        <a href="{json_url}">latest.json</a>
                    </div>
                </div>
                <div class="grid">{''.join(cards)}</div>
            </section>"""
        )

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>四家店跟款看板</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{ margin: 0; padding: 30px 24px 80px; background: #f3f4f6; color: #111827;
                font: 14px/1.6 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif; }}
        .wrap {{ max-width: 1280px; margin: 0 auto; }}
        h1 {{ font-size: 22px; margin: 0 0 4px; }}
        .sub {{ color: #6b7280; font-size: 12.5px; margin-bottom: 22px; }}
        .store {{ background: #fff; border: 1px solid #e5e7eb; border-radius: 14px; padding: 18px 20px 24px; margin-bottom: 22px; }}
        .store-header {{ display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 10px; margin-bottom: 14px; }}
        .store-header h2 {{ margin: 0; font-size: 18px; }}
        .meta {{ display: flex; flex-wrap: wrap; gap: 10px 16px; align-items: center; color: #4b5563; font-size: 12.5px; }}
        .meta a {{ color: #1d4ed8; text-decoration: none; }}
        .meta a:hover {{ text-decoration: underline; }}
        .status {{ border: 1px solid currentColor; border-radius: 20px; padding: 1px 9px; font-weight: 600; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 14px; }}
        .card {{ border: 1px solid #e5e7eb; border-radius: 12px; overflow: hidden; display: flex; flex-direction: column; background: #fff; }}
        .card img {{ width: 100%; height: 150px; object-fit: cover; background: #f3f4f6; }}
        .noimg {{ width: 100%; height: 150px; background: #f3f4f6; }}
        .ct {{ padding: 10px 12px 13px; display: flex; flex-direction: column; gap: 4px; flex: 1; }}
        .cp {{ color: #b91c1c; font-weight: 700; font-size: 14px; }}
        .cn {{ font-size: 12.5px; color: #111827; line-height: 1.45; flex: 1; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }}
        .ch {{ font-size: 11.5px; color: #1d4ed8; margin-top: 6px; }}
        .empty {{ grid-column: 1 / -1; color: #9ca3af; padding: 18px 0; }}
        .footer {{ color: #9ca3af; font-size: 12px; text-align: center; margin-top: 10px; }}
    </style>
</head>
<body>
    <div class="wrap">
        <h1>四家店跟款看板</h1>
        <div class="sub">cotitoc / viqzes / bestjas / storekyloe ｜ 数据来自 GitHub Actions 定时抓取 ｜ 生成于 {fmt_ts(summary.get('generated_at', ''))}</div>
        {''.join(stores_html)}
        <div class="footer">如果某家长时间失败或商品数为 0，说明该次 runner IP 也被风控，等下一轮 schedule 自动重试。</div>
    </div>
</body>
</html>"""

    (PUBLIC_DIR / "index.html").write_text(html, encoding="utf-8")
    # 同时把 data 复制到 public，方便 Pages 直接访问 latest.json
    import shutil
    if (PUBLIC_DIR / "data").exists():
        shutil.rmtree(PUBLIC_DIR / "data")
    shutil.copytree(DATA_DIR, PUBLIC_DIR / "data")
    print(f"Dashboard written to {PUBLIC_DIR / 'index.html'}")


if __name__ == "__main__":
    build()
