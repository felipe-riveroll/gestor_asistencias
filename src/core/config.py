"""
Configuration module for the attendance reporting system.
Contains all constants, settings, and configuration variables.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ==============================================================================
# API CONFIGURATION
# ==============================================================================

# Frappe API credentials
API_KEY = os.getenv("ASIATECH_API_KEY")
API_SECRET = os.getenv("ASIATECH_API_SECRET")
API_URL = "https://erp.asiatech.com.mx/api/resource/Employee Checkin"
LEAVE_API_URL = "https://erp.asiatech.com.mx/api/resource/Leave Application"
EMPLOYEE_API_URL = "https://erp.asiatech.com.mx/api/resource/Employee"

# ==============================================================================
# VALIDATION FUNCTIONS
# ==============================================================================

def validate_api_credentials():
    """Validate that required API credentials are present."""
    if not all([API_KEY, API_SECRET]):
        raise ValueError(
            "Missing API credentials (ASIATECH_API_KEY, ASIATECH_API_SECRET) in .env file"
        )
    return True

def get_api_headers():
    """Get API headers with authentication."""
    validate_api_credentials()
    return {
        "Authorization": f"token {API_KEY}:{API_SECRET}",
        "Content-Type": "application/json"
    }

# ==============================================================================
# LEAVE POLICY CONFIGURATION
# ==============================================================================

# Leave policy by type - defines how expected hours are handled
POLITICA_PERMISOS = {
    "permiso sin goce de sueldo": "no_ajustar",
    "permiso sin goce": "no_ajustar", 
    "sin goce de sueldo": "no_ajustar",
    "sin goce": "no_ajustar",
}

# ==============================================================================
# BUSINESS RULES CONFIGURATION
# ==============================================================================

# Tardiness forgiveness rule configuration
PERDONAR_TAMBIEN_FALTA_INJUSTIFICADA = False

# Early departure detection configuration
TOLERANCIA_SALIDA_ANTICIPADA_MINUTOS = 15

# Tardiness and absence thresholds (in minutes)
TOLERANCIA_RETARDO_MINUTOS = 15
UMBRAL_FALTA_INJUSTIFICADA_MINUTOS = 60

# Midnight crossing shift grace period (in minutes)
GRACE_MINUTES = 59

# ==============================================================================
# REPORT CONFIGURATION
# ==============================================================================

# Output file names
OUTPUT_DETAILED_REPORT = "reporte_asistencia_analizado.csv"
OUTPUT_SUMMARY_REPORT = "resumen_periodo.csv" 
OUTPUT_HTML_DASHBOARD = "dashboard_asistencia.html"

# ==============================================================================
# SPANISH DAY NAMES MAPPING
# ==============================================================================

DIAS_ESPANOL = {
    "Monday": "Lunes",
    "Tuesday": "Martes", 
    "Wednesday": "Miércoles",
    "Thursday": "Jueves",
    "Friday": "Viernes",
    "Saturday": "Sábado",
    "Sunday": "Domingo",
}