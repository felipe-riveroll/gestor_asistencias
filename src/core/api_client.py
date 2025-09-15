# api_client.py
import json
import requests
import pytz
from datetime import datetime
from typing import List, Dict, Any
from config import API_URL, LEAVE_API_URL, EMPLOYEE_API_URL, get_api_headers

class APIClient:
    def __init__(self):
        self.checkin_url = API_URL
        self.leave_url = LEAVE_API_URL
        self.employee_url = EMPLOYEE_API_URL
        self.page_length = 100
        self.timeout = 30
    
    def fetch_checkins(self, start_date: str, end_date: str, device_filter: str) -> List[Dict[str, Any]]:
        headers = get_api_headers()
        filters = json.dumps([
            ["Employee Checkin", "time", "Between", [start_date, end_date]],
            ["Employee Checkin", "device_id", "like", device_filter],
        ])
        params = {"fields": json.dumps(["employee", "employee_name", "time"]), "filters": filters}
        all_records = []
        limit_start = 0
        while True:
            params["limit_start"], params["limit_page_length"] = limit_start, self.page_length
            try:
                response = requests.get(self.checkin_url, headers=headers, params=params, timeout=self.timeout)
                response.raise_for_status()
                data = response.json().get("data", [])
                if not data: break
                for record in data:
                    try:
                        time_utc = datetime.fromisoformat(record["time"].replace("Z", "+00:00"))
                        mexico_tz = pytz.timezone("America/Mexico_City")
                        record["time"] = time_utc.astimezone(mexico_tz).isoformat()
                    except (ValueError, TypeError):
                        record["time"] = None
                all_records.extend([r for r in data if r["time"] is not None])
                if len(data) < self.page_length: break
                limit_start += self.page_length
            except requests.exceptions.RequestException as e:
                # En una API real, aquí usaríamos un logger en lugar de print
                print(f"ERROR fetching checkins: {e}")
                raise  # Lanza la excepción para que el servidor la maneje
        return all_records

    def fetch_leave_applications(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        headers = get_api_headers()
        # AJUSTE: Este filtro es más preciso para capturar permisos que traslapan el período
        filters = json.dumps([
            ["status", "=", "Approved"],
            ["from_date", "<=", end_date],
            ["to_date", ">=", start_date],
        ])
        params = {
            "fields": json.dumps(["employee", "employee_name", "leave_type", "from_date", "to_date", "status", "half_day"]),
            "filters": filters,
        }
        all_records = []
        limit_start = 0
        while True:
            params["limit_start"], params["limit_page_length"] = limit_start, self.page_length
            try:
                response = requests.get(self.leave_url, headers=headers, params=params, timeout=self.timeout)
                response.raise_for_status()
                data = response.json().get("data", [])
                if not data: break
                all_records.extend(data)
                if len(data) < self.page_length: break
                limit_start += self.page_length
            except requests.exceptions.RequestException as e:
                print(f"ERROR fetching leaves: {e}")
                raise
        return all_records