import discord
from discord.ext import commands
from discord import app_commands, WebhookMessage
from discord import Embed

from datetime import datetime
from dotenv import load_dotenv
import os
import asyncio

import api
from details import booking

load_dotenv()

intents = discord.Intents.all()
client = commands.Bot(command_prefix='/', intents=intents)

PROVIDER = os.getenv("PROVIDER")
PROVIDER_NAME = os.getenv("PROVIDER_NAME")
GUILD = discord.Object(int(os.getenv("GUILD")))
CHANNEL = int(os.getenv("CHANNEL_ID"))
MAX_BOOKABLE = int(os.getenv("MAX_BOOKABLE"))

# Global variables
g_regions = {}
regions = []
booker = {}
BookingAmount = 0
choices = []


# For choices init
async def GetBookableChoices():
    global choices
    for region in regions:
        choices.append(app_commands.Choice(name=region["name"], value=region["code"]))

        # save into g_regions variable
        g_regions[region["code"]] = {
            "fullname": region["name"]
        }

        if len(choices) >= 25:  # Discord limit
            break
    return

# --------------------------------------------------- DISCORD EVENTS / COMMANDS --------------------------------------------------- #

#
#   On ready
#
@client.event
async def on_ready():
    print(f'Logged on as {client.user}!')

    await client.tree.sync(guild=GUILD) # Sync commands

#
#   SLASHCOMMAND: /status <region:OPT>
#
@client.tree.command(name="status", description="List all of the bookable locations.", guild=GUILD)
@app_commands.choices(region=choices)
async def status(interaction: discord.Interaction, region: str = None):
    await interaction.response.defer() # might just remove this and have a placeholder

    bookings = await api.FetchBookableAvailability(PROVIDER)

    # Setup base embed
    embed = Embed(
            timestamp   = datetime.now(),
            color       = 0x4c7c2c,
            title       = f"**Status - {PROVIDER_NAME}**",
            description = f"Total Capacity: `{BookingAmount}/{MAX_BOOKABLE}` booked"
        )
    embed.set_footer(text="Regards")

    try:
        # Retrieve the quotas and occupancy of each region
        if region:
            # Show specific region if requested
            if region in bookings:
                region_data = bookings[region]
                total = region_data["quota"]
                available = region_data["available"]

                embed.add_field(
                    name=f"{region_data['name']}",
                    value=f"`{available}/{total}` available",
                    inline=True
                )

        else:
            # Show all regions
            for _, region_data in bookings.items():
                # Regions with zero quota should not appear in the embed
                if region_data["quota"] == 0:
                    continue
                
                total = region_data["quota"]
                available = region_data["available"]
                
                embed.add_field(
                    name=f"{region_data['name']}",
                    value=f"`{available}/{total}` available",
                    inline=True
                )
        
        await interaction.followup.send(content=f"<@{interaction.user.id}>", embed=embed)
        
    except Exception as e:
        error_embed = Embed(
            title="Error",
            description=f"An error has occured: {str(e)}",
            color=0x7c2c4c
        )

        await interaction.followup.send(content=f"<@{interaction.user.id}>", embed=error_embed)

#
#   SLASHCOMMAND: /book <region>
#
@client.tree.command(name="book", description="Book a server in a location", guild=GUILD)
@app_commands.choices(region=choices)
async def book(interaction: discord.Interaction, region: str):
    await interaction.response.defer()

    user = interaction.user

    # ACK
    embed = Embed(
            timestamp   = datetime.now(),
            color       = 0x2c4c7c,
            title       = "**Bookings**",
            description = "Your request is being processed.\nThis message will be updated accordingly later."
        )
        
    embed.set_footer(text="Regards")
    msg = await interaction.followup.send(content=f"<@{interaction.user.id}>", embed=embed, wait=True)

    tempID = user.id # using discord snowflake as temp, unique and literally impossible to reach

    global booker, BookingAmount
    if not isinstance(booker, dict):
        booker = {}

    if tempID in booker: # If the tempID exists: the request is still being processed
        embed = Embed(
            timestamp   = datetime.now(),
            color       = 0x7c2c4c,
            title       = "**Bookings**",
            description = "You have a request being processed.\nPlease wait till it has finished."
        )
        embed.set_footer(text="Regards")
        await msg.edit(content=f"<@{interaction.user.id}>", embed=embed)
        return

    booker[tempID] = booking(None, None, None, None)  # Temporary booking object

    bookingid = None
    for b_id, b_obj in booker.items():
        if b_obj.getDiscordID() == user.id:
            embed = Embed(
                timestamp   = datetime.now(),
                color       = 0x7c2c4c,
                title       = "**Bookings**",
                description = "You have already booked a server.\nPlease unbook the server before booking a new one."
            )
            embed.set_footer(text="Regards")
            await msg.edit(content=f"<@{interaction.user.id}>", embed=embed)
            del booker[tempID]
            return
    try:
        # Send an invalid message to test if the user has DM disabled
        await user.send()

    except discord.Forbidden:
        print(f"BOOKING FAILED: User {user.name} has DMs disabled.")

        embed = Embed(
                timestamp   = datetime.now(),
                color       = 0x7c2c4c,
                title       = "**Bookings**",
                description = "Please enable Direct Messages before booking for a server."
            )
        
        embed.set_footer(text="Apologies")
        await msg.edit(content=f"<@{interaction.user.id}>", embed=embed)
        del booker[tempID]
        return
    
    except discord.HTTPException:
        # Has DM enabled
        pass

    # Check if it exceeds the MAX_BOOKABLE
    if BookingAmount >= MAX_BOOKABLE:
        embed = Embed(
            timestamp   = datetime.now(),
            color       = 0x7c2c4c,
            title       = "**Bookings**",
            description = "The total server capacity has been reached.\nPlease try again later."
        )
        embed.set_footer(text="Apologies")
        await msg.edit(content=f"<@{interaction.user.id}>", embed=embed)
        del booker[tempID]
        return

    # Create the request in the background
    status, data = await api.CreateMatchaBooking(str(user.id), region, PROVIDER) # Attempt to book

    del booker[tempID]

    match status:
        case 200:
            # Successful
            embed = Embed(
                timestamp   = datetime.now(),
                color       = 0x2c4c7c,
                title       = "**Bookings**",
                description = "Your server is being booked, this may take some time.\nServer details will be sent to you via private message."
            )
            embed.set_footer(text="Have fun")
            await msg.edit(content=f"<@{interaction.user.id}>", embed=embed)

        case 301:
            # Duplicated (Tried booking from 2 different bots with the same Backend)
            embed = Embed(
                timestamp   = datetime.now(),
                color       = 0x7c2c4c,
                title       = "**Bookings**",
                description = "You have a separate booking currently.\nPlease unbook from the other bookable before attempting."
            )
            embed.set_footer(text="Regards")
            await msg.edit(content=f"<@{interaction.user.id}>", embed=embed)
            return
        
        case 302:
            # The region is full
            embed = Embed(
                timestamp   = datetime.now(),
                color       = 0x7c2c4c,
                title       = "**Bookings**",
                description = "This region has no available servers.\nPlease try again later."
            )
            embed.set_footer(text="Apologies")
            await msg.edit(content=f"<@{interaction.user.id}>", embed=embed)
            return
        
        case 0:
            # API configuration error or connection failure
            embed = Embed(
                timestamp   = datetime.now(),
                color       = 0x7c2c4c,
                title       = "**Bookings**",
                description = "Service temporarily unavailable.\nThis could be due to a configuration issue or network problem.\nPlease try again later or contact the admins."
            )
            embed.set_footer(text="Apologies")
            await msg.edit(content=f"<@{interaction.user.id}>", embed=embed)
            return
        
        case _:
            # Unknown issue, most likely backend status 500
            embed = Embed(
                timestamp   = datetime.now(),
                color       = 0x7c2c4c,
                title       = "**Bookings**",
                description = "An Interal Server Errors has occured.\nPlease try again later."
            )
            embed.set_footer(text=f"Status Code: {status}")
            await msg.edit(content=f"<@{interaction.user.id}>", embed=embed)
            return

    # Store the datas
    response_data = data.json()
    bookingid = response_data.get("booking", {}).get("bookingID")

    if not isinstance(booker, dict):
        booker = {}
    booker[bookingid] = booking(user.id, bookingid, region, msg)
    BookingAmount += 1

    #
    #   DISCORD INTERACTION WEBHOOK TOKEN IS ONLY VALID FOR 15 MINUTES!!!!!
    #

    # timeout for webhook
    timeout = False
    start_time = datetime.now()
    while True:
        if booker[bookingid].getStatus() == "started": # webhook went through
            break
        elif booker[bookingid].getStatus() == "starting" and timeout:
            embed = Embed(
                timestamp   = datetime.now(),
                color       = 0x7c2c4c,
                title       = "**Bookings**",
                description = "The request has timed out.\nPlease try again later."
            )
            embed.set_footer(text=f"Apologies")
            await msg.edit(content=f"<@{interaction.user.id}>", embed=embed)
            BookingAmount -= 1
            del booker[bookingid]
            break

        elif timeout: # future proof heh
            break

        # Wait 10 seconds before checking
        await asyncio.sleep(10)
        
        if (datetime.now() - start_time).total_seconds() > 600: # 10 minutes is more than sufficient
            timeout = True

#
#   SLASHCOMMAND: /unbook
#
@client.tree.command(name="unbook", description="Unbook your server", guild=GUILD)
async def unbook(interaction: discord.Interaction):
    await interaction.response.defer()

    user = interaction.user

    embed = Embed(
        timestamp   = datetime.now(),
        color       = 0x2c4c7c,
        title       = "**Bookings**",
        description = "Your unbook request is being processed.\nThis message will be updated accordingly later."
    )
    embed.set_footer(text="Regards")
    msg = await interaction.followup.send(content=f"<@{interaction.user.id}>", embed=embed, wait=True)

    global booker, BookingAmount
    if not isinstance(booker, dict):
        booker = {}

    bookingid = None
    for b_id, b_obj in booker.items():
        if b_obj.getDiscordID() == user.id:
            bookingid = b_id
            break

    if bookingid is None:
        embed = Embed(
            timestamp   = datetime.now(),
            color       = 0x7c2c4c,
            title       = "**Bookings**",
            description = "You haven't booked a server yet.\nPlease book a server first."
        )
        embed.set_footer(text="Regards")
        await msg.edit(content=f"<@{interaction.user.id}>", embed=embed)
        return

    if booker[bookingid].getStatus() == "unbooking": # an unbook request is being processed
        embed = Embed(
            timestamp   = datetime.now(),
            color       = 0x7c2c4c,
            title       = "**Bookings**",
            description = "Your server is being closed right now.\nPlease wait for it to finish."
        )
        embed.set_footer(text="Regards")
        await msg.edit(content=f"<@{interaction.user.id}>", embed=embed)
        return
    
    elif booker[bookingid].getStatus() == "starting": # the server is starting
        embed = Embed(
            timestamp   = datetime.now(),
            color       = 0x7c2c4c,
            title       = "**Bookings**",
            description = "You may close the server after it has started.\nPlease wait for it to finish."
        )
        embed.set_footer(text="Regards")
        await msg.edit(content=f"<@{interaction.user.id}>", embed=embed)
        return

    booker[bookingid].setStatus("unbooking")

    status = await api.StopMatchaBooking(bookingid)

    if status == 200:
        embed = Embed(
            timestamp   = datetime.now(),
            color       = 0x4c7c2c,
            title       = "**Bookings**",
            description = "Your server has been closed.\nThank you for using our service."
        )
        embed.set_footer(text="Have a nice day")
        await msg.edit(content=f"<@{interaction.user.id}>", embed=embed)

    else:
        embed = Embed(
            timestamp   = datetime.now(),
            color       = 0x7c2c4c,
            title       = "**Bookings**",
            description = f"An Internal Server Error has occured.\nPlease try again later or contact the admins."
        )

        embed.set_footer(text=f"Status Code: {status}")
        await msg.edit(content=f"<@{interaction.user.id}>", embed=embed)

    if bookingid in booker: # garbage collect
        del booker[bookingid]
        BookingAmount -= 1

#
#   FUNCTION: Manually triggered to deliever the server details
#
async def sendServerDetails(userid: int, msg: WebhookMessage, details: dict):
    connectString = f"connect {details["address"]}:{details["port"]}; password \"{details["sv_password"]}\""
    sdrString = f"connect {details["sdr_ipv4"]}:{details["sdr_port"]}; password \"{details["sv_password"]}\""
    stvString = f"connect {details["address"]}:{details["stv_port"]}"
    instanceName = details["instance"]
    region = f"{g_regions[details["region"]]["fullname"]} ({details["region"].upper()})"
    reminder = "WARNING: THIS BOOKABLE IS CURRENTLY BEING EXPERIMENTED, WE ARE NOT RESPONSIBLE FOR ANY INCIDENTS OCCURED FROM GAMES IN THIS BOOKABLE.\n\nUse `!votemenu` to change configs and maps.\nUse `!sdr` to receive SDR connect string in-game.\nServer will close if there are less than 2 players for 10 minutes."

    # Send DM embed to user
    embed_dm = Embed(
        timestamp   = datetime.now(),
        color       = 0x4c7c2c,
        title       = "**Bookings**",
        description = "Your server is ready!"
    )
    embed_dm.set_footer(text="Have fun")

    embed_dm.add_field(
            name="Connect String",
            value=f"```{connectString}```",
            inline=False
        )
    
    embed_dm.add_field(
            name="SDR Connect String",
            value=f"```{sdrString}```",
            inline=False
        )
    
    embed_dm.add_field(
            name="SourceTV Details",
            value=f"```{stvString}```",
            inline=False
        )
    
    embed_dm.add_field(
            name="Server",
            value=f"`{instanceName}`",
            inline=True
        )
    
    embed_dm.add_field(
            name="Region",
            value=f"`{region}`",
            inline=True
        )
    
    embed_dm.add_field(
            name="Reminder",
            value=f"{reminder}",
            inline=False
        )
    
    
    user = client.get_user(userid)
    if user is None:
        user = await client.fetch_user(userid) # backup
    
    await user.send(embed=embed_dm)

    # Confirmation embed
    embed = Embed(
                timestamp   = datetime.now(),
                color       = 0x4c7c2c,
                title       = "**Bookings**",
                description = "Server details have been sent to you via private message."
            )
    embed.set_footer(text=f"{g_regions[details["region"]]["fullname"]} ({details["region"].upper()})")
    await msg.edit(content=f"<@{userid}>", embed=embed)

#
#   FUNCTION: Notify the user that the server was empty and unbooked
#
async def ServerIsEmpty(userid: int, bookingid: int):
    channel = await client.fetch_channel(CHANNEL)

    embed = Embed(
                timestamp   = datetime.now(),
                color       = 0x2c7c7c,
                title       = "**Empty**",
                description = "The server has been closed due to inactivity.\nThank you for using our service."
            )
    embed.set_footer(text="Have a nice day")
    await channel.send(content=f"<@{userid}>", embed=embed)

    if bookingid in booker:
        del booker[bookingid] # garbage collect
        global BookingAmount
        BookingAmount -= 1


# ------------------------------- STARTER ------------------------------- #

webhook_cog = None

async def setup_webhook():
    """Setup the webhook cog"""
    global webhook_cog
    from webhook import setup
    webhook_cog = await setup(client)
    
    # Set the global variables in webhook module
    webhook_cog.set_globals(booker, sendServerDetails, ServerIsEmpty)

async def run_bot():
    """Run the Discord bot"""
    print("Starting Discord bot...")

    # Fetch available regions for choices
    global regions
    regions = await api.FetchBookableRegions(PROVIDER)
    await GetBookableChoices()

    # Setup webhook cog before starting the bot
    async with client:
        await setup_webhook()
        await client.start(os.getenv("BOT_TOKEN"))

def main():
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\nShutting down...")

if __name__ == "__main__":
    main()