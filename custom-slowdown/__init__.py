from .cooldown import CustomCooldown

def setup(bot):
    bot.add_cog(CustomCooldown(bot))