# Selfrole System / Dropdown Menu
import discord


def _resolve_role(guild: discord.Guild, value: str):
    try:
        return guild.get_role(int(value))
    except ValueError:
        return discord.utils.get(guild.roles, name=value)


class RoleSelect(discord.ui.Select):

    multi: bool = False

    async def callback(self, interaction: discord.Interaction):
        # Interaction sofort bestaetigen, damit sie nicht mit 10062 ablaeuft.
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        if guild is None:
            await interaction.followup.send("Dieser Befehl kann nur in einem Server verwendet werden.", ephemeral=True)
            return

        member = guild.get_member(interaction.user.id)
        if member is None:
            await interaction.followup.send("Member nicht gefunden.", ephemeral=True)
            return

        all_group_roles = [
            role for option in self.options
            if (role := _resolve_role(guild, option.value))
        ]

        if self.multi:
            selected_roles = [
                role for role_id in self.values
                if (role := _resolve_role(guild, role_id))
            ]
            roles_to_remove = [r for r in all_group_roles if r in member.roles]
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove)
            if selected_roles:
                await member.add_roles(*selected_roles)
            names = ", ".join(f"**{r.name}**" for r in selected_roles)
            response_text = f"Deine Rollen wurden aktualisiert!\nDu hast jetzt folgende Rollen: {names}" if names else "Alle deine Rollen aus dieser Kategorie wurden entfernt."

        else:
            if not self.values:
                roles_to_remove = [r for r in all_group_roles if r in member.roles]
                if roles_to_remove:
                    await member.remove_roles(*roles_to_remove)
                    response_text = "Deine Rolle in dieser Kategorie wurde entfernt."
                else:
                    response_text = "Du hast in dieser Kategorie aktuell keine Rolle."
                await interaction.followup.send(response_text, ephemeral=True)
                return

            selected = _resolve_role(guild, self.values[0])
            if selected is None:
                await interaction.followup.send(
                    "Oh! Deine Rolle wurde nicht gefunden.\n"
                    "Bitte melde uns dies über unser Ticketsystem.\nDankeschön!",
                    ephemeral=True
                )
                return
            if selected in member.roles:
                await member.remove_roles(selected)
                response_text = f"Du hast die Rolle **{selected.name}** entfernt."
            else:
                roles_to_remove = [r for r in all_group_roles if r in member.roles]
                if roles_to_remove:
                    await member.remove_roles(*roles_to_remove)
                await member.add_roles(selected)
                response_text = f"Du hast die Rolle **{selected.name}** bekommen!"

        await interaction.followup.send(response_text, ephemeral=True)


class AestheticRoles(RoleSelect):
    def __init__(self):
        super().__init__(
            custom_id="select_aesthetic",
            placeholder="aesthetic",
            min_values=0,
            max_values=1,
            options=[
                discord.SelectOption(label="emo ﹒⌗﹒🦇﹒˚₊‧",                     value="1527258414554546226"),
                discord.SelectOption(label="alt.⋆🕸️⋆⁺₊✧",                          value="1527264970926981131"),
                discord.SelectOption(label="indie 𓏲 ๋࣭ ࣪ ˖🎐",                         value="1527265064678330469"),
                discord.SelectOption(label="basic 🤍",                              value="1527265160761184296"),
                discord.SelectOption(label="coquette⋆. 𐙚 ̊",                         value="1527265261604831363"),
                discord.SelectOption(label="stockholm 🐆🪩",                    value="1527265425434480720"),
                discord.SelectOption(label="adam sandler !!",                   value="1527265512701300906"),
            ],
        )


class HolyTriangleRoles(RoleSelect):
    def __init__(self):
        super().__init__(
            custom_id="select_holy_triangle",
            placeholder="holy triangle",
            min_values=0,
            max_values=1,
            options=[
                discord.SelectOption(label="atzig 𓆩☠︎︎ 𓆪",                       value="1527266101829042267"),
                discord.SelectOption(label="mausig ૮₍ ˃ ⤙ ˂ ₎ა",                value="1527266200768348210"),
                discord.SelectOption(label="fotzig 𓂃 ࣪˖ ִֶཐི༏ཋྀ💋ྀིྀི",                  value="1527266284134469682"),
            ],
        )


class VibesRoles(RoleSelect):
    def __init__(self):
        super().__init__(
            custom_id="select_vibes",
            placeholder="vibes",
            min_values=0,
            max_values=1,
            options=[
                discord.SelectOption(label="black cat ᓚᘏᗢ",                 value="1527266493287632937"),
                discord.SelectOption(label="golden retriever ꒰🐾୭",          value="1527266598652608574"),
                discord.SelectOption(label="hater❤️‍🔥",                       value="1527266695440240720"),
                discord.SelectOption(label="witch ⋆.˚ ☾⭒.˚",               value="1527266820246081597"),
                discord.SelectOption(label="lover ❤️",                      value="1527266971060539462"),
            ],
        )


class CharacterRoles(RoleSelect):
    multi = True

    def __init__(self):
        super().__init__(
            custom_id="select_character",
            placeholder="character",
            min_values=0,
            max_values=13,
            options=[
                discord.SelectOption(label="yolo",                              value="1527268437846397018"),
                discord.SelectOption(label="smd",                               value="1527268487448367114"),
                discord.SelectOption(label="lol",                               value="1527268535087271936"),
                discord.SelectOption(label="extrovertiert",                     value="1527268595435048960"),
                discord.SelectOption(label="introvertiert",                     value="1527268643740713081"),
                discord.SelectOption(label="süssmaus ˚.🎀༘⋆",                  value="1527268698551881838"),
                discord.SelectOption(label="sleepyhead ᶻ 𝗓 𐰁 .ᐟ",                value="1527268765027405935"),
                discord.SelectOption(label="gamer 👾",                          value="1527268817674305536"),
                discord.SelectOption(label="baddie ──★˙🍓̟!!",                  value="1527268868110942249"),
                discord.SelectOption(label="booklover 📖",                     value="1527268916911407226"),      
                discord.SelectOption(label="nerd 🤓",                          value="1527268979746279585"),
                discord.SelectOption(label="anime freak (˶˃ ᵕ ˂˶)",            value="1527269078325133403"),
                discord.SelectOption(label="music-lover ♬⋆⸜ 🎧✮",             value="1527269138236440616"),
            ],
        )


class cute_roles(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(AestheticRoles())
        self.add_item(HolyTriangleRoles())
        self.add_item(VibesRoles())
        self.add_item(CharacterRoles())

