from aiohttp import web
import json
import asyncio
from discord.ext import commands
from datetime import datetime

#
#   CREDITS: https://gist.github.com/crrapi/c8465f9ce8b579a8ca3e78845309b832?permalink_comment_id=3431065#gistcomment-3431065
#   Not going to lie, i have no idea how to tackle with this until searching it up
#

class WebhookServer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.site = None

        self.booker = None
        self.sendServerDetails = None
        self.ServerIsEmpty = None
    
    def set_globals(self, booker_dict, send_server_details_func, server_is_empty_func):
        """Set global variables from main.py to avoid circular imports"""
        self.booker = booker_dict
        self.sendServerDetails = send_server_details_func
        self.ServerIsEmpty = server_is_empty_func

    async def webhook_handler(self, request):
        """Handle incoming POST requests to the webhook endpoint"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            print(f"\n[{timestamp}] Webhook POST Request Received:")
            print("=" * 50)
            print("Headers:")
            for header, value in request.headers.items():
                print(f"  {header}: {value}")
            
            # Webhook will receives JSON
            data = await request.json()
            print("\nJSON Data:")
            print(json.dumps(data, indent=2))
        
            print("=" * 50)

            await self.checkout_bookable(data)
            
            return web.json_response({"message": "Webhook received"})
            
        except Exception as e:
            print(f"Error processing webhook: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def health_handler(self, request):
        return web.json_response({"status": "healthy"})


    async def checkout_bookable(self, data):
        """
        Process the incoming webhook data.
        
        Args:
            data (dict): The JSON data received from the webhook.
        """
        bookingid = int(data.get("bookingID"))

        if data.get("status") == "started":
            serverDetails = data.get("details", {})
            details = {
                "address": serverDetails.get("address"),
                "port": serverDetails.get("port"),
                "stv_port": serverDetails.get("stv_port"),
                "sdr_ipv4": serverDetails.get("sdr_ipv4"),
                "sdr_port": serverDetails.get("sdr_port"),
                "sv_password": serverDetails.get("sv_password"),
                "instance": data.get("instance"),
                "region": self.booker[bookingid].getRegion()
            }

            await self.sendServerDetails(
                self.booker[bookingid].getDiscordID(),
                self.booker[bookingid].getMessageObject(),
                details
            )

            self.booker[bookingid].setStatus("started")

        else:
            await self.ServerIsEmpty(self.booker[bookingid].getDiscordID(), bookingid)

    async def webserver(self):
        """Start the aiohttp web server"""
        app = web.Application()
        app.router.add_post('/webhook', self.webhook_handler)
        app.router.add_get('/health', self.health_handler)
        
        runner = web.AppRunner(app)
        await runner.setup()
        self.site = web.TCPSite(runner, '0.0.0.0', 5000)
        await self.bot.wait_until_ready()
        print("Starting webhook server...")
        print("Health endpoint available at: http://0.0.0.0:5000/health")
        await self.site.start()

    def cog_unload(self):
        """Cleanup when cog is unloaded"""
        if self.site:
            asyncio.ensure_future(self.site.stop())

async def setup(bot):
    """Setup function for the cog"""
    webhook_cog = WebhookServer(bot)
    await bot.add_cog(webhook_cog)
    bot.loop.create_task(webhook_cog.webserver())
    return webhook_cog
