#AIzaSyAUBRU8lkM1hTTlw2smkXh_woWXEJ68Iag
import discord
from redbot.core import commands, Config, checks
import redbot.core.utils.chat_formatting as chat_formatter
import aiohttp
import json

class MessageAnalyzer(commands.Cog):
    """A cog to display stats of messages in a chat"""
    def __init__(self):
        self.API_URL = "https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze"
        self.all_attributes = {
            "TOXICITY" : {},
            "SEVERE_TOXICITY" : {},
            "ATTACK_ON_AUTHOR" : {},
            "ATTACK_ON_COMMENTER" : {},
            "INCOHERENT" : {},
            "INFLAMMATORY" : {},
            "LIKELY_TO_REJECT" : {},
            "OBSCENE" : {},
            "SPAM" : {}
        }
        self.config = Config.get_conf(self, identifier=23112002)
        default_guild = {"required_attributes" : {"TOXICITY" : {}, "SEVERE_TOXICITY" : {}}}
        self.config.register_guild(**default_guild)

    async def analyze_message(self, bot, message : discord.Message, attributes : dict = None):
        required_attributes = self.all_attributes if not attributes else attributes
        api_key = (await bot.get_shared_api_tokens('perspective')).get('api_key')
        params = {'key' : api_key}
        post_data = {"comment" : {"text" : message.content}, "requestedAttributes" : required_attributes}
        async with aiohttp.ClientSession() as session:
            async with session.post(self.API_URL, params=params, json=post_data) as resp:
                resp_data = await resp.json()
                return resp_data
    
    async def message_stats(self, bot, messages, guild_attributes):
        channel_stats = {}
        for message in messages:
            message_stats = await self.analyze_message(bot, message, guild_attributes)
            attributes_scores = message_stats.get("attributeScores")
            if "error" in message_stats or attributes_scores is None:
                pass
            try:
                for attr_name, attr_value in attributes_scores.items():
                    if attr_name not in channel_stats:
                        channel_stats[attr_name] = []
                    channel_stats[attr_name].append(attr_value["summaryScore"]["value"])
            except AttributeError:
                pass
        for key, val in channel_stats.items():
            channel_stats[key] = (sum(val) * 100) / len(val)
        return channel_stats

    @commands.command()
    @commands.guild_only()
    async def analyzechannel(self, ctx, *, channel : discord.TextChannel = None):
        """
        Analyzes the last 50 messages in a channel
        """
        perspective_keys = await ctx.bot.get_shared_api_tokens('perspective')
        if perspective_keys.get('api_key') is None:
            response_embed = discord.Embed(title="API KEY MISSING", color = discord.Color.red(), description = chat_formatter.error(f"The Google Perspective api key hasn't been set yet. [Click here](https://github.com/conversationai/perspectiveapi/tree/master/1-get-started) to get the api key\nAfter you have the api key set it using the following command\n`{ctx.prefix}set api perspective api_key,<api_key>`\n**Note** : `<api_key>` should be directly replaced with the api key you get from Google Dev Console do not put it in `<` `>`"))
            return await ctx.send(embed=response_embed)
        target_channel = ctx.message.channel if channel is None else channel
        msg = await ctx.send("Analyzing...")
        guild_attributes = await self.config.guild(ctx.guild).required_attributes()
        messages = await target_channel.history(limit=50).flatten()
        if not messages:
            return await ctx.send(chat_formatter.error(f"No messages found in {target_channel.mention}"))
        channel_stats = await self.message_stats(ctx.bot, messages, guild_attributes)
        response_embed = discord.Embed(title=f"Analyzed the  last 50 messages", description=f"Channel : {target_channel.mention}" , color=discord.Color.blurple())
        if not channel_stats:
            return await ctx.send(chat_formatter.error("An error occured."))
        for attr_name, attr_percentage in channel_stats.items():
            field_name = " ".join(attr_name.lower().capitalize().split("_"))
            response_embed.add_field(name=field_name, value="{:.2f}%".format(attr_percentage))
        await msg.edit(content = f"Analyzed {target_channel.mention}", embed=response_embed)
        
    @commands.group()
    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def perspectiveset(self, ctx):
        """
        Config options for perspective api
        """
        if ctx.invoked_subcommand is None:
            guild_attributes = await self.config.guild(ctx.guild).required_attributes()
            all_attr_names = [key for key, val in guild_attributes.items()]
            await ctx.send("Here are the current attributes required by your server : ```{}```".format("\n".join(all_attr_names)))



    @perspectiveset.command()
    async def addattr(self, ctx, attribute_name):
        """
        Adds a new attribute that will be analyzed for each message
        """
        guild_attributes = await self.config.guild(ctx.guild).required_attributes()
        if attribute_name not in self.all_attributes:
            all_attr_names = [key for key, val in self.all_attributes.items()]
            return await ctx.send("The attribute name is not valid, the cog only supports the Google Perspective API production attributes and NYT attributes.\n```Here is a list o all the attributes you can add : {}```".format("\n".join(all_attr_names)))
        if attribute_name in guild_attributes:
            return await ctx.send("The attribute is already in your server configuration. No changes were made.")
        guild_attributes[attribute_name] = {}
        await self.config.guild(ctx.guild).required_attributes.set(guild_attributes)
        await ctx.send(f"`{attribute_name}` has been added.")
    
    @perspectiveset.command()
    async def removeattr(self, ctx, attribute_name):
        """
        Remove a new attribute that will be analyzed for each message
        """
        guild_attributes = await self.config.guild(ctx.guild).required_attributes()
        if attribute_name not in self.all_attributes:
            all_attr_names = [key for key, val in self.all_attributes.items()]
            return await ctx.send("The attribute name is not valid, the cog only supports the Google Perspective API production attributes and NYT attributes.\n```Here is a list o all the attributes you can remove : {}```".format("\n".join(all_attr_names)))
        if attribute_name not in guild_attributes:
            return await ctx.send("The attribute is not in your server configuration. No changes were made.")
        del guild_attributes[attribute_name]
        await self.config.guild(ctx.guild).required_attributes.set(guild_attributes)
        await ctx.send(f"`{attribute_name}` has been removed.")
    


def setup(bot):
    """Cog setup function"""
    bot.add_cog(MessageAnalyzer())


