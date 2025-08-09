import requests
import os
from dotenv import load_dotenv
from typing import Tuple, Optional
from logging import Logger
from logging_config import setup_logger

load_dotenv()

MATCHA_API_URL = os.getenv("MATCHA_API_URL")
logger: Logger = setup_logger()

async def FetchBookableRegions(provider: str):
    """
    Fetches bookable regions from the specified provider.
    
    Args:
        provider (str): The provider to fetch regions from.
        
    Returns:
        list: A list of regions that have the specified provider available
    """
    try:
        response = requests.get(f"{MATCHA_API_URL}/v1/resources/region/list")
        response.raise_for_status()
        
        # Parse the JSON response
        regions_data = response.json()
        available_regions = []
        
        for region_code, region_info in regions_data.items():
            for provider_info in region_info.get("providers", []):
                if provider_info.get("provider") == provider:

                    available_regions.append({
                        "code": region_code,
                        "name": region_info.get("regionName")
                    })

                    break
        
        return available_regions
        
    except requests.exceptions.RequestException as e:
        logger.error("Error fetching regions: %s", e, exc_info=True)
        return []
    except Exception as e:
        logger.exception("Unexpected error while fetching regions")
        return []

async def FetchBookableAvailability(provider: str, region: str = None):
    """
    Fetches bookable availability for a specific provider and region.
    
    Args:
        provider (str): The provider to fetch availability from.
        region (str, optional): The specific region to filter by. Defaults to None.
        
    Returns:
        dict: A dictionary with region codes as keys and availability info as values.
              Each region contains: name, zone, quota, occupied, available
              
    Example:
        {
            "sgp": {
                "name": "Singapore",
                "zone": "asia-southeast1",
                "quota": 12,
                "occupied": 0,
                "available": 12
            },
            "tyo": {
                "name": "Tokyo", 
                "zone": "asia-northeast1",
                "quota": 4,
                "occupied": 0,
                "available": 4
            }
        }
    """
    try:
        response = requests.get(f"{MATCHA_API_URL}/v1/resources/region/list")
        response.raise_for_status()
        
        # Parse the JSON response
        regions_data = response.json()
        availability_data = {}
        
        for region_code, region_info in regions_data.items():
            # If a specific region is requested, skip others
            if region and region_code != region:
                continue
                
            # Look for the specified provider in this region
            for provider_info in region_info.get("providers", []):
                if provider_info.get("provider") == provider:
                    quota = provider_info.get("quota", 0)
                    occupied = provider_info.get("occupied", 0)
                    available = quota - occupied
                    
                    availability_data[region_code] = {
                        "name": region_info.get("regionName"),
                        "zone": provider_info.get("zone"),
                        "quota": quota,
                        "occupied": occupied,
                        "available": available
                    }
                    break  # Found the provider, no need to check other providers for this region
        
        return availability_data
        
    except requests.exceptions.RequestException as e:
        logger.error("Error fetching availability: %s", e, exc_info=True)
        return {}
    except Exception:
        logger.exception("Unexpected error while fetching availability")
        return {}
    
async def CreateMatchaBooking(discordid: str, region: str, provider: str = None) -> Tuple[int, Optional[requests.Response]]:
    """
    Creates a booking in the Matcha API.
    
    Args:
        discordid (str): Discord user ID (e.g. 108840458347610112)
        region (str): Region code (e.g. "hkg", "sgp", "del")
        provider (str, optional): Provider name (e.g. "google-cloud-platform")
        
    Returns:
        Tuple[int, Optional[requests.Response]]:
        
    Status Codes:
        200: OK - Booking created successfully
        301: DUPLICATED BOOKING - User already has a booking in this region
        302: FULL BOOKING IN THE REGION - No available slots in the region
        0: Error (API token not configured or request failed)
    """
    try:
        payload = {
            "discordid": discordid,
            "regionCode": region,
            "webhook": {
                "url": os.getenv("WEBHOOK_URL"),
                "bearer": os.getenv("WEBHOOK_BEARER")
            }
        }
        
        if provider:
            payload["provider"] = provider
        
        bearer_token = os.getenv("MATCHA_API_TOKEN")
        if not bearer_token:
            return 0, None
        
        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json"
        }
        
        # post
        response = requests.post(
            f"{MATCHA_API_URL}/v1/matcha/createbooking",
            json=payload,
            headers=headers
        )

        logger.info("Create booking response: status=%s body=%s", response.status_code, response.text)
        return response.status_code, response
        
    except requests.exceptions.RequestException as e:
        logger.error("Request error creating booking: %s", e, exc_info=True)
        return 0, None
    except Exception:
        logger.exception("Unexpected error creating booking")
        return 0, None

async def StopMatchaBooking(bookingid: int) -> int:
    """
    Terminates the booking in Matcha API.

    Args:
        bookingid (int): The bookingID of the bookable instance.

    Returns:
        requests.Response

    Status Codes:
        200: OK - Successful unbook
        404: BOOKING NOT FOUND - User does not have an on-going booking
        0: Error (API token or request not configured correctly)
    """

    try:
        bearer_token = os.getenv("MATCHA_API_TOKEN")
        if not bearer_token:
            return 0
        
        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json"
        }

        response = requests.post(
            f"{MATCHA_API_URL}/v1/matcha/endbooking?id={bookingid}",
            headers=headers
        )

        logger.info("End booking response: status=%s body=%s", response.status_code, response.text)
        return response.status_code

    except requests.exceptions.RequestException as e:
        logger.error("Request error stopping booking: %s", e, exc_info=True)
        return 0
    except Exception:
        logger.exception("Unexpected error stopping booking")
        return 0