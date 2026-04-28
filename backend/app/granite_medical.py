import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import logging
from typing import Dict

logger = logging.getLogger(__name__)

class GraniteMedicalAssistant:
    """IBM Granite model for medical text analysis"""
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_loaded = False
        self.model_name = "ibm-granite/granite-3.3-2b-instruct"
        
    def load_model(self):
        """Load the IBM Granite model with optimized settings"""
        try:
            logger.info(f"Loading IBM Granite model: {self.model_name}")
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True
            )
            
            # Load model with memory optimization
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map="auto" if self.device == "cuda" else None,
                low_cpu_mem_usage=True,
                trust_remote_code=True
            )
            
            self.model_loaded = True
            logger.info("IBM Granite model loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load IBM Granite model: {e}")
            return False
    
    def generate_medical_advice(self, prescription_text: str, patient_age: int) -> Dict:
        """Generate medical advice using IBM Granite model"""
        if not self.model_loaded:
            if not self.load_model():
                return {"error": "IBM Granite model failed to load. Requires ~6GB RAM and internet connection."}
        
        try:
            # Create medical context prompt
            prompt = f"""As a medical AI assistant, analyze this prescription for a {patient_age}-year-old patient:

Prescription: {prescription_text}

Please provide:
1. Potential drug interactions to watch for
2. Age-appropriate dosage considerations
3. Alternative medication suggestions if needed
4. Safety recommendations

Analysis:"""
            
            # Format for chat template
            messages = [{"role": "user", "content": prompt}]
            
            # Apply chat template
            inputs = self.tokenizer.apply_chat_template(
                messages,
                add_generation_prompt=True,
                tokenize=True,
                return_dict=True,
                return_tensors="pt",
            ).to(self.device)

            # Generate response
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=400,
                temperature=0.7,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id,
                top_p=0.9
            )
            
            # Decode response
            response = self.tokenizer.decode(
                outputs[0][inputs["input_ids"].shape[-1]:], 
                skip_special_tokens=True
            ).strip()
            
            return {
                "model": self.model_name,
                "analysis": response,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"IBM Granite analysis failed: {e}")
            return {"error": f"Analysis failed: {str(e)}", "success": False}

# Global instance
granite_medical = GraniteMedicalAssistant()