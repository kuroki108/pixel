"""Epic Games Store: kostenlose Angebote (freeGamesPromotions)."""

import logging
from datetime import datetime, timezone

import aiohttp

from modules.free_games.deal import Deal

logger = logging.getLogger("freestuffbot.epic")

_API_URL = "https://store-site-backend-static-ipv4.ak.epicgames.com/freeGamesPromotions"
_PARAMS = {"locale": "de-DE", "country": "DE", "allowCountries": "DE"}

_IMAGE_PRIORITY = ("OfferImageWide", "DieselStoreFrontWide", "featuredMedia", "Thumbnail")


def _pick_image(key_images: list[dict]) -> str | None:
    by_type = {img.get("type"): img.get("url") for img in key_images}
    for wanted in _IMAGE_PRIORITY:
        if by_type.get(wanted):
            return by_type[wanted]
    return key_images[0]["url"] if key_images else None


def _slug(element: dict) -> str | None:
    offer_mappings = element.get("offerMappings") or []
    if offer_mappings and offer_mappings[0].get("pageSlug"):
        return offer_mappings[0]["pageSlug"]
    catalog_mappings = (element.get("catalogNs") or {}).get("mappings") or []
    if catalog_mappings and catalog_mappings[0].get("pageSlug"):
        return catalog_mappings[0]["pageSlug"]
    return element.get("productSlug") or element.get("urlSlug")


def _parse_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


async def fetch_candidates(session: aiohttp.ClientSession) -> list[Deal]:
    """Liefert aktuell kostenlose Epic-Games-Angebote als fertige Deals."""
    async with session.get(_API_URL, params=_PARAMS, timeout=aiohttp.ClientTimeout(total=20)) as resp:
        resp.raise_for_status()
        payload = await resp.json()

    elements = payload["data"]["Catalog"]["searchStore"]["elements"]
    deals: list[Deal] = []

    for element in elements:
        active_offers = (element.get("promotions") or {}).get("promotionalOffers") or []
        if not active_offers or not active_offers[0].get("promotionalOffers"):
            continue  # nicht aktuell kostenlos (z.B. nur zukünftig angekündigt)

        offer = active_offers[0]["promotionalOffers"][0]
        end_date = _parse_date(offer.get("endDate"))

        total_price = (element.get("price") or {}).get("totalPrice") or {}
        original_price = int(total_price.get("originalPrice", 0))
        discount_price = int(total_price.get("discountPrice", 0))
        currency = total_price.get("currencyCode", "EUR")

        if discount_price != 0:
            continue  # aktuell doch nicht 100% reduziert

        slug = _slug(element)
        if not slug:
            continue
        store_url = f"https://store.epicgames.com/de/p/{slug}"
        launcher_url = f"com.epicgames.launcher://store/product/{slug}"

        deal_id = f"epic:{slug}:{offer.get('endDate')}"

        deals.append(
            Deal(
                deal_id=deal_id,
                source="Epic Games",
                title=element.get("title", "Unbekanntes Spiel"),
                description=(element.get("description") or "").strip(),
                store_url=store_url,
                launcher_url=launcher_url,
                image_url=_pick_image(element.get("keyImages") or []),
                original_price_cents=original_price,
                current_price_cents=discount_price,
                currency=currency,
                end_date=end_date,
                rating=None,
                is_free=True,
            )
        )

    return deals


async def enrich(session: aiohttp.ClientSession, deal: Deal) -> Deal:
    # Epic liefert bereits alle nötigen Infos in einem Request.
    return deal
