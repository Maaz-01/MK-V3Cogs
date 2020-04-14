import aiohttp
import matplotlib
import discord
import functools
from io import BytesIO
import matplotlib.pyplot as plt
from redbot.core.utils.menus import menu
import redbot.core.utils.chat_formatting as chat_formatter

matplotlib.use('Agg')

class CoronavirusDataApi:
    def __init__(self):
        self.GLOBAL_STATS_URL = 'https://corona-api.com/timeline'
        self.COUNTRY_STATS_URL = 'https://corona-api.com/countries'
    

    async def get_global_stats(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(self.GLOBAL_STATS_URL) as resp:
                resp_data = await resp.json()
                return resp_data['data']
    

    async def get_country_stats(self, get_timeline : bool = False):
        async with aiohttp.ClientSession() as session:
            params = {'include' : 'timeline'} if get_timeline else {}
            async with session.get(self.COUNTRY_STATS_URL, params=params) as resp:
                resp_data = await resp.json()
                return resp_data['data']

class Graph:
    def __init__(self, bot, title : str, x_label : str, y_label : str, data : list, plot_style):
        self.bot = bot
        self.plot_style = plot_style
        self.file_obj = BytesIO()
        self.data = data
        plt.style.use(plot_style)
        self.fig, self.ax = plt.subplots(tight_layout=True)
        self.ax.set_xlabel(x_label)
        self.ax.set_ylabel(y_label)
        self.ax.set_title(title)
    

    def _plot(self, x_field, y_field : str, line_spec : str = "", label : str = None):
        """
        This is the sync function which should not be used to plots the data, it should not be run because it blocks the event loop, call plot() instead which runs this function in an executor
        """
        if not self.data:
            return
        x_values = [x[x_field] for x in self.data]
        y_values = [x[y_field] for x in self.data]
        self.ax.plot_date(x_values, y_values, line_spec, label=label)
    

    async def plot(self, x_field, y_field : str, line_spec : str = "", label : str = None):
        """
        Plots the data required
        """
        plot_function = functools.partial(self._plot, x_field, y_field, line_spec, label)
        await self.bot.loop.run_in_executor(None, plot_function)
    

    def _save(self):
        """
        This is the sync function which should not be used to save the plot, it should not be run because it blocks the event loop, call save() instead which runs this function in an executor
        """
        self.ax.ticklabel_format(style='plain', axis='y')
        self.ax.legend()
        for label in self.ax.xaxis.get_ticklabels()[::2]:
            label.set_visible(False) 
        self.fig.autofmt_xdate()
        plt.xticks(rotation=90)
        plt.savefig(self.file_obj, format="png")
        self.file_obj.seek(0)


    async def save(self):
        """
        Saves the plot
        """
        save_function = functools.partial(self._save)
        await self.bot.loop.run_in_executor(None, save_function)

        
#Custom menu close function to add ✅ to the command invoke mesage once the menu is closed
async def close_menu(ctx, pages, controls, message, page, timeout, emoji):
    try:
        await message.delete()
    except discord.NotFound:
        pass
    try:
        await ctx.message.add_reaction("✅")
    except discord.NotFound:
        pass