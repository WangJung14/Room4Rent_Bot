from supabase import create_client, Client

URL = "https://peyohdmmblfrftzzshvp.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBleW9oZG1tYmxmcmZ0enpzaHZwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODU1OTU2MzgsImV4cCI6MjEwMTE3MTYzOH0.MNfjPGljOi3tpy7vALchttQCOJc35YoIwWnPDIjw_bs"

print("Dang thu ket noi Supabase...")

try:
    supabase: Client = create_client(URL, KEY)
    response = supabase.table("phong_tro").select("*").limit(1).execute()
    
    print("=> KET NOI THANH CONG!")
    print("=> Du lieu lay duoc:", response.data)

except Exception as e:
    print("=> LOI KET NOI:")
    print(e)