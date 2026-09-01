import discord

from modules.free_games.deal import Deal

_COLOR_FREE = 0x2ECC71
_COLOR_DISCOUNT = 0xF39C12

_SOURCE_ICONS = {
    "Epic Games": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/31/Epic_Games_logo.svg/512px-Epic_Games_logo.svg.png",
    "Steam": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/83/Steam_icon_logo.svg/512px-Steam_icon_logo.svg.png",
}

def _format_price(cents: int) -> str:
    return f"{cents / 100:.2f} €".replace(".", ",")


def _format_date(deal: Deal) -> str | None:
    if not deal.end_date:
        return None
    return f"<t:{int(deal.end_date.timestamp())}:D>"


def build_embed(deal: Deal) -> discord.Embed:
    embed = discord.Embed(
        title=deal.title,
        description=deal.description[:400] if deal.description else None,
        color=_COLOR_FREE if deal.is_free else _COLOR_DISCOUNT,
        url=deal.store_url,
    )

    if deal.is_free:
        price_value = f"~~{_format_price(deal.original_price_cents)}~~  **KOSTENLOS**"
    else:
        price_value = f"~~{_format_price(deal.original_price_cents)}~~  **{_format_price(deal.current_price_cents)}**"
    embed.add_field(name="Preis", value=price_value, inline=True)

    until = _format_date(deal)
    if until:
        embed.add_field(name="Verfügbar bis", value=until, inline=True)

    if deal.rating:
        embed.add_field(name="Bewertung", value=f"{deal.rating} ★", inline=True)

    if deal.image_url:
        embed.set_image(url=deal.image_url)

    icon = _SOURCE_ICONS.get(deal.source)
    if icon:
        embed.set_thumbnail(url=icon)

    embed.set_footer(text=deal.source)
    return embed


def build_view(deal: Deal) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="Im Browser öffnen", url=deal.store_url))
    return view
