"""Steam: reduzierte Angebote und 100%-Rabatte (Freegames) aus den Store-Specials."""

import logging
from datetime import datetime, timezone

import aiohttp

from modules.free_games.deal import Deal

logger = logging.getLogger("freestuffbot.steam")

_FEATURED_URL = "https://store.steampowered.com/api/featuredcategories"
_APPDETAILS_URL = "https://store.steampowered.com/api/appdetails"
_PARAMS = {"cc": "de", "l": "german"}


async def fetch_candidates(session: aiohttp.ClientSession) -> list[Deal]:
    """Liefert Steam-Angebote aus der 'Specials'-Kategorie (noch ohne Beschreibung/Rating)."""
    async with session.get(_FEATURED_URL, params=_PARAMS, timeout=aiohttp.ClientTimeout(total=20)) as resp:
        resp.raise_for_status()
        payload = await resp.json()

    items = (payload.get("specials") or {}).get("items") or []
    deals: list[Deal] = []

    for item in items:
        if item.get("type") != 0:
            continue  # nur vollwertige Spiele, keine DLC/Bundles/Software

        appid = item.get("id")
        discount_percent = item.get("discount_percent", 0)
        if not appid or discount_percent <= 0:
            continue

        original_price = int(item.get("original_price") or 0)
        final_price = int(item.get("final_price") or 0)
        is_free = final_price == 0 and discount_percent == 100
        expiration_ts = item.get("discount_expiration") or 0
        end_date = (
            datetime.fromtimestamp(expiration_ts, tz=timezone.utc) if expiration_ts else None
        )

        deal_id_suffix = expiration_ts or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        deal_id = f"steam:{appid}:{deal_id_suffix}"

        deals.append(
            Deal(
                deal_id=deal_id,
                source="Steam",
                title=item.get("name", "Unbekanntes Spiel"),
                description="",
                store_url=f"https://store.steampowered.com/app/{appid}/",
                launcher_url=f"steam://store/{appid}",
                image_url=item.get("large_capsule_image") or item.get("header_image"),
                original_price_cents=original_price,
                current_price_cents=final_price,
                currency="EUR",
                end_date=end_date,
                rating=None,
                is_free=is_free,
            )
        )

    return deals


async def enrich(session: aiohttp.ClientSession, deal: Deal) -> Deal:
    """Holt Kurzbeschreibung und Metacritic-Wertung nach (nur für neue, noch nicht geposte Deals)."""
    appid = deal.store_url.rstrip("/").rsplit("/", 1)[-1]
    try:
        async with session.get(
            _APPDETAILS_URL,
            params={"appids": appid, "cc": "de", "l": "german"},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            resp.raise_for_status()
            payload = await resp.json()

        app_data = (payload.get(appid) or {}).get("data") or {}
        description = (app_data.get("short_description") or "").strip()
        metacritic = (app_data.get("metacritic") or {}).get("score")
        rating = f"{metacritic}/100" if metacritic else None

        deal.description = description
        deal.rating = rating
    except (aiohttp.ClientError, KeyError, ValueError) as exc:
        logger.warning("Konnte Steam-Details für App %s nicht laden: %s", appid, exc)

    return deal
