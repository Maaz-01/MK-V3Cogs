from .analyzer import MessageAnalyzer

def setup(bot):
    bot.add_cog(MessageAnalyzer())