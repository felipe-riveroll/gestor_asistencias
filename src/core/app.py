# app.py
from flask import Flask, jsonify, request
from datetime import datetime
from api_client import APIClient  # Importa tu clase

# Se crea la aplicación de la API
app = Flask(__name__)

# Se define el endpoint para las checadas
@app.route('/api/checkins', methods=['GET'])
def get_checkins_endpoint():
    print(f"[{datetime.now()}] Petición recibida en /api/checkins")
    
    # Obtiene parámetros de la URL, con valores por defecto
    today_str = datetime.now().strftime('%Y-%m-%d')
    start_date = request.args.get('start_date', default=today_str)
    end_date = request.args.get('end_date', default=today_str)
    sucursal = request.args.get('sucursal', default='%')
    
    try:
        # Crea una instancia de tu cliente
        client = APIClient()
        # Llama al método para obtener las checadas
        checkins = client.fetch_checkins(
            start_date=start_date, 
            end_date=end_date, 
            device_filter=f"%{sucursal}%"
        )
        return jsonify({"records_found": len(checkins), "data": checkins})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint para obtener permisos
@app.route('/api/leaves', methods=['GET'])
def get_leaves_endpoint():
    print(f"[{datetime.now()}] Petición recibida en /api/leaves")
    today_str = datetime.now().strftime('%Y-%m-%d')
    start_date = request.args.get('start_date', default=today_str)
    end_date = request.args.get('end_date', default=today_str)

    try:
        client = APIClient()
        leaves = client.fetch_leave_applications(start_date=start_date, end_date=end_date)
        return jsonify({"records_found": len(leaves), "data": leaves})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Inicia el servidor
if __name__ == '__main__':
    app.run(debug=True, port=5000)