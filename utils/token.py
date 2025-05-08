import asyncio
import logging

async def refresh_token_periodically(auth_instance, api_instance):
    """Periodically refresh the Locket API token."""
    while True:
        try:
            logging.info("Attempting to refresh Locket API token...")
            new_token = await asyncio.to_thread(auth_instance.get_token)
            api_instance.token = new_token
            api_instance.headers['Authorization'] = f'Bearer {new_token}'
            logging.info("Successfully refreshed Locket API token.")
        except Exception as e:
            logging.error(f"Failed to refresh token: {e}")
        await asyncio.sleep(3300)