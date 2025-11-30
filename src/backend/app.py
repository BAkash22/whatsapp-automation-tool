import os
from flask import Flask, jsonify, request
from whatsapp_service import WhatsAppService

app = Flask(__name__)

# Get the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")

# Create uploads directory if it doesn't exist
os.makedirs(UPLOADS_DIR, exist_ok=True)

ws = WhatsAppService()

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "WhatsApp Automation Backend Running!"})

@app.route("/start", methods=["GET"])
def start_session():
    ws.start_whatsapp()
    return {"message": "WhatsApp session started! Scan the QR on screen."}

@app.route("/send", methods=["POST"])
def send_message():
    try:
        # Try to get JSON data first, fallback to form data
        if request.is_json:
            data = request.get_json()
            number = data.get("number") if data else None
            message = data.get("message") if data else None
        else:
            # Try form data
            number = request.form.get("number")
            message = request.form.get("message")
        
        # Log what we received for debugging
        print(f"Received request - Number: {number}, Message: {message}")
        
        if not number or not message:
            error_msg = f"Number and message are required. Received - Number: {number}, Message: {message}"
            print(f"Validation error: {error_msg}")
            return jsonify({"status": "error", "message": error_msg}), 400

        result = ws.send_message(number, message)
        if result:
            return jsonify({"status": "sent"})
        else:
            return jsonify({"status": "error", "message": "Failed to send message. Make sure WhatsApp session is started."}), 400
    except Exception as e:
        error_msg = f"Error in send_message endpoint: {str(e)}"
        print(error_msg)
        return jsonify({"status": "error", "message": error_msg}), 500
@app.route("/bulk", methods=["POST"])
def send_bulk():
    try:
        file = request.files["file"]
        message = request.form["message"]

        # Use absolute path to ensure we always use the backend/uploads folder
        file_path = os.path.join(UPLOADS_DIR, "contacts.xlsx")
        file.save(file_path)

        result = ws.send_bulk(file_path, message)
        
        # Check if there was an error
        if "error" in result:
            return jsonify({
                "status": "error",
                "message": result.get("error"),
                "success": result.get("success", 0),
                "failed": result.get("failed", 0),
                "total": result.get("total", 0)
            }), 400
        
        return jsonify({
            "status": "completed",
            "success": result.get("success", 0),
            "failed": result.get("failed", 0),
            "total": result.get("total", 0)
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


    

if __name__ == "__main__":
    app.run(debug=True)
