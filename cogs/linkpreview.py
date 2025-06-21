import discord
from discord.ext import commands
import aiohttp
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse

class LinkPreview(commands.Cog):
    """URL metadata extractor that generates rich previews for links. This module allows users to preview webpage titles, images, and descriptions in an embed format."""
    
    def __init__(self, bot):
        self.bot = bot
        
    @commands.command(name="linkpreview")
    async def link_preview(self, ctx, url: str):
        """Generate a rich preview of a URL with title, image, and description
        
        Args:
            url: The URL to generate a preview for
        """
        # Check if the URL is valid
        if not self._is_valid_url(url):
            embed = discord.Embed(
                title="❌ Invalid URL",
                description="Please provide a valid URL starting with http:// or https://",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
            
        # Send a typing indicator while processing
        async with ctx.typing():
            # Fetch metadata from the URL
            metadata = await self._fetch_metadata(url)
            
            if not metadata:
                embed = discord.Embed(
                    title="❌ Error",
                    description="Could not fetch metadata from the provided URL",
                    color=discord.Color.red()
                )
                return await ctx.send(embed=embed)
                
            # Create the embed with the metadata
            embed = discord.Embed(
                title=metadata.get("title", "No Title"),
                description=metadata.get("description", "No description available"),
                url=url,
                color=discord.Color.blue()
            )
            
            # Add the image if available
            if metadata.get("image"):
                embed.set_image(url=metadata["image"])
                
            # Add the favicon if available
            if metadata.get("favicon"):
                embed.set_thumbnail(url=metadata["favicon"])
                
            # Add footer with domain information
            domain = urlparse(url).netloc
            embed.set_footer(text=f"Source: {domain}")
            
            # Add timestamp
            embed.timestamp = ctx.message.created_at
            
            await ctx.send(embed=embed)
            
    def _is_valid_url(self, url):
        """Check if a URL is valid"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc]) and result.scheme in ["http", "https"]
        except:
            return False
            
    async def _fetch_metadata(self, url):
        """Fetch metadata from a URL"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        return None
                        
                    html = await response.text()
                    return self._extract_metadata(html, url)
        except Exception as e:
            print(f"Error fetching URL {url}: {e}")
            return None
            
    def _extract_metadata(self, html, base_url):
        """Extract metadata from HTML content"""
        metadata = {
            "title": None,
            "description": None,
            "image": None,
            "favicon": None
        }
        
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            # Extract title
            metadata["title"] = self._get_title(soup)
            
            # Extract description
            metadata["description"] = self._get_description(soup)
            
            # Extract image
            metadata["image"] = self._get_image(soup, base_url)
            
            # Extract favicon
            metadata["favicon"] = self._get_favicon(soup, base_url)
            
            return metadata
        except Exception as e:
            print(f"Error extracting metadata: {e}")
            return metadata
            
    def _get_title(self, soup):
        """Extract title from HTML"""
        # Try Open Graph title first
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return og_title["content"]
            
        # Try Twitter card title
        twitter_title = soup.find("meta", attrs={"name": "twitter:title"})
        if twitter_title and twitter_title.get("content"):
            return twitter_title["content"]
            
        # Fall back to HTML title
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            return title_tag.string.strip()
            
        return "No Title"
        
    def _get_description(self, soup):
        """Extract description from HTML"""
        # Try Open Graph description first
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            return og_desc["content"]
            
        # Try Twitter card description
        twitter_desc = soup.find("meta", attrs={"name": "twitter:description"})
        if twitter_desc and twitter_desc.get("content"):
            return twitter_desc["content"]
            
        # Try meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            return meta_desc["content"]
            
        return "No description available"
        
    def _get_image(self, soup, base_url):
        """Extract image from HTML"""
        # Try Open Graph image first
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            return self._resolve_url(og_image["content"], base_url)
            
        # Try Twitter card image
        twitter_image = soup.find("meta", attrs={"name": "twitter:image"})
        if twitter_image and twitter_image.get("content"):
            return self._resolve_url(twitter_image["content"], base_url)
            
        return None
        
    def _get_favicon(self, soup, base_url):
        """Extract favicon from HTML"""
        # Look for favicon link
        favicon = soup.find("link", rel=lambda r: r and ("icon" in r.lower()))
        if favicon and favicon.get("href"):
            return self._resolve_url(favicon["href"], base_url)
            
        # Try default location
        parsed_url = urlparse(base_url)
        return f"{parsed_url.scheme}://{parsed_url.netloc}/favicon.ico"
        
    def _resolve_url(self, url, base_url):
        """Resolve relative URLs to absolute URLs"""
        if url.startswith("http://") or url.startswith("https://"):
            return url
            
        parsed_base = urlparse(base_url)
        base_domain = f"{parsed_base.scheme}://{parsed_base.netloc}"
        
        if url.startswith("//"):
            return f"{parsed_base.scheme}:{url}"
        elif url.startswith("/"):
            return f"{base_domain}{url}"
        else:
            path = "/".join(parsed_base.path.split("/")[:-1]) + "/"
            return f"{base_domain}{path}{url}"


async def setup(bot):
    await bot.add_cog(LinkPreview(bot))
