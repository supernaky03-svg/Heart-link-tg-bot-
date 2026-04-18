from telethon.sync import TelegramClient
from telethon.sessions import StringSession

# Replace these before running locally.
API_ID = 1234567
API_HASH = "your_api_hash"

with TelegramClient(StringSession(), API_ID, API_HASH) as client:
    print("Copy this value into STORAGE_SESSION:")
    print(client.session.save())
