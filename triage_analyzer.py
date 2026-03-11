"""
Triage Analysis Module using Groq (Llama-3)
Analyzes symptom severity and directs patients to appropriate specialties
"""

from groq import Groq
import os
import json
from typing import Dict, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()


class TriageAnalyzer:
    """AI-powered triage analysis using Groq Llama-3"""
    
    # Triage levels
    TRIAGE_CRITICAL = "CRITICAL"
    TRIAGE_EMERGENCY = "EMERGENCY"
    TRIAGE_URGENT = "URGENT"
    TRIAGE_NON_URGENT = "NON_URGENT"
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Groq client"""
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment")
        
        self.client = Groq(api_key=self.api_key)
        self.model = "llama-3.1-8b-instant"
    
    def analyze_symptoms(self, symptoms: str, patient_age: Optional[str] = None) -> Dict:
        """
        Analyze symptoms and return triage assessment
        
        Returns:
            Dict containing:
            - triage_level: CRITICAL, EMERGENCY, URGENT, or NON_URGENT
            - specialty: Recommended specialty
            - confidence: Confidence score (0-1)
            - reasoning: Explanation of the assessment
            - is_emergency: Boolean indicating if immediate care needed
        """
        prompt = self._create_triage_prompt(symptoms, patient_age)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Validate and normalize response
            return self._normalize_triage_result(result)
            
        except Exception as e:
            # Fallback to rule-based analysis if AI fails
            return self._rule_based_triage(symptoms)
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for triage analysis"""
        return """You are an expert medical triage assistant. Analyze patient symptoms and provide:

1. **triage_level**: One of:
   - "CRITICAL": Life-threatening, needs immediate emergency care (call ambulance)
   - "EMERGENCY": Severe condition, needs urgent care within 1 hour
   - "URGENT": Needs medical attention within 24 hours
   - "NON_URGENT": Can wait for scheduled appointment

2. **specialty**: Most appropriate medical specialty (e.g., "Cardiology", "Neurology", "Emergency Medicine", "Internal Medicine", "Pediatrics", "Orthopedics", "Dermatology", "Ophthalmology")

3. **confidence**: Number between 0.0 and 1.0 indicating confidence in assessment

4. **reasoning**: Brief explanation in English

5. **is_emergency**: Boolean - true if CRITICAL or EMERGENCY level

6. **recommended_action**: What the patient should do next

Respond ONLY with valid JSON in this exact format:
{
    "triage_level": "string",
    "specialty": "string",
    "confidence": 0.0,
    "reasoning": "string",
    "is_emergency": boolean,
    "recommended_action": "string"
}"""

    def _create_triage_prompt(self, symptoms: str, patient_age: Optional[str]) -> str:
        """Create the triage analysis prompt"""
        age_info = f"Patient age: {patient_age}" if patient_age else "Patient age: not specified"
        
        return f"""
        Please analyze the following patient case:
        
        {age_info}
        Symptoms: {symptoms}
        
        Provide triage assessment based on the symptoms described.
        Consider:
        - Severity of symptoms
        - Potential life-threatening conditions
        - Appropriate specialty for treatment
        - Urgency of care needed
        """
    
    def _normalize_triage_result(self, result: Dict) -> Dict:
        """Normalize and validate triage result"""
        # Ensure required fields exist
        required_fields = ["triage_level", "specialty", "confidence", 
                          "reasoning", "is_emergency", "recommended_action"]
        
        for field in required_fields:
            if field not in result:
                result[field] = self._get_default_value(field)
        
        # Normalize triage level
        triage_level = result["triage_level"].upper()
        if triage_level not in [self.TRIAGE_CRITICAL, self.TRIAGE_EMERGENCY, 
                                self.TRIAGE_URGENT, self.TRIAGE_NON_URGENT]:
            triage_level = self.TRIAGE_URGENT
        
        result["triage_level"] = triage_level
        
        # Ensure is_emergency matches triage_level
        if triage_level in [self.TRIAGE_CRITICAL, self.TRIAGE_EMERGENCY]:
            result["is_emergency"] = True
        
        # Ensure confidence is between 0 and 1
        result["confidence"] = max(0.0, min(1.0, float(result["confidence"])))
        
        return result
    
    def _get_default_value(self, field: str):
        """Get default value for a field"""
        defaults = {
            "triage_level": self.TRIAGE_URGENT,
            "specialty": "Internal Medicine",
            "confidence": 0.5,
            "reasoning": "Unable to determine with high confidence",
            "is_emergency": False,
            "recommended_action": "Please consult with a healthcare provider"
        }
        return defaults.get(field, None)
    
    def _rule_based_triage(self, symptoms: str) -> Dict:
        """Fallback rule-based triage if AI fails"""
        symptoms_lower = symptoms.lower()
        
        # Critical/Emergency indicators
        emergency_keywords = [
            "chest pain", "heart attack", "can't breathe", "not breathing",
            "severe bleeding", "unconscious", "stroke", "seizure",
            "severe trauma", "major accident", "poisoning", "overdose"
        ]
        
        # Urgent indicators
        urgent_keywords = [
            "high fever", "severe pain", "broken bone", "fracture",
            "difficulty breathing", "vomiting blood", "severe headache"
        ]
        
        # Check for emergency
        for keyword in emergency_keywords:
            if keyword in symptoms_lower:
                return {
                    "triage_level": self.TRIAGE_EMERGENCY,
                    "specialty": "Emergency Medicine",
                    "confidence": 0.8,
                    "reasoning": f"Emergency indicators detected: {keyword}",
                    "is_emergency": True,
                    "recommended_action": "Seek immediate emergency care or call ambulance"
                }
        
        # Check for urgent
        for keyword in urgent_keywords:
            if keyword in symptoms_lower:
                return {
                    "triage_level": self.TRIAGE_URGENT,
                    "specialty": "Internal Medicine",
                    "confidence": 0.7,
                    "reasoning": f"Urgent indicators detected: {keyword}",
                    "is_emergency": False,
                    "recommended_action": "Seek medical attention within 24 hours"
                }
        
        # Default to non-urgent
        return {
            "triage_level": self.TRIAGE_NON_URGENT,
            "specialty": "Internal Medicine",
            "confidence": 0.6,
            "reasoning": "No severe indicators detected",
            "is_emergency": False,
            "recommended_action": "Schedule a routine appointment"
        }
    
    def get_triage_color(self, triage_level: str) -> str:
        """Get color code for triage level"""
        colors = {
            self.TRIAGE_CRITICAL: "🔴",  # Red
            self.TRIAGE_EMERGENCY: "🟠",  # Orange
            self.TRIAGE_URGENT: "🟡",    # Yellow
            self.TRIAGE_NON_URGENT: "🟢"  # Green
        }
        return colors.get(triage_level, "⚪")
    
    def format_triage_report(self, triage_result: Dict) -> str:
        """Format triage result as human-readable report"""
        color = self.get_triage_color(triage_result["triage_level"])
        
        report = f"""
{color} *TRIAGE ASSESSMENT REPORT* {color}

*Triage Level:* {triage_result['triage_level']}
*Specialty:* {triage_result['specialty']}
*Confidence:* {triage_result['confidence'] * 100:.0f}%
*Emergency:* {'Yes ⚠️' if triage_result['is_emergency'] else 'No'}

*Analysis:*
{triage_result['reasoning']}

*Recommended Action:*
{triage_result['recommended_action']}
"""
        return report.strip()


# Singleton instance
_analyzer_instance = None


def get_triage_analyzer() -> TriageAnalyzer:
    """Get or create TriageAnalyzer singleton instance"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = TriageAnalyzer()
    return _analyzer_instance
