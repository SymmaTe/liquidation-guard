import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv("../.env")

url: str = os.getenv("SUPABASE_URL", "")
key: str = os.getenv("SUPABASE_ANON_KEY", "")
supabase: Client = create_client(url, key)
