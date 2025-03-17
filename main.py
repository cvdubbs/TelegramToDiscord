import os
import asyncio
from telethon import TelegramClient, events
from discord_webhook import DiscordWebhook, DiscordEmbed
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Telegram API credentials
API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
TELEGRAM_PHONE = os.getenv("TELEGRAM_PHONE")
TELEGRAM_CHANNEL = os.getenv("TELEGRAM_CHANNEL")  # Username or ID of the channel

# Discord webhook URL
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# Create a .env file with the following variables:
"""
TELEGRAM_API_ID=your_telegram_api_id
TELEGRAM_API_HASH=your_telegram_api_hash
TELEGRAM_PHONE=your_phone_number
TELEGRAM_CHANNEL=channel_username_or_id
DISCORD_WEBHOOK_URL=your_discord_webhook_url
"""

async def main():
    # Initialize the Telegram client
    client = TelegramClient('session_name', API_ID, API_HASH)
    
    # Connect to the client first
    await client.start()
    
    # Resolve the channel entity
    try:
        # Try to get the channel entity - this works with channel usernames like '@channelname'
        channel = None
        if TELEGRAM_CHANNEL:
            # If it looks like a channel username but doesn't have @, add it
            if TELEGRAM_CHANNEL.isalnum() and not TELEGRAM_CHANNEL.startswith('@'):
                try:
                    channel = await client.get_entity(f'@{TELEGRAM_CHANNEL}')
                except ValueError:
                    pass
                    
            # If that didn't work, try as is (might be a username with @ or a channel ID)
            if not channel:
                try:
                    channel = await client.get_entity(TELEGRAM_CHANNEL)
                except ValueError:
                    # Try as integer ID
                    try:
                        channel_id = int(TELEGRAM_CHANNEL)
                        channel = await client.get_entity(channel_id)
                    except (ValueError, TypeError):
                        logger.error(f"Could not resolve channel: {TELEGRAM_CHANNEL}")
                        return
        
        if channel:
            logger.info(f"Successfully connected to channel: {getattr(channel, 'title', TELEGRAM_CHANNEL)}")
        else:
            logger.error("Channel not found. Please check the TELEGRAM_CHANNEL value.")
            return
            
    except Exception as e:
        logger.error(f"Error connecting to the channel: {e}")
        return
    
    @client.on(events.NewMessage(chats=channel))
    async def handler(event):
        """Handle new messages from the Telegram channel"""
        message = event.message
        
        try:
            # Create a Discord webhook
            webhook = DiscordWebhook(url=DISCORD_WEBHOOK_URL)
            
            # Format the message content
            content = message.message
            
            # Check if the message has media
            if message.media:
                # Handle different types of media
                if hasattr(message.media, 'photo'):
                    # Download the photo
                    path = await client.download_media(message.media)
                    with open(path, 'rb') as f:
                        webhook.add_file(file=f.read(), filename='photo.jpg')
                    # Clean up the downloaded file
                    os.remove(path)
                    
                # Add more media types handling here if needed
                # e.g., videos, documents, etc.
            
            # Create embed for better formatting
            embed = DiscordEmbed(
                title="Telegram Message",
                description=content,
                color="03b2f8"
            )
            
            # Add author information if available
            if message.sender:
                sender = await message.get_sender()
                # Check if sender is a channel or a user
                if hasattr(sender, 'title'):  # It's a channel
                    sender_name = sender.title
                elif hasattr(sender, 'first_name'):  # It's a user
                    sender_name = sender.first_name
                    if hasattr(sender, 'last_name') and sender.last_name:
                        sender_name += f" {sender.last_name}"
                else:
                    sender_name = "Unknown"
                embed.set_author(name=sender_name)
            
            # Add timestamp
            embed.set_timestamp(message.date.timestamp())
            
            # Add the embed to the webhook
            webhook.add_embed(embed)
            
            # Send the message to Discord
            response = webhook.execute()
            
            if response.status_code == 200:
                logger.info(f"Message forwarded successfully to Discord")
            else:
                logger.error(f"Failed to forward message: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error forwarding message: {e}")
    
    # Client is already started above
    
    # Run the client until disconnected
    logger.info("Bot is running. Press Ctrl+C to stop.")
    await client.run_until_disconnected()

if __name__ == "__main__":
    # Run the main function
    asyncio.run(main())