"""
Healthcare Agent - Main Flask Application
Integrates Twilio WhatsApp, ChromaDB, Groq Triage, and Emergency SMS
"""

from flask import Flask, request, jsonify
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

from medical_database import get_medical_database, MedicalDatabase
from triage_analyzer import get_triage_analyzer, TriageAnalyzer
from emergency_notifier import get_emergency_notifier, EmergencyNotifier

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize components
db: MedicalDatabase = None
triage_analyzer: TriageAnalyzer = None
notifier: EmergencyNotifier = None


def initialize_components():
    """Initialize all system components"""
    global db, triage_analyzer, notifier
    
    try:
        db_path = os.getenv("CHROMA_DB_PATH", "./chroma_db")
        db = get_medical_database(db_path)
        logger.info("✓ Medical Database initialized")
        
        triage_analyzer = get_triage_analyzer()
        logger.info("✓ Triage Analyzer initialized")
        
        notifier = get_emergency_notifier()
        logger.info("✓ Emergency Notifier initialized")
        
        return True
    except Exception as e:
        logger.error(f"✗ Failed to initialize components: {e}")
        return False


# ============================================================================
# TWILIO WEBHOOK ENDPOINTS
# ============================================================================

@app.route('/webhook/whatsapp', methods=['POST'])
def whatsapp_webhook():
    """
    Handle incoming WhatsApp messages from patients
    Expects Twilio webhook format
    """
    try:
        # Get message data from Twilio
        from_number = request.form.get('From', '')
        message_body = request.form.get('Body', '')
        message_sid = request.form.get('MessageSid', '')
        
        logger.info(f"Received WhatsApp message from {from_number}: {message_body[:50]}...")
        
        # Remove 'whatsapp:' prefix if present
        if from_number.startswith('whatsapp:'):
            from_number = from_number
        
        # Process the message
        response = process_patient_message(from_number, message_body)
        
        # Return TwiML response
        from twilio.twiml.messaging_response import MessagingResponse
        twilio_response = MessagingResponse()
        twilio_response.message(response.get('reply', 'Thank you for contacting Healthcare Agent'))
        
        return str(twilio_response)
        
    except Exception as e:
        logger.error(f"Error processing WhatsApp webhook: {e}")
        from twilio.twiml.messaging_response import MessagingResponse
        response = MessagingResponse()
        response.message("Sorry, we're experiencing technical difficulties. Please try again later.")
        return str(response)


@app.route('/webhook/sms', methods=['POST'])
def sms_webhook():
    """Handle incoming SMS messages"""
    try:
        from_number = request.form.get('From', '')
        message_body = request.form.get('Body', '')
        
        logger.info(f"Received SMS from {from_number}: {message_body[:50]}...")
        
        response = process_patient_message(from_number, message_body)
        
        from twilio.twiml.messaging_response import MessagingResponse
        twilio_response = MessagingResponse()
        twilio_response.message(response.get('reply', 'Thank you for contacting Healthcare Agent'))
        
        return str(twilio_response)
        
    except Exception as e:
        logger.error(f"Error processing SMS webhook: {e}")
        from twilio.twiml.messaging_response import MessagingResponse
        response = MessagingResponse()
        response.message("Sorry, we're experiencing technical difficulties.")
        return str(response)


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/api/triage', methods=['POST'])
def api_triage():
    """
    API endpoint for triage analysis
    
    Expected JSON:
    {
        "symptoms": "chest pain, shortness of breath",
        "patient_name": "John Doe",
        "patient_phone": "+1234567890",
        "patient_age": "45" (optional)
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'symptoms' not in data:
            return jsonify({
                "status": "error",
                "message": "Symptoms are required"
            }), 400
        
        symptoms = data.get('symptoms', '')
        patient_name = data.get('patient_name', 'Unknown')
        patient_phone = data.get('patient_phone', '')
        patient_age = data.get('patient_age')
        
        # Perform triage analysis
        triage_result = triage_analyzer.analyze_symptoms(symptoms, patient_age)
        
        patient_info = {
            "name": patient_name,
            "phone": patient_phone,
            "symptoms": symptoms
        }
        
        # If emergency, send SMS alert to doctor
        if triage_result.get('is_emergency', False):
            logger.warning(f"EMERGENCY CASE: {patient_name} - {triage_result['triage_level']}")
            notification_result = notifier.send_emergency_sms(patient_info, triage_result)
            triage_result['emergency_notification'] = notification_result
        
        # Search for matching specialty and appointments
        matching_specialties = db.search_specialty(symptoms)
        appointments = []
        
        if matching_specialties:
            specialty_name = matching_specialties[0].get('name', 'Internal Medicine')
            appointments = db.get_available_appointments(specialty_name)
        
        return jsonify({
            "status": "success",
            "triage": triage_result,
            "matching_specialties": matching_specialties,
            "available_appointments": appointments[:3],  # Top 3 slots
            "patient_info": patient_info
        })
        
    except Exception as e:
        logger.error(f"Error in triage API: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/api/appointments', methods=['GET'])
def api_get_appointments():
    """Get available appointments for a specialty"""
    try:
        specialty = request.args.get('specialty', 'Internal Medicine')
        days = int(request.args.get('days', 3))
        
        appointments = db.get_available_appointments(specialty, days)
        
        return jsonify({
            "status": "success",
            "specialty": specialty,
            "appointments": appointments
        })
        
    except Exception as e:
        logger.error(f"Error getting appointments: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/api/book', methods=['POST'])
def api_book_appointment():
    """Book an appointment"""
    try:
        data = request.get_json()
        
        appointment_id = data.get('appointment_id')
        patient_info = data.get('patient_info', {})
        
        if not appointment_id:
            return jsonify({
                "status": "error",
                "message": "Appointment ID is required"
            }), 400
        
        success = db.book_appointment(appointment_id, patient_info)
        
        if success:
            # Send confirmation
            appointment_details = db.appointments_collection.get(ids=[appointment_id])
            if appointment_details and appointment_details.get('metadatas'):
                notifier.send_appointment_confirmation(
                    patient_info.get('phone', ''),
                    appointment_details['metadatas'][0]
                )
            
            return jsonify({
                "status": "success",
                "message": "Appointment booked successfully"
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to book appointment"
            }), 500
        
    except Exception as e:
        logger.error(f"Error booking appointment: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/api/specialties', methods=['GET'])
def api_get_specialties():
    """Get all available specialties"""
    try:
        all_specialties = db.specialties_collection.get()
        
        specialties = []
        if all_specialties.get('metadatas'):
            for metadata in all_specialties['metadatas']:
                specialties.append({
                    "id": metadata.get('id'),
                    "name": metadata.get('name'),
                    "name_ar": metadata.get('name_ar'),
                    "description": metadata.get('description'),
                    "doctors": metadata.get('doctors', [])
                })
        
        return jsonify({
            "status": "success",
            "specialties": specialties
        })
        
    except Exception as e:
        logger.error(f"Error getting specialties: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/api/stats', methods=['GET'])
def api_get_stats():
    """Get system statistics"""
    try:
        stats = db.get_statistics()
        stats['twilio_connected'] = notifier.test_connection()
        
        return jsonify({
            "status": "success",
            "statistics": stats
        })
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def process_patient_message(from_number: str, message: str) -> Dict:
    """
    Process incoming patient message and return appropriate response
    
    Args:
        from_number: Patient's phone/WhatsApp number
        message: Message content (symptoms description)
    
    Returns:
        Dict with reply message and action taken
    """
    message_lower = message.lower().strip()
    
    # Handle simple commands
    if message_lower in ['help', 'helpme', '/help']:
        return {
            "reply": """
🏥 *Healthcare Agent - Help*

Please describe your symptoms and I'll help you find the right doctor.

Examples:
• "I have chest pain and difficulty breathing"
• "My child has a high fever"
• "I need to see a dermatologist"

Type your symptoms to get started
            """,
            "action": "help_requested"
        }
    
    if message_lower in ['start', '/start']:
        return {
            "reply": """
👋 Welcome to *Healthcare Agent*

I'm here to help you find the right medical care.

Please describe your symptoms in detail, and I will:
1. Assess the urgency of your condition
2. Recommend the right specialty
3. Find available appointments

What symptoms are you experiencing?
            """,
            "action": "welcome_sent"
        }
    
    # If message looks like symptoms (not a command), perform triage
    if len(message) > 10 and not message.startswith('/'):
        try:
            # Perform triage analysis
            triage_result = triage_analyzer.analyze_symptoms(message)
            
            patient_info = {
                "name": "Patient",
                "phone": from_number,
                "symptoms": message
            }
            
            # If emergency, send SMS alert
            if triage_result.get('is_emergency', False):
                notifier.send_emergency_sms(patient_info, triage_result)
                logger.warning(f"EMERGENCY ALERT sent for: {from_number}")
            
            # Find matching specialties
            matching_specialties = db.search_specialty(message)
            
            # Get available appointments
            appointments = []
            appointment_info = None
            
            if matching_specialties:
                specialty_name = matching_specialties[0].get('name', 'Internal Medicine')
                appointments = db.get_available_appointments(specialty_name)
                if appointments:
                    appointment_info = appointments[0]
            
            # Send triage result to patient
            notifier.send_triage_result(from_number, triage_result, appointment_info)
            
            # Format reply
            reply = triage_analyzer.format_triage_report(triage_result)
            
            if appointments:
                apt = appointments[0]
                reply += f"""

📅 *Next Available Appointment:*
Doctor: {apt['doctor']}
Date: {apt['date']}
Time: {apt['time']}

Reply *BOOK* to confirm
"""
            
            return {
                "reply": reply,
                "action": "triage_completed",
                "triage_result": triage_result,
                "appointments": appointments
            }
            
        except Exception as e:
            logger.error(f"Error processing patient message: {e}")
            return {
                "reply": "I apologize, but I'm having trouble processing your request right now. Please try again or call our hotline for immediate assistance.",
                "action": "error"
            }
    
    # Default response
    return {
        "reply": "Please describe your symptoms so I can help you find the right medical care.",
        "action": "awaiting_symptoms"
    }


# ============================================================================
# HEALTH CHECK & STATUS
# ============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Healthcare Agent"
    })


@app.route('/status', methods=['GET'])
def system_status():
    """Detailed system status"""
    try:
        status = {
            "timestamp": datetime.now().isoformat(),
            "components": {
                "database": {
                    "status": "connected",
                    "specialties": db.specialties_collection.count(),
                    "appointments": db.appointments_collection.count()
                },
                "triage": {
                    "status": "ready",
                    "model": triage_analyzer.model
                },
                "notifications": {
                    "status": "connected" if notifier.test_connection() else "disconnected",
                    "twilio": "active"
                }
            }
        }
        
        return jsonify(status)
        
    except Exception as e:
        return jsonify({
            "status": "degraded",
            "error": str(e)
        }), 500


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🏥  HEALTHCARE AGENT - Starting...")
    print("="*60 + "\n")
    
    # Initialize components
    if not initialize_components():
        print("❌ Failed to initialize. Check logs for details.")
        exit(1)
    
    # Get configuration
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", 5000))
    
    print(f"✅ All systems ready!")
    print(f"🌐 Server running on http://{host}:{port}")
    print(f"\nWebhook Endpoints:")
    print(f"  • WhatsApp: POST /webhook/whatsapp")
    print(f"  • SMS: POST /webhook/sms")
    print(f"\nAPI Endpoints:")
    print(f"  • Triage: POST /api/triage")
    print(f"  • Appointments: GET /api/appointments")
    print(f"  • Book: POST /api/book")
    print(f"  • Specialties: GET /api/specialties")
    print(f"\n" + "="*60 + "\n")
    
    # Run Flask app
    app.run(host=host, port=port, debug=True)
