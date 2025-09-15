# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# --- API CONFIGURATION ---
API_KEY = os.getenv("ASIATECH_API_KEY")
API_SECRET = os.getenv("ASIATECH_API_SECRET")
API_URL = "https://erp.asiatech.com.mx/api/resource/Employee Checkin"
LEAVE_API_URL = "https://erp.asiatech.com.mx/api/resource/Leave Application"
EMPLOYEE_API_URL = "https://erp.asiatech.com.mx/api/resource/Employee"

# --- VALIDATION ---
def get_api_headers():
    if not all([API_KEY, API_SECRET]):
        raise ValueError("Faltan credenciales (API_KEY, API_SECRET) en el archivo .env")
    return {"Authorization": f"token {API_KEY}:{API_SECRET}"}
