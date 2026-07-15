# Selfrole System / Dropdown Menu
import discord


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

        # Rollen per ID suchen statt per Name
        all_group_roles = [
            role for option in self.options
            if (role := guild.get_role(int(option.value)))
        ]

        if self.multi:
            selected_roles = [
                role for role_id in self.values
                if (role := guild.get_role(int(role_id)))
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

            selected = guild.get_role(int(self.values[0]))
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



class GenderRoles(RoleSelect):
    def __init__(self):
        super().__init__(
            custom_id="select_gender",
            placeholder="Geschlecht",
            min_values=0,
            max_values=1,
            options=[
                discord.SelectOption(label="Männlich", value="1525603628298141787"),
                discord.SelectOption(label="Weiblich", value="1525603628298141786"),
                discord.SelectOption(label="Divers", value="1525603628285431917"),
            ],
        )


class AgeRoles(RoleSelect):
    def __init__(self):
        super().__init__(
            custom_id="select_age",
            placeholder="Alter",
            min_values=0,
            max_values=1,
            options=[
                discord.SelectOption(label="16 bis 17", value="1525603628285431915"),
                discord.SelectOption(label="18 bis 20", value="1525603628285431914"),
                discord.SelectOption(label="21 bis 25", value="1525603628285431913"),
                discord.SelectOption(label="26 bis 30", value="1525603628285431912"),
                discord.SelectOption(label="31 bis 35", value="1525603628285431911"),
                discord.SelectOption(label="35 + (Unc)", value="1525603628285431910"),
            ],
        )



class StateRoles(RoleSelect):
    def __init__(self):
        super().__init__(
            custom_id="select_state",
            placeholder="Bundesland",
            min_values=0,
            max_values=1,
            options=[
                discord.SelectOption(label="Baden-Württemberg", value="1525603628285431908"),
                discord.SelectOption(label="Bayern", value="1525603628277039193"),
                discord.SelectOption(label="Berlin", value="1525603628277039192"),
                discord.SelectOption(label="Brandenburg", value="1525603628277039191"),
                discord.SelectOption(label="Bremen", value="1525603628277039190"),
                discord.SelectOption(label="Hamburg", value="1525603628277039189"),
                discord.SelectOption(label="Hessen", value="1525603628277039188"),
                discord.SelectOption(label="Mecklenburg-Vorpommern", value="1525603628277039187"),
                discord.SelectOption(label="Niedersachsen", value="1525603628277039186"),
                discord.SelectOption(label="Nordrhein-Westfalen", value="1525603628277039185"),
                discord.SelectOption(label="Rheinland-Pfalz", value="1525603628277039184"),
                discord.SelectOption(label="Saarland", value="1525603628264722554"),
                discord.SelectOption(label="Sachsen", value="1525603628264722553"),
                discord.SelectOption(label="Sachsen-Anhalt", value="1525603628264722552"),
                discord.SelectOption(label="Schleswig-Holstein", value="1525603628264722551"),
                discord.SelectOption(label="Thüringen", value="1525603628264722550"),
                discord.SelectOption(label="Österreich", value="1525603628264722549"),
                discord.SelectOption(label="Schweiz", value="1525603628264722548"),
            ],
        )


class DM_StatusRoles(RoleSelect):
    def __init__(self):
        super().__init__(
            custom_id="select_dm_status",
            placeholder="DM Status",
            min_values=0,
            max_values=1,
            options=[
                discord.SelectOption(label="Dm's -offen", value="1525603628264722546"),
                discord.SelectOption(label="Dm's -anfrage", value="1525603628264722545"),
                discord.SelectOption(label="Dm's -close", value="1525603628256329918"),
            ],
        )


class PingRoles(RoleSelect):
    multi = True

    def __init__(self):
        super().__init__(
            custom_id="select_ping",
            placeholder="Ping",
            min_values=0,
            max_values=7,
            options=[
                discord.SelectOption(label="Bump", value="1525603628256329916"),
                discord.SelectOption(label="Umfragen", value="1525603628256329915"),
                discord.SelectOption(label="Neuigkeiten/Ankündigungen", value="1525603628256329914"),
                discord.SelectOption(label="Giveaways", value="1525603628256329913"),
                discord.SelectOption(label="Events", value="1525603628256329912"),
                discord.SelectOption(label="Minigames", value="1525603628256329911"),
                discord.SelectOption(label="Dead Chat", value="1525603628256329910"),
            ],
        )


class GamesRoles(RoleSelect):
    multi = True

    def __init__(self):
        super().__init__(
            custom_id="select_games",
            placeholder="Games",
            min_values=0,
            max_values=18,
            options=[
                discord.SelectOption(label="Spielersuche", value="1525603628243484843"),
                discord.SelectOption(label="Minecraft", value="1525603628243484842"),
                discord.SelectOption(label="Dead by Daylight", value="1525603628243484841"),
                discord.SelectOption(label="Valorant", value="1525603628243484840"),
                discord.SelectOption(label="Phasmophobia", value="1525603628243484839"),
                discord.SelectOption(label="Fortnite", value="1525603628243484838"),
                discord.SelectOption(label="Rocket League", value="1525603628243484837"),
                discord.SelectOption(label="Genshin Impact", value="1525603628243484836"),
                discord.SelectOption(label="Where the Winds Meet", value="1525603628243484835"),
                discord.SelectOption(label="Once Human", value="1525603628243484834"),
                discord.SelectOption(label="Yu-Gi-Oh!", value="1525603628235362363"),
                discord.SelectOption(label="Overwatch", value="1525603628235362362"),
                discord.SelectOption(label="COD", value="1525603628235362361"),
                discord.SelectOption(label="Roblox", value="1525603628235362360"),
                discord.SelectOption(label="League of Legends", value="1525603628235362359"),
                discord.SelectOption(label="Helldivers", value="1525603628235362358"),
                discord.SelectOption(label="Warframe", value="1525603628235362357"),
                discord.SelectOption(label="Repo", value="1525603628235362356"),
            ],
        )


class RoleView01(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(GenderRoles())
        self.add_item(AgeRoles())
        self.add_item(StateRoles())
        self.add_item(DM_StatusRoles())


class RoleView02(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(PingRoles())
        self.add_item(GamesRoles())