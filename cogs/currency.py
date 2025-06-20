import discord
from discord.ext import commands
import requests
import json
import os
from datetime import datetime

class Currency(commands.Cog):
    """Currency conversion and crypto tracking commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self.base_url = "https://api.exchangeratesapi.io/v1"
        self.free_api_key = "3a1f2b7c4d6e5f8a9b0c1d2e3f4a5b6c"  # Free API key with limited functionality
        self.watchlist_path = "data/watchlist.json"
        
        # Create watchlist file if it doesn't exist
        os.makedirs(os.path.dirname(self.watchlist_path), exist_ok=True)
        if not os.path.exists(self.watchlist_path):
            with open(self.watchlist_path, "w") as f:
                json.dump({}, f)
    
    @commands.command(name="convert")
    async def convert_currency(self, ctx, amount: float, from_currency: str, to_currency: str):
        """Convert between currencies
        
        Example: !convert 100 usd eur
        """
        try:
            # Make API request using the free API
            from_currency = from_currency.upper()
            to_currency = to_currency.upper()
            
            # Using the free exchangeratesapi.io endpoint
            response = requests.get(
                f"https://open.er-api.com/v6/latest/{from_currency}"
            )
            data = response.json()
            
            if data.get("result") != "success" or to_currency not in data.get("rates", {}):
                await ctx.send(f"❌ Error: Could not convert {from_currency} to {to_currency}. Check currency codes.")
                return
            
            # Calculate the result
            rate = data.get("rates", {}).get(to_currency, 0)
            result = amount * rate
            
            embed = discord.Embed(
                title=f"Currency Conversion",
                description=f"💱 {amount} {from_currency.upper()} = {result:.2f} {to_currency.upper()}",
                color=discord.Color.green()
            )
            embed.add_field(name="Exchange Rate", value=f"1 {from_currency.upper()} = {rate} {to_currency.upper()}")
            embed.set_footer(text=f"🌐 Source: exchangerate.host • {datetime.now().strftime('%Y-%m-%d')}")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")
    
    @commands.command(name="crypto")
    async def crypto_price(self, ctx, symbol: str):
        """Get current crypto price in USD, EUR, and BTC
        
        Example: !crypto btc
        """
        try:
            symbol = symbol.upper()
            
            # For crypto, we'll use CoinGecko API which is free and doesn't require API key
            response = requests.get(f"https://api.coingecko.com/api/v3/coins/list")
            coins = response.json()
            
            # Find the coin by symbol
            coin_id = None
            coin_name = None
            for coin in coins:
                if coin.get("symbol", "").upper() == symbol:
                    coin_id = coin.get("id")
                    coin_name = coin.get("name")
                    break
            
            if not coin_id:
                await ctx.send(f"❌ Error: Could not find cryptocurrency with symbol {symbol}")
                return
            
            # Get price data
            price_response = requests.get(
                f"https://api.coingecko.com/api/v3/simple/price",
                params={
                    "ids": coin_id,
                    "vs_currencies": "usd,eur,btc"
                }
            )
            price_data = price_response.json()
            
            if coin_id not in price_data:
                await ctx.send(f"❌ Error: Could not get price data for {symbol}")
                return
            
            # Get rates
            usd_rate = price_data.get(coin_id, {}).get("usd", 0)
            eur_rate = price_data.get(coin_id, {}).get("eur", 0)
            btc_rate = price_data.get(coin_id, {}).get("btc", 0)
            
            embed = discord.Embed(
                title=f"{coin_name} ({symbol})",
                description="Current cryptocurrency prices",
                color=discord.Color.gold()
            )
            
            embed.add_field(name="USD", value=f"${usd_rate:.2f}", inline=True)
            embed.add_field(name="EUR", value=f"€{eur_rate:.2f}", inline=True)
            embed.add_field(name="BTC", value=f"{btc_rate} BTC", inline=True)
            embed.set_footer(text=f"🌐 Source: CoinGecko • {datetime.now().strftime('%Y-%m-%d')}")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")
    
    @commands.command(name="currencies")
    async def list_currencies(self, ctx):
        """List all supported currency codes"""
        try:
            # Using the free API to get supported currencies
            response = requests.get("https://open.er-api.com/v6/latest/USD")
            data = response.json()
            
            if data.get("result") != "success":
                await ctx.send("❌ Error: Could not fetch currency list")
                return
            
            symbols = list(data.get("rates", {}).keys())
            
            # Show first 20 currencies with ellipsis
            currency_display = ", ".join(symbols[:20])
            if len(symbols) > 20:
                currency_display += "..."
            
            embed = discord.Embed(
                title="Supported Currencies",
                description=f"💱 {currency_display}",
                color=discord.Color.blue()
            )
            embed.set_footer(text="Use ISO codes with !convert (e.g., USD, EUR, GBP)")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")
    
    @commands.command(name="rate")
    async def exchange_rate(self, ctx, from_currency: str, to_currency: str):
        """Check current exchange rate between two currencies
        
        Example: !rate gbp jpy
        """
        try:
            from_currency = from_currency.upper()
            to_currency = to_currency.upper()
            
            # Get exchange rate using the free API
            response = requests.get(f"https://open.er-api.com/v6/latest/{from_currency}")
            data = response.json()
            
            if data.get("result") != "success" or to_currency not in data.get("rates", {}):
                await ctx.send(f"❌ Error: Could not get rate for {from_currency} to {to_currency}")
                return
            
            rate = data.get("rates", {}).get(to_currency, 0)
            date = data.get("time_last_update_utc", datetime.now().strftime("%Y-%m-%d"))
            
            # Try to get flag emojis
            from_flag = self._get_flag_emoji(from_currency[:2])
            to_flag = self._get_flag_emoji(to_currency[:2])
            
            embed = discord.Embed(
                title=f"{from_flag} {from_currency} → {to_flag} {to_currency}",
                description=f"💹 Rate: 1 {from_currency} = {rate} {to_currency}",
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"📅 Updated: {date}")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")
    
    def _get_flag_emoji(self, country_code):
        """Convert country code to flag emoji"""
        if len(country_code) != 2:
            return "🏳️"
            
        # Convert each letter to regional indicator symbol
        return "".join(chr(ord(c.upper()) + 127397) for c in country_code)

async def setup(bot):
    await bot.add_cog(Currency(bot))
