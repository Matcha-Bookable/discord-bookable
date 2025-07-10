# Discord Bookable Bot
- GCP Bookable - ![GCP Bookable](https://status.matcha-bookable.com/api/badge/12/status)
- AWS Bookable - ![AWS Bookable](https://status.matcha-bookable.com/api/badge/4/status)

A Simple Discord bot with webhook that integrates with the [Matcha-Bookable/matcha-api](https://github.com/Matcha-Bookable/matcha-api).

### Discord Permissions

Deployment will require the following permissions:
- Send Messages
- Use Slash Commands
- Embed Links
- Read Message History

## Commands

### `/status <region>`
Lists all bookable server locations and their availability.
- **Optional**: Specify a region to see specific availability
- Shows total capacity across all regions
- Displays available slots per region

### `/book <region>`
Books a server in the specified region.
- Will deliever the details into the users' private DMs

### `/unbook`
Unbooks the users' server.


## Setup

### Prerequisites
- Python 3.12
- Matcha API Access
- Docker

### Manual Setup

1. Clone the repository:
```bash
git clone https://github.com/Matcha-Bookable/discord-bookable
cd discord-bookable
```

2. Dependencies:
```bash
pip install -r requirements.txt
```

3. Change `.env.example` to `.env` and fill in the following variables:
```
BOT_TOKEN=          Bot token              
MATCHA_API_TOKEN=   Matcha API's apikey
MATCHA_API_URL=     FQDN of the Matcha API URL          
PROVIDER=           Provider identifier                   
PROVIDER_NAME=      Appearance name for bookable 
WEBHOOK_PORT=       Desired port for webhook         
WEBHOOK_URL=        FQDN of the webhook url to receive details               
WEBHOOK_BEARER=     if you wish to have bearer authenication      
GUILD=              Server ID                             
CHANNEL_ID=         Channel ID                            
MAX_BOOKABLE=       Maximum number of bookable servers    
```
4. Run the bot:
```bash
python main.py
```

### Docker Setup

Alternatively, use Docker:

```bash
docker build -t discord-bookable .
docker run -d -p 5000:5000/tcp --env-file .env discord-bookable
```

### Note
> please remember to change the `WEBHOOK_PORT` if you have multiple docker instances running in the same environment


## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
