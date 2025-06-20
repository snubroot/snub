import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot configuration
PREFIX = os.getenv('PREFIX', '!')
TOKEN = os.getenv('DISCORD_TOKEN')
OWNER_IDS = list(map(int, os.getenv('OWNER_IDS', '').split(','))) if os.getenv('OWNER_IDS') else []

# Activity status
ACTIVITY_TYPE = os.getenv('ACTIVITY_TYPE', 'listening')  # playing, watching, listening
ACTIVITY_NAME = os.getenv('ACTIVITY_NAME', 'your commands')

# Error logging
ERROR_LOG_CHANNEL = int(os.getenv('ERROR_LOG_CHANNEL', 0))  # Channel ID for error logging

# OpenAI configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')  # OpenAI API key
