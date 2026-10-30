from typing import Any
from urllib.parse import quote

from conf.config import settings
from infrastructure.http_client import http_client


def _base_url() -> str:
    return settings.commerce_api_base_url.rstrip("/")


def _extract_data(result: dict | None) -> dict | None:
    data = result.get("data") if isinstance(result, dict) else None
    return data if isinstance(data, dict) else None


async def fetch_order(order_id: str) -> dict | None:
    try:
        r = await http_client.get(f"{_base_url()}/orders/{quote(order_id)}")
        return _extract_data(r.json())
    except Exception:
        return None


async def fetch_logistics(order_id: str) -> dict | None:
    try:
        r = await http_client.get(f"{_base_url()}/orders/{quote(order_id)}/logistics")
        return _extract_data(r.json())
    except Exception:
        return None


async def fetch_product(product_id: str) -> dict | None:
    try:
        r = await http_client.get(f"{_base_url()}/products/{quote(product_id)}")
        return _extract_data(r.json())
    except Exception:
        return None

def _build_order_summary(payload: dict[str, Any]) -> str:
    parts = []

    # 金额为 0 时也应该显示
    if payload.get("amount") is not None:
        parts.append(f"订单金额￥{payload['amount']}")

    items = payload.get("items") or []
    titles = [
        str(item.get("title") or "").strip()
        for item in items[:2]
        if item.get("title")
    ]

    if titles:
        parts.append("商品:" + "、".join(titles))

    return "。".join(parts) + "。" if parts else ""
