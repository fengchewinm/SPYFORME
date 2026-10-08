#!/usr/bin/env python3
"""
定时抓取 cotitoc / viqzes / bestjas / storekyloe 的首页/分类页，
提取商品卡片并存成 JSON。

设计目标：
- 在 GitHub Actions 境外 runner 上跑，避开本机 IP 被封的问题。
- 请求尽量像真实浏览器；失败自动重试带退避。
- 每家店保存 raw HTML + latest.json（供看板消费）。
"""
import json
import re
import time
import html as htmlmod
from pathlib import Path
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

DATA_DIR = Path("data")
RAW_DIR = Path("raw")
DATA_DIR.mkdir(parents=True, exist_ok=True)
RAW_DIR.mkdir(parents=True, exist_ok=True)

# 站点配置：handle、显示名、实际入口 URL、特殊 key
STORES = {
    "cotitoc.com": {
        "name": "cotitoc.com",
        "url": "https://cotitoc.com/collections/all?sort_by=created-descending&key=2026up",
    },
    "viqzes.com": {
        "name": "viqzes.com",
        "url": "https://viqzes.com/collections/all?sort_by=created-descending",
    },
    "bestjas.com": {
        "name": "bestjas.com",
        "url": "https://bestjas.com/collections/all?sort_by=created-descending&key=bestjas2024",
    },
    "storekyloe.co.uk": {
        "name": "storekyloe.co.uk",
        # /collections/all 在主题层被焊死会跳首页；走 all-products（真实在售入口）
        "url": "https://storekyloe.co.uk/collections/all-products?sort_by=created-descending",
    },
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/117.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}


def fetch(url: str, retries: int = 4, timeout: int = 35):
    """带指数退避的 GET。返回 (status_code, text, err_kind)。"""
    session = requests.Session()
    for attempt in range(retries):
        try:
            r = session.get(url, headers=HEADERS, timeout=timeout)
            # Shopify 429 也返回 usable body（如 local_rate_limited），先不抛
            return r.status_code, r.text, None
        except requests.exceptions.Timeout:
            if attempt == retries - 1:
                return 0, "", "timeout"
        except requests.exceptions.ConnectionError as e:
            if attempt == retries - 1:
                return 0, "", f"connection_error:{type(e).__name__}"
        except Exception as e:
            if attempt == retries - 1:
                return 0, "", f"exception:{type(e).__name__}"
        time.sleep(2 ** attempt)  # 1, 2, 4, 8s
    return 0, "", "unknown"


def sanitize(text: str) -> str:
    if not text:
        return ""
    t = htmlmod.unescape(text)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def extract_products(html: str, store: str) -> list:
    """从 Shopify 集合页 HTML 提取商品卡片。"""
    soup = BeautifulSoup(html, "lxml")
    products = []

    # Shopify 常见卡片选择器
    selectors = [
        "li.grid__item",
        "li.product-grid__item",
        "li.collection-product-card",
        ".product-item",
        ".card-wrapper",
        ".grid-item",
    ]
    cards = []
    for sel in selectors:
        cards = soup.select(sel)
        if cards:
            break

    # 兜底：直接搜所有带 /products/ 的链接
    if not cards:
        links = soup.find_all("a", href=re.compile(r"/products/[^\s\"]+"))
        # 按链接去重，每个链接当成一个卡片
        seen_h = set()
        for a in links:
            href = a.get("href", "")
            if not href or href in seen_h:
                continue
            seen_h.add(href)
            cards.append(a.find_parent(["li", "div", "article"]) or a)

    seen = set()
    for card in cards:
        # 标题 / 链接
        a = card.find("a", href=re.compile(r"/products/"))
        if not a:
            continue
        href = a.get("href", "").split("?")[0]
        handle = href.split("/products/")[-1].strip("/")
        if not handle or handle in seen:
            continue
        seen.add(handle)

        title = sanitize(a.get_text())

        # 价格：常见类名
        price = ""
        for cls in ["price", "price__regular", "money", "product-price", "card__price"]:
            el = card.find(class_=re.compile(cls, re.I))
            if el:
                price = sanitize(el.get_text())
                if price:
                    break

        # 图片
        img = ""
        for tag in card.find_all("img"):
            src = tag.get("src") or tag.get("data-src")
            if src:
                img = src if src.startswith("http") else f"https://{store}{src}"
                break

        products.append(
            {
                "handle": handle,
                "title": title,
                "price": price,
                "image": img,
                "product_url": f"https://{store}/products/{handle}",
            }
        )

    return products


def run():
    summary = {}
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")

    for handle, cfg in STORES.items():
        print(f"\n[{handle}] fetching {cfg['url']}")
        status, html, err = fetch(cfg["url"])
        print(f"  status={status} err={err or '-'} html_len={len(html)}")

        # 保存 raw HTML（调试用）
        raw_path = RAW_DIR / f"{handle}_{ts.replace(':', '-')}.html"
        raw_path.write_text(html, encoding="utf-8")

        products = []
        if status == 200 and len(html) > 10000:
            products = extract_products(html, handle)
            print(f"  extracted {len(products)} products")
        else:
            print(f"  skip extraction (status={status}, len={len(html)})")

        payload = {
            "store": handle,
            "name": cfg["name"],
            "fetched_at": ts,
            "source_url": cfg["url"],
            "status_code": status,
            "error": err,
            "html_bytes": len(html),
            "product_count": len(products),
            "products": products,
        }

        store_dir = DATA_DIR / handle
        store_dir.mkdir(parents=True, exist_ok=True)
        (store_dir / "latest.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (store_dir / f"{ts.replace(':', '-')}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        summary[handle] = {
            "status": status,
            "error": err,
            "products": len(products),
            "url": cfg["url"],
        }

    # 汇总
    (DATA_DIR / "summary.json").write_text(
        json.dumps(
            {"generated_at": ts, "stores": summary},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("\nSummary:", json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
