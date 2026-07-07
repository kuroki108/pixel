# Selfrole System / Dropdown Menu
import discord


class RoleSelect(discord.ui.Select):

    multi: bool = False

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("Dieser Befehl kann nur in einem Server verwendet werden.", ephemeral=True)
            return

        member = guild.get_member(interaction.user.id)
        if member is None:
            await interaction.response.send_message("Member nicht gefunden.", ephemeral=True)
            return

        await interaction.response.edit_message(view=self.view)

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


class AgeRoles(RoleSelect):

    def __init__(self):
        super().__init__(
            custom_id="select_age",
            placeholder="Alter",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label="16 bis 17",     value="1519735748637622292"),
                discord.SelectOption(label="18 bis 20",     value="1519735820926320731"),
                discord.SelectOption(label="21 bis 25",     value="1519735859891404930"),
                discord.SelectOption(label="26 bis 30",     value="1519735846029361255"),
                discord.SelectOption(label="31 bis 35",     value="1519735966431055912"),
                discord.SelectOption(label="35 + (Unc)",    value="1519736007245955176"),
            ]
        )


class GenderRoles(RoleSelect):

    def __init__(self):
        super().__init__(
            custom_id="select_gender",
            placeholder="Geschlecht",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label="Männlich",      value="1435591961695490180"),  
                discord.SelectOption(label="Weiblich",      value="1435591966401232928"),
                discord.SelectOption(label="Trans",         value="1436359645211136111"),  
            ]
        )


class StateRoles(RoleSelect):

    def __init__(self):
        super().__init__(
            custom_id="select_state",
            placeholder="Bundesland",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label="Baden-Württemberg",       value="1435592084001259642"),  
                discord.SelectOption(label="Bayern",                  value="1435592057124290643"),   
                discord.SelectOption(label="Berlin",                  value="1435592132793729136"),  
                discord.SelectOption(label="Brandenburg",             value="1435592127026303063"),   
                discord.SelectOption(label="Bremen",                  value="1435592121976356935"),   
                discord.SelectOption(label="Hamburg",                 value="1435592137793208404"),  
                discord.SelectOption(label="Hessen",                  value="1435592062677553283"),              
                discord.SelectOption(label="Mecklenburg-Vorpommern",  value="1435592051868569720"),                
                discord.SelectOption(label="Niedersachsen",           value="1435592078968229928"),                
                discord.SelectOption(label="Nordrhein-Westfalen",     value="1435592067966439464"),                
                discord.SelectOption(label="Rheinland-Pfalz",         value="1435592111591391372"),                
                discord.SelectOption(label="Saarland",                value="1435592088749342862"),                
                discord.SelectOption(label="Sachsen",                 value="1435592073901248563"),                
                discord.SelectOption(label="Sachsen-Anhalt",          value="1435592117534724117"),                
                discord.SelectOption(label="Schleswig-Holstein",      value="1435592098651963502"),                
                discord.SelectOption(label="Thüringen",               value="1435592093518135368"),                
                discord.SelectOption(label="Österreich",              value="1436238374678822922"),                
                discord.SelectOption(label="Schweiz",                 value="1436238722847871016"),          
                ]
        )


class DM_StatusRoles(RoleSelect):

    def __init__(self):
        super().__init__(
            custom_id="select_dm_status",
            placeholder="DM Status",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label="Dm's -offen",             value="1435999472814653550"),
                discord.SelectOption(label="Dm's -anfrage",           value="1436243877911855124"), 
                discord.SelectOption(label="Dm's -close",             value="1436243676371222538"),  
            ]
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
                discord.SelectOption(label="Bump",                      value="1440952671858331739"),  
                discord.SelectOption(label="Umfragen",                  value="1519754279366295782"), 
                discord.SelectOption(label="Neuigkeiten/Ankündigungen", value="1519754313239367921"),  
                discord.SelectOption(label="Giveaways",                 value="1519754361511870575"), 
                discord.SelectOption(label="Events",                    value="1519754339629924453"), 
                discord.SelectOption(label="Minigames",                 value="1519754411000205452"),  
                discord.SelectOption(label="Dead Chat",                 value="1440262128564174939"), 
            ]
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
                discord.SelectOption(label="Spielersuche",               value="1519755098169934015"),  
                discord.SelectOption(label="Minecraft",                  value="1519755129367040101"),  
                discord.SelectOption(label="Dead by Daylight",           value="1519755151592656977"),  
                discord.SelectOption(label="Valorant",                   value="1519755172836937969"),  
                discord.SelectOption(label="Phasmophobia",               value="1519755194093535322"),  
                discord.SelectOption(label="Fortnite",                   value="1519755213106577609"),  
                discord.SelectOption(label="Rocket League",              value="1519755245310316624"),  
                discord.SelectOption(label="Genshin Impact",             value="1519755269553520823"),  
                discord.SelectOption(label="Where the Winds Meet",       value="1519755293829890191"),  
                discord.SelectOption(label="Once Human",                 value="1519755316198117478"),  
                discord.SelectOption(label="Yu-Gi-Oh!",                  value="1519755344874705069"),  
                discord.SelectOption(label="Overwatch",                  value="1519755367251316759"),  
                discord.SelectOption(label="COD",                        value="1519755385513443461"),  
                discord.SelectOption(label="Roblox",                     value="1519755405398507671"),  
                discord.SelectOption(label="League of Legends",          value="1519755430417662105"),  
                discord.SelectOption(label="Helldivers",                 value="1519755448104910949"), 
                discord.SelectOption(label="Warframe",                   value="1519756166563889293"),
                discord.SelectOption(label="Repo",                       value="1519756146049683496"),
            ]
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