import discord
from datetime import datetime
from redbot.core import commands
import dateutil.parser as date_parser
from .utils import CoronavirusDataApi, Graph, close_menu
import redbot.core.utils.chat_formatting as chat_formatter
from redbot.core.utils.menus import menu, next_page, prev_page

data_client = CoronavirusDataApi()

class CoronavirusStats(commands.Cog):
    """A cog to display Coronavirus spread in the world"""


    def add_stats_field(self, embed, embed_field_index, data : dict, key_name, showed_name,increment_key : str = None):
        """
        embed : discord.Embed, the embed to which edit the field
        embed_field_index : the index of the field to edit
        data : a dict with the data 
        key_name : the key which value will be added to the field
        showd_name = the name that will be showed in the field instead of the key name
        increment_key : the key that represents the increment of cases, if any.
        """
        embed_field_name = embed.fields[embed_field_index].name
        embed_field_value = embed.fields[embed_field_index].value
        if key_name in data:
            updated_field_value = embed_field_value + f"\n•{chat_formatter.underline(showed_name)} : {chat_formatter.humanize_number(data[key_name])}"
            if increment_key and increment_key in data:
                updated_field_value += f"(+{chat_formatter.bold(chat_formatter.humanize_number(data[increment_key]))})"
            embed.set_field_at(index=embed_field_index, name=embed_field_name, value=updated_field_value, inline=True)


    def embed_pages(self, pages, title, embed_desc, set_page_footer : bool = True):
        """
        pages : list of pages to embed
        title : the title of the embed
        embed_desc : the descriptio of the embed
        set_page_footer : to set the footer to the current page es. Page 1/2, Page 2/2
        """
        embeds = []
        for page in pages:
            embed = discord.Embed(title=title, color=discord.Color.red(), description=embed_desc + chat_formatter.box(page))
            embed.set_footer(text=f"Page {pages.index(page)+1}/{len(pages)}")
            embeds.append(embed)
        return embeds
    
    def all_country_pages(self, countries_data):
        """
        Returns a list of the pages with the stats of all the countries.
        countries_data : the data of all the countries retrived with data_client.get_country_stats()
        """
        countries_info = []
        for country in countries_data:
            latest_data = country['latest_data']
            countries_info.append(f"{country['name']}({country['code']}) : {chat_formatter.humanize_number(latest_data['confirmed'])}")
        pages = list(chat_formatter.pagify("\n".join(countries_info), page_length=1500))
        return pages


    @commands.command()
    async def globalstats(self, ctx, date : str = None):
        """
        Command to check global Coronavirus stats
        date : it can be almost any kind of date format for the required date
        Example : 
        [p]globalstats "3 March 2020" or [p]globalstats 3/3/2020 or [p]globalstats "2020 3 March"
        """
        global_data = await data_client.get_global_stats()
        response_embed = discord.Embed(title="Global Coronavirus Stats", color=discord.Color.red())
        current_day_data = {}
        if not date:
            current_day_data = global_data[0]
        else:
            try:
                required_date = date_parser.parse(date)
            except date_parser.ParserError:
                return await ctx.send(chat_formatter.error("The specified date is invalid."))
            current_day_data = [day_data for day_data in global_data if date_parser.parse(day_data['date']).date() == required_date.date()]
        if not current_day_data:
            response_embed.add_field(name="Overall stats", value=chat_formatter.info("No data found for the current day."), inline=True)
            return await ctx.send(embed=response_embed)
        response_embed.add_field(name="Overall stats", value="", inline=True)
        self.add_stats_field(response_embed, 0, current_day_data, "confirmed", "Total cases", "new_confirmed")
        self.add_stats_field(response_embed, 0, current_day_data, "deaths", "Total deaths", "new_deaths")
        self.add_stats_field(response_embed, 0, current_day_data, "recovered", "Total recovered", "new_recovered")
        graph = Graph(ctx.bot, "Global Coronavirus(Sars-Cov2) stats", "Date", "Cases", global_data[::-1], "seaborn")
        await graph.plot("date", "confirmed", "b", "Confirmed cases")
        await graph.plot("date", "deaths", "r", "Deaths")
        await graph.plot("date", "recovered", "g", "Recovered cases")
        await graph.save()
        img_file = discord.File(graph.file_obj, filename='globalstats.png')
        response_embed.set_image(url='attachment://globalstats.png')
        await ctx.send(embed=response_embed, file=img_file)


    @commands.command()
    async def countrystats(self, ctx, country : str = None):
        """
        Command to check country Coronavirus stats
        country : it can be the country name or country code
        Example : 
        [p]countrystats USA or [p]globalstats IT or [p]globalstats "Italy"
        """
        countries_data = await data_client.get_country_stats(get_timeline=True)
        if country is None:
            pages = self.all_country_pages(countries_data)
            embeds = self.embed_pages(pages, "Global Coronavirus stats", "you didn't specify any country. Here are the stats for each affected country\nYou can use the following controls to move through pages\n➡️ : **next page**\n⬅️ : **previous page**\n❌ : **close all pages**", set_page_footer=True)
            controls = {"➡️" : next_page, "❌" : close_menu, "⬅️" : prev_page}
            return await menu(ctx, embeds, controls)
        countries = [country['name'].upper() for country in countries_data] + [country['code'].upper() for country in countries_data]
        if country.upper() not in countries:
            return await ctx.send(chat_formatter.error(f"The country name or code you have entered is invalid or there could be no cases reported for it yet.\nTo get a complete list of affected countries you may use this command withour specifying a country(Example : `{ctx.prefix}countrystats`)"))
        for data in countries_data:
            if data['name'].upper() == country.upper() or data['code'].upper() == country.upper():
                country_data = data
                break
        response_embed = discord.Embed(title=f"{country_data['name']} Coronavirus Stats", color=discord.Color.red())
        if 'timeline' not in country_data.keys():
            response_embed.add_field(name="Overall stats", value=chat_formatter.info("No data found for the current day."), inline=True)
            return await ctx.send(embed=response_embed)
        response_embed.add_field(name="Overall stats", value="", inline=True)
        current_day_data = country_data['timeline'][0]
        timeline_data = country_data['timeline']
        self.add_stats_field(response_embed, 0, current_day_data, "confirmed", "Total cases", "new_confirmed")
        self.add_stats_field(response_embed, 0, current_day_data, "deaths", "Total deaths", "new_deaths")
        self.add_stats_field(response_embed, 0, current_day_data, "recovered", "Total recovered", "new_recovered")
        graph = Graph(ctx.bot, f"{country_data['name']} Coronavirus(Sars-Cov2) stats", "Date", "Cases", timeline_data[::-1], "seaborn")
        await graph.plot("date", "confirmed", "b", "Confirmed cases")
        await graph.plot("date", "deaths", "r", "Deaths")
        await graph.plot("date", "recovered", "g", "Recovered cases")
        await graph.save()
        img_file = discord.File(graph.file_obj, filename='countrystats.png')
        response_embed.set_image(url='attachment://countrystats.png')
        await ctx.send(embed=response_embed, file=img_file)


def setup(bot):
    """Cog setup function"""
    bot.add_cog(CoronavirusStats())