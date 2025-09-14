from aiohttp import web
import json
import asyncio
from discord.ext import commands
from datetime import datetime
import os
from dotenv import load_dotenv
from logging_config import setup_logger
from logging import Logger

load_dotenv()
logger: Logger = setup_logger()

WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT"))

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
            
            logger.info("Webhook POST received at %s", timestamp)
            logger.debug("Webhook headers: %s", dict(request.headers))
            
            # Webhook will receives JSON
            data = await request.json()
            logger.debug("Webhook JSON: %s", json.dumps(data, indent=2))

            await self.checkout_bookable(data)
            
            return web.json_response({"message": "Webhook received"})
            
        except Exception:
            logger.exception("Error processing webhook request")
            return web.json_response({"error": "Internal server error"}, status=500)

    async def health_handler(self, request):
        return web.json_response({"status": "healthy"})


    async def checkout_bookable(self, data):
        """
        Process the incoming webhook data.
        
        Args:
            data (dict): The JSON data received from the webhook.
        """
        bookingid = int(data.get("bookingID"))

        # Check if booking exists in our records and isn't one that has already been delivered
        if bookingid not in self.booker or self.booker[bookingid].getStatus() == "started":
            logger.warning("Received webhook for unknown/duplicated booking ID: %s", bookingid)
            return

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
                "region": self.booker[bookingid].getRegion(),
                "bookingid": bookingid
            }

            await self.sendServerDetails(
                self.booker[bookingid].getDiscordID(),
                self.booker[bookingid].getMessageObject(),
                details
            )

            logger.info("Booking %s started for user %s", bookingid, self.booker[bookingid].getDiscordID())

            self.booker[bookingid].setStatus("started")

        else:
            # Check if booking still exists before processing server empty notification
            if bookingid in self.booker:
                await self.ServerIsEmpty(self.booker[bookingid].getDiscordID(), bookingid)
            else:
                logger.warning("Received server empty webhook for unknown/expired booking ID: %s", bookingid)

    async def webserver(self):
        """Start the aiohttp web server"""
        app = web.Application()
        app.router.add_post('/webhook', self.webhook_handler)
        app.router.add_get('/health', self.health_handler)
        
        runner = web.AppRunner(app)
        await runner.setup()
        self.site = web.TCPSite(runner, '0.0.0.0', WEBHOOK_PORT)
        await self.bot.wait_until_ready()
        logger.info("Starting webhook server on port %s", WEBHOOK_PORT)
        logger.info("Health endpoint available at: http://localhost:%s/health", WEBHOOK_PORT)
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
