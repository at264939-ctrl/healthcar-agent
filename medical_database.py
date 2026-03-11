"""
Medical Database Module using ChromaDB
Handles local storage and retrieval of medical specialties and appointments
"""

import chromadb
from chromadb.config import Settings
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional


class MedicalDatabase:
    """ChromaDB-based medical database for specialties and appointments"""
    
    def __init__(self, db_path: str = "./chroma_db"):
        """Initialize ChromaDB client and collections"""
        self.client = chromadb.PersistentClient(path=db_path)
        
        # Create collections
        self.specialties_collection = self.client.get_or_create_collection(
            name="specialties",
            metadata={"description": "Medical specialties and doctors"}
        )
        self.appointments_collection = self.client.get_or_create_collection(
            name="appointments",
            metadata={"description": "Available appointments"}
        )
        
        self._initialize_default_data()
    
    def _initialize_default_data(self):
        """Initialize database with default medical specialties and doctors"""
        if self.specialties_collection.count() == 0:
            # Medical specialties data
            specialties = [
                {
                    "id": "spec_001",
                    "name": "Cardiology",
                    "name_ar": "أمراض القلب",
                    "description": "Heart and cardiovascular system diseases",
                    "description_ar": "أمراض القلب والأوعية الدموية",
                    "symptoms": "chest pain, heart palpitations, shortness of breath, high blood pressure",
                    "symptoms_ar": "ألم الصدر، خفقان القلب، ضيق التنفس، ارتفاع ضغط الدم",
                    "doctors": ["Dr. Ahmed Hassan", "Dr. Sarah Mohammed"],
                    "urgency_keywords": "chest pain, heart attack, severe shortness of breath"
                },
                {
                    "id": "spec_002",
                    "name": "Neurology",
                    "name_ar": "الأعصاب",
                    "description": "Brain, spinal cord, and nervous system disorders",
                    "description_ar": "اضطرابات الدماغ والحبل الشوكي والجهاز العصبي",
                    "symptoms": "headache, migraine, seizures, numbness, dizziness",
                    "symptoms_ar": "الصداع، الشقيقة، النوبات، الخدر، الدوار",
                    "doctors": ["Dr. Mohammed Ali", "Dr. Fatima Ahmed"],
                    "urgency_keywords": "severe headache, stroke, seizure, loss of consciousness"
                },
                {
                    "id": "spec_003",
                    "name": "Emergency Medicine",
                    "name_ar": "الطوارئ",
                    "description": "Immediate care for acute illnesses and injuries",
                    "description_ar": "الرعاية الفورية للأمراض والإصابات الحادة",
                    "symptoms": "severe pain, bleeding, difficulty breathing, chest pain, trauma",
                    "symptoms_ar": "ألم شديد، نزيف، صعوبة التنفس، ألم الصدر، الصدمات",
                    "doctors": ["Dr. Omar Khalid", "Dr. Layla Mahmoud"],
                    "urgency_keywords": "emergency, critical, severe bleeding, unconscious, not breathing"
                },
                {
                    "id": "spec_004",
                    "name": "Pediatrics",
                    "name_ar": "طب الأطفال",
                    "description": "Medical care for infants, children, and adolescents",
                    "description_ar": "الرعاية الطبية للرضع والأطفال والمراهقين",
                    "symptoms": "fever, cough, rash, vomiting, diarrhea in children",
                    "symptoms_ar": "الحمى، السعال، الطفح الجلدي، القيء، الإسهال عند الأطفال",
                    "doctors": ["Dr. Aisha Ibrahim", "Dr. Khalid Youssef"],
                    "urgency_keywords": "child high fever, infant not breathing, child seizure"
                },
                {
                    "id": "spec_005",
                    "name": "Orthopedics",
                    "name_ar": "العظام",
                    "description": "Bones, joints, muscles, and skeletal system",
                    "description_ar": "العظام والمفاصل والعضلات والجهاز الهيكلي",
                    "symptoms": "bone pain, fracture, joint pain, back pain, sprain",
                    "symptoms_ar": "ألم العظام، الكسر، ألم المفاصل، ألم الظهر، الالتواء",
                    "doctors": ["Dr. Hassan Ali", "Dr. Mariam Saeed"],
                    "urgency_keywords": "broken bone, severe fracture, dislocated joint"
                },
                {
                    "id": "spec_006",
                    "name": "Dermatology",
                    "name_ar": "الجلدية",
                    "description": "Skin, hair, and nail conditions",
                    "description_ar": "حالات الجلد والشعر والأظافر",
                    "symptoms": "rash, itching, acne, skin lesions, allergic reactions",
                    "symptoms_ar": "الطفح الجلدي، الحكة، حب الشباب، آفات الجلد، الحساسية",
                    "doctors": ["Dr. Noor Ahmed", "Dr. Yusuf Hassan"],
                    "urgency_keywords": "severe allergic reaction, widespread rash with fever"
                },
                {
                    "id": "spec_007",
                    "name": "Internal Medicine",
                    "name_ar": "الباطنية",
                    "description": "Adult diseases and general medical conditions",
                    "description_ar": "أمراض البالغين والحالات الطبية العامة",
                    "symptoms": "fever, fatigue, abdominal pain, nausea, general weakness",
                    "symptoms_ar": "الحمى، التعب، ألم البطن، الغثيان، الضعف العام",
                    "doctors": ["Dr. Ibrahim Mohammed", "Dr. Samira Khalil"],
                    "urgency_keywords": "high fever, severe abdominal pain, persistent vomiting"
                },
                {
                    "id": "spec_008",
                    "name": "Ophthalmology",
                    "name_ar": "العيون",
                    "description": "Eye diseases and vision disorders",
                    "description_ar": "أمراض العيون واضطرابات الرؤية",
                    "symptoms": "eye pain, blurred vision, redness, eye injury",
                    "symptoms_ar": "ألم العين، عدم وضوح الرؤية، الاحمرار، إصابة العين",
                    "doctors": ["Dr. Amal Said", "Dr. Tarek Nasser"],
                    "urgency_keywords": "sudden vision loss, eye trauma, chemical in eye"
                }
            ]
            
            # Add specialties to ChromaDB
            for spec in specialties:
                self.specialties_collection.add(
                    ids=[spec["id"]],
                    documents=[
                        f"{spec['name']}: {spec['description']}. Symptoms: {spec['symptoms']}"
                    ],
                    metadatas=[spec]
                )
            
            # Initialize appointments
            self._initialize_appointments()
    
    def _initialize_appointments(self):
        """Generate available appointments for the next 7 days"""
        specialties = ["Cardiology", "Neurology", "Pediatrics", "Orthopedics", 
                      "Internal Medicine", "Dermatology", "Ophthalmology"]
        doctors = {
            "Cardiology": ["Dr. Ahmed Hassan", "Dr. Sarah Mohammed"],
            "Neurology": ["Dr. Mohammed Ali", "Dr. Fatima Ahmed"],
            "Pediatrics": ["Dr. Aisha Ibrahim", "Dr. Khalid Youssef"],
            "Orthopedics": ["Dr. Hassan Ali", "Dr. Mariam Saeed"],
            "Internal Medicine": ["Dr. Ibrahim Mohammed", "Dr. Samira Khalil"],
            "Dermatology": ["Dr. Noor Ahmed", "Dr. Yusuf Hassan"],
            "Ophthalmology": ["Dr. Amal Said", "Dr. Tarek Nasser"]
        }
        
        time_slots = ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
                      "14:00", "14:30", "15:00", "15:30", "16:00", "16:30"]
        
        appointment_id = 1
        for days_ahead in range(1, 8):  # Next 7 days
            date = datetime.now() + timedelta(days=days_ahead)
            date_str = date.strftime("%Y-%m-%d")
            
            for specialty in specialties:
                for doctor in doctors[specialty]:
                    for slot in time_slots:
                        self.appointments_collection.add(
                            ids=[f"apt_{appointment_id}"],
                            documents=[
                                f"{specialty} appointment with {doctor} at {slot}"
                            ],
                            metadatas=[{
                                "specialty": specialty,
                                "doctor": doctor,
                                "date": date_str,
                                "time": slot,
                                "status": "available"
                            }]
                        )
                        appointment_id += 1
    
    def search_specialty(self, symptoms: str, top_k: int = 3) -> List[Dict]:
        """Search for matching specialties based on symptoms"""
        results = self.specialties_collection.query(
            query_texts=[symptoms],
            n_results=top_k
        )
        
        matching_specialties = []
        if results["metadatas"] and results["metadatas"][0]:
            for metadata in results["metadatas"][0]:
                matching_specialties.append(metadata)
        
        return matching_specialties
    
    def get_available_appointments(self, specialty: str, days: int = 3) -> List[Dict]:
        """Get available appointments for a specialty within specified days"""
        # Get all appointments and filter
        all_appointments = self.appointments_collection.get(
            where={"specialty": specialty, "status": "available"}
        )
        
        available = []
        if all_appointments["metadatas"]:
            for metadata in all_appointments["metadatas"]:
                available.append(metadata)
        
        # Sort by date and time, return top results
        available.sort(key=lambda x: (x["date"], x["time"]))
        return available[:10]  # Return top 10 available slots
    
    def book_appointment(self, appointment_id: str, patient_info: Dict) -> bool:
        """Book an appointment (update status)"""
        try:
            # Update appointment status
            self.appointments_collection.update(
                ids=[appointment_id],
                metadatas=[{"status": "booked", "patient": patient_info.get("name", "Unknown")}]
            )
            return True
        except Exception as e:
            print(f"Error booking appointment: {e}")
            return False
    
    def get_specialty_by_name(self, name: str) -> Optional[Dict]:
        """Get specialty details by name"""
        all_specialties = self.specialties_collection.get()
        
        if all_specialties["metadatas"]:
            for metadata in all_specialties["metadatas"]:
                if metadata.get("name", "").lower() == name.lower():
                    return metadata
        
        return None
    
    def get_statistics(self) -> Dict:
        """Get database statistics"""
        return {
            "total_specialties": self.specialties_collection.count(),
            "total_appointments": self.appointments_collection.count(),
            "collections": ["specialties", "appointments"]
        }


# Singleton instance
_db_instance = None


def get_medical_database(db_path: str = "./chroma_db") -> MedicalDatabase:
    """Get or create MedicalDatabase singleton instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = MedicalDatabase(db_path)
    return _db_instance
