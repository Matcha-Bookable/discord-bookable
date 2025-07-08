# literally the only time i think oop is useful
from requests import Response
from discord import WebhookMessage

class booking:
    """
    Represents a booking by user.
    """
    
    def __init__(self, discordid: int, bookingid: int, region: str, msg: WebhookMessage):
        self.discordID = discordid
        self.bookingID = bookingid
        self.region = region
        self.msg = msg

        self.status = "starting" # type: str
    
    def setStatus(self, status: str):
        self.status = status

    def getStatus(self):
        return self.status

    def getDiscordID(self):
        return self.discordID
    
    def getRegion(self):
        return self.region
    
    def getMessageObject(self):
        return self.msg
    