"""
API client module for fetching data from external services.
Handles communication with Frappe API for check-ins and leave applications.
"""

import json
import requests
import pytz
from datetime import datetime, timedelta
from typing import List, Dict, Any

from .config import API_URL, LEAVE_API_URL, EMPLOYEE_API_URL, get_api_headers
from .utils import normalize_leave_type


class APIClient:
    """Client for handling API requests to Frappe/ERPNext."""
    
    def __init__(self):
        """Initialize API client with default configuration."""
        self.checkin_url = API_URL
        self.leave_url = LEAVE_API_URL
        self.employee_url = EMPLOYEE_API_URL
        self.page_length = 100
        self.timeout = 30
    
    def fetch_checkins(self, start_date: str, end_date: str, device_filter: str) -> List[Dict[str, Any]]:
        """
        Fetches all check-in records from the API for a date range.
        """
        print(f"📡 Obtaining check-ins from API for device '{device_filter}'...")
        print(f"   - Date range: {start_date} to {end_date}")
        
        try:
            headers = get_api_headers()
            print(f"✅ Headers obtenidos correctamente")
        except ValueError as e:
            print(f"❌ Error validating API credentials: {e}")
            return []
        
        # Mapeo mejorado de sucursales
        device_patterns = {
            "Todas": ["%"],
            "Villas": ["%villas%", "%Villas%", "%VILLAS%", "%VLLA%"],
            "31pte": ["%31pte%", "%31%pte%", "%31%", "%pte%", "%31PTE%"], 
            "Nave": ["%nave%", "%Nave%", "%NAVE%", "%NAV%"],
            "RioBlanco": ["%rioblanco%", "%RioBlanco%", "%Rio%Blanco%", "%Rio%", "%Blanco%"]
        }
        
        # Obtener todos los patrones para la sucursal
        sucursal_key = device_filter.replace("%", "")
        patterns = device_patterns.get(sucursal_key, [device_filter])
        
        all_records = []
        
        for pattern in patterns:
            print(f"🔍 Trying pattern: '{pattern}'")
            
            filters = json.dumps([
                ["Employee Checkin", "time", "Between", [start_date, end_date]],
                ["Employee Checkin", "device_id", "like", pattern],
            ])
            
            params = {
                "fields": json.dumps(["employee", "employee_name", "time", "device_id"]),
                "filters": filters,
            }

            limit_start = 0
            page = 1
            pattern_records = []

            while True:
                params["limit_start"] = limit_start
                params["limit_page_length"] = self.page_length
                
                try:
                    print(f"🌐 Page {page}: Making API request with pattern '{pattern}'")
                    
                    response = requests.get(
                        self.checkin_url, 
                        headers=headers, 
                        params=params,
                        timeout=self.timeout
                    )
                    
                    print(f"📥 Response status: {response.status_code}")
                    
                    if response.status_code != 200:
                        print(f"❌ API returned status {response.status_code}")
                        print(f"   - Response text: {response.text[:500]}...")
                        break
                    
                    try:
                        response_data = response.json()
                        data = response_data.get("data", [])
                    except json.JSONDecodeError as e:
                        print(f"❌ Error decoding JSON response: {e}")
                        print(f"   - Raw response: {response.text[:500]}...")
                        break
                    
                    print(f"📊 Records in page {page}: {len(data)}")
                    
                    if not data:
                        print("✅ No more data available for this pattern")
                        break

                    # Process and normalize timezone
                    for record in data:
                        try:
                            time_str = record["time"]
                            if time_str.endswith('Z'):
                                time_utc = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                            else:
                                time_utc = datetime.fromisoformat(time_str)
                                
                            mexico_tz = pytz.timezone("America/Mexico_City")
                            time_mexico = time_utc.astimezone(mexico_tz)
                            record["time"] = time_mexico.isoformat()
                        except Exception as e:
                            print(f"❌ Error processing time for record {record.get('employee')}: {e}")
                            continue

                    pattern_records.extend(data)
                    
                    if len(data) < self.page_length:
                        print("✅ Reached final page for this pattern")
                        break
                        
                    limit_start += self.page_length
                    page += 1
                    
                except requests.exceptions.Timeout:
                    print("⏰ Timeout connecting to API")
                    break
                except requests.exceptions.ConnectionError:
                    print("🔌 Connection error - API may be unreachable")
                    break
                except requests.exceptions.RequestException as e:
                    print(f"❌ Request error: {e}")
                    break
                except Exception as e:
                    print(f"❌ Unexpected error: {e}")
                    break

            print(f"✅ Pattern '{pattern}' retrieved {len(pattern_records)} records")
            all_records.extend(pattern_records)

        # Eliminar duplicados por si hay overlap entre patrones
        unique_records = []
        seen_ids = set()
        
        for record in all_records:
            record_id = f"{record.get('employee')}{record.get('time')}{record.get('device_id')}"
            if record_id not in seen_ids:
                seen_ids.add(record_id)
                unique_records.append(record)
        
        print(f"✅ Total unique records retrieved: {len(unique_records)}")
        
        # Debug: mostrar dispositivos únicos encontrados
        if unique_records:
            unique_devices = set(record.get("device_id", "N/A") for record in unique_records)
            print(f"📋 Unique devices found: {sorted(unique_devices)}")
        
        return unique_records

    def fetch_leave_applications(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Fetches all approved leave applications from the API for a date range.
        """
        print(f"📄 Obtaining approved leave applications from API for period {start_date} - {end_date}...")
        
        try:
            headers = get_api_headers()
        except ValueError as e:
            print(f"❌ Error validating API credentials: {e}")
            return []
        
        url = f'https://erp.asiatech.com.mx/api/resource/Leave Application?fields=["employee","employee_name","leave_type","from_date","to_date","status","half_day"]&filters=[["status","=","Approved"],["from_date",">=","{start_date}"],["to_date","<=","{end_date}"]]'

        all_leave_records = []
        limit_start = 0
        page = 1

        while True:
            params = {
                "limit_start": limit_start,
                "limit_page_length": self.page_length,
            }

            try:
                response = requests.get(
                    url, 
                    headers=headers, 
                    params=params, 
                    timeout=self.timeout
                )
                
                if response.status_code != 200:
                    print(f"❌ Leave API returned status {response.status_code}")
                    break
                
                response_data = response.json()
                data = response_data.get("data", [])
                
                print(f"📄 Leave records in page {page}: {len(data)}")
                
                if not data:
                    break

                all_leave_records.extend(data)

                if len(data) < self.page_length:
                    break

                limit_start += self.page_length
                page += 1

            except requests.exceptions.Timeout:
                print("⏰ Timeout connecting to Leave API")
                break
            except requests.exceptions.RequestException as e:
                print(f"❌ Error obtaining leave applications: {e}")
                break

        print(f"✅ Retrieved {len(all_leave_records)} approved leave applications.")
        return all_leave_records

    def fetch_employee_joining_dates(self) -> List[Dict[str, Any]]:
        """
        Fetches all employee records from the API to get their joining dates.
        """
        print("👥 Obtaining all employee joining dates from API...")

        try:
            headers = get_api_headers()
        except ValueError as e:
            print(f"❌ Error validating API credentials: {e}")
            return []

        params = {
            "fields": json.dumps(["employee", "date_of_joining"]),
        }

        all_records = []
        limit_start = 0
        page = 1

        while True:
            params["limit_start"] = limit_start
            params["limit_page_length"] = self.page_length

            try:
                response = requests.get(
                    self.employee_url,
                    headers=headers,
                    params=params,
                    timeout=self.timeout
                )
                
                if response.status_code != 200:
                    print(f"❌ Employee API returned status {response.status_code}")
                    break
                
                response_data = response.json()
                data = response_data.get("data", [])
                
                print(f"👥 Employee records in page {page}: {len(data)}")
                
                if not data:
                    break

                all_records.extend(data)

                if len(data) < self.page_length:
                    break

                limit_start += self.page_length
                page += 1

            except requests.exceptions.RequestException as e:
                print(f"❌ Error calling Employee API: {e}")
                break

        print(f"✅ Retrieved {len(all_records)} employee records.")
        return all_records


def procesar_permisos_empleados(leave_data: List[Dict[str, Any]]) -> Dict[str, Dict]:
    """
    Processes leave data and creates a dictionary organized by employee and date.
    """
    if not leave_data:
        return {}

    print("🔄 Processing leave applications by employee and date...")

    permisos_por_empleado = {}
    total_dias_permiso = 0
    permisos_medio_dia = 0

    for permiso in leave_data:
        employee_code = permiso["employee"]
        from_date = datetime.strptime(permiso["from_date"], "%Y-%m-%d").date()
        to_date = datetime.strptime(permiso["to_date"], "%Y-%m-%d").date()
        is_half_day = permiso.get("half_day") == 1

        if employee_code not in permisos_por_empleado:
            permisos_por_empleado[employee_code] = {}

        if is_half_day:
            leave_type_normalized = normalize_leave_type(permiso["leave_type"])

            permisos_por_empleado[employee_code][from_date] = {
                "leave_type": permiso["leave_type"],
                "leave_type_normalized": leave_type_normalized,
                "employee_name": permiso["employee_name"],
                "from_date": from_date,
                "to_date": to_date,
                "status": permiso["status"],
                "is_half_day": True,
                "dias_permiso": 0.5,
            }
            total_dias_permiso += 0.5
            permisos_medio_dia += 1
        else:
            current_date = from_date
            while current_date <= to_date:
                leave_type_normalized = normalize_leave_type(permiso["leave_type"])

                permisos_por_empleado[employee_code][current_date] = {
                    "leave_type": permiso["leave_type"],
                    "leave_type_normalized": leave_type_normalized,
                    "employee_name": permiso["employee_name"],
                    "from_date": from_date,
                    "to_date": to_date,
                    "status": permiso["status"],
                    "is_half_day": False,
                    "dias_permiso": 1.0,
                }
                current_date += timedelta(days=1)
                total_dias_permiso += 1.0

    print(f"✅ Processed leave applications for {len(permisos_por_empleado)} employees, "
          f"{total_dias_permiso:.1f} total leave days ({permisos_medio_dia} half-day leaves).")

    return permisos_por_empleado