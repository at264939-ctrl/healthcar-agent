"""
Emergency Notification Module
Sends SMS alerts to doctors via Twilio for emergency cases
"""

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import os
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()


class EmergencyNotifier:
    """Handles emergency SMS notifications to medical staff"""
    
    def __init__(self):
        """Initialize Twilio client"""
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.twilio_number = os.getenv("TWILIO_PHONE_NUMBER")
        self.emergency_doctor_number = os.getenv("EMERGENCY_DOCTOR_NUMBER")
        
        if not all([self.account_sid, self.auth_token, self.twilio_number]):
            raise ValueError("Twilio credentials not found in environment")
        
        self.client = Client(self.account_sid, self.auth_token)
    
    def send_emergency_sms(
        self,
        patient_info: Dict,
        triage_result: Dict,
        doctor_number: Optional[str] = None
    ) -> Dict:
        """
        Send emergency SMS notification to doctor
        
        Args:
            patient_info: Patient information (name, phone, symptoms)
            triage_result: Triage analysis result
            doctor_number: Doctor's phone number (uses default if not provided)
        
        Returns:
            Dict with status and message SID
        """
        target_number = doctor_number or self.emergency_doctor_number
        
        if not target_number:
            return {
                "status": "error",
                "message": "No emergency doctor number configured",
                "sid": None
            }
        
        message_body = self._format_emergency_message(patient_info, triage_result)
        
        try:
            message = self.client.messages.create(
                body=message_body,
                from_=self.twilio_number,
                to=target_number
            )
            
            return {
                "status": "success",
                "message": "Emergency SMS sent successfully",
                "sid": message.sid,
                "to": target_number
            }
            
        except TwilioRestException as e:
            return {
                "status": "error",
                "message": f"Failed to send SMS: {str(e)}",
                "sid": None
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Unexpected error: {str(e)}",
                "sid": None
            }
    
    def _format_emergency_message(self, patient_info: Dict, triage_result: Dict) -> str:
        """Format emergency SMS message"""
        symptoms = patient_info.get("symptoms", "Not specified")
        # Truncate symptoms if too long
        if len(symptoms) > 100:
            symptoms = symptoms[:97] + "..."
        
        message = f"""🚨 EMERGENCY ALERT 🚨

Patient: {patient_info.get('name', 'Unknown')}
Phone: {patient_info.get('phone', 'Not provided')}

Triage Level: {triage_result.get('triage_level', 'UNKNOWN')}
Specialty: {triage_result.get('specialty', 'Not specified')}

Symptoms: {symptoms}

Action Required: {triage_result.get('recommended_action', 'Immediate assessment needed')}

Confidence: {triage_result.get('confidence', 0) * 100:.0f}%

⚠️ Please respond immediately
"""
        return message.strip()
    
    def send_whatsapp_message(self, to_number: str, message: str) -> Dict:
        """
        Send WhatsApp message via Twilio
        
        Args:
            to_number: Recipient's WhatsApp number (with whatsapp: prefix)
            message: Message content
        
        Returns:
            Dict with status and message SID
        """
        # Ensure number has whatsapp: prefix
        if not to_number.startswith("whatsapp:"):
            to_number = f"whatsapp:{to_number}"
        
        from_number = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
        
        try:
            message_obj = self.client.messages.create(
                body=message,
                from_=from_number,
                to=to_number
            )
            
            return {
                "status": "success",
                "message": "WhatsApp message sent successfully",
                "sid": message_obj.sid
            }
            
        except TwilioRestException as e:
            return {
                "status": "error",
                "message": f"Failed to send WhatsApp message: {str(e)}",
                "sid": None
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Unexpected error: {str(e)}",
                "sid": None
            }
    
    def send_appointment_confirmation(
        self,
        patient_number: str,
        appointment_details: Dict
    ) -> Dict:
        """Send appointment confirmation via WhatsApp"""
        message = f"""
✅ *Appointment Confirmed*

*Specialty:* {appointment_details.get('specialty', 'Not specified')}
*Doctor:* {appointment_details.get('doctor', 'Not assigned')}
*Date:* {appointment_details.get('date', 'TBD')}
*Time:* {appointment_details.get('time', 'TBD')}

📍 Please arrive 15 minutes early

Reply CANCEL to reschedule
"""
        
        return self.send_whatsapp_message(patient_number, message.strip())
    
    def send_triage_result(
        self,
        patient_number: str,
        triage_result: Dict,
        appointment_info: Optional[Dict] = None
    ) -> Dict:
        """Send triage assessment result to patient via WhatsApp"""
        from triage_analyzer import TriageAnalyzer
        
        analyzer = TriageAnalyzer()
        message = analyzer.format_triage_report(triage_result)
        
        if appointment_info:
            message += f"""

📅 *Available Appointments:*
Doctor: {appointment_info.get('doctor', 'TBD')}
Date: {appointment_info.get('date', 'TBD')}
Time: {appointment_info.get('time', 'TBD')}

Reply BOOK to confirm this appointment
"""
        
        return self.send_whatsapp_message(patient_number, message)
    
    def test_connection(self) -> bool:
        """Test Twilio connection"""
        try:
            # Validate credentials by fetching account info
            account = self.client.api.account.fetch()
            return account.sid == self.account_sid
        except Exception:
            return False


# Singleton instance
_notifier_instance = None


def get_emergency_notifier() -> EmergencyNotifier:
    """Get or create EmergencyNotifier singleton instance"""
    global _notifier_instance
    if _notifier_instance is None:
        _notifier_instance = EmergencyNotifier()
    return _notifier_instance
