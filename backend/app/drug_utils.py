from .models import InteractionAlert, DosageAlert, AlternativeSuggestion

# Dummy data for drug interactions and alternatives
drug_interactions = {
    ("atorvastatin", "clarithromycin"): "May increase risk of muscle damage and kidney problems",
    ("aspirin", "ibuprofen"): "May increase risk of gastrointestinal bleeding",
    ("warfarin", "ibuprofen"): "May increase risk of serious bleeding",
    ("lisinopril", "ibuprofen"): "May reduce kidney function and blood pressure control",
    ("metformin", "ibuprofen"): "May increase risk of lactic acidosis",
    ("simvastatin", "clarithromycin"): "May increase risk of muscle damage",
    ("digoxin", "clarithromycin"): "May increase digoxin toxicity",
}

age_dosage_recommendations = {
    "atorvastatin": { 
        "adult": "10-80mg once daily", 
        "child": "Not recommended under 18" 
    },
    "clarithromycin": { 
        "adult": "250-500mg twice daily", 
        "child": "7.5mg/kg twice daily (max 500mg)" 
    },
    "aspirin": { 
        "adult": "75-325mg once daily", 
        "child": "Contraindicated under 18 (Reye's syndrome)" 
    },
    "amoxicillin": { 
        "adult": "250-500mg three times daily", 
        "child": "20-40mg/kg per day in divided doses" 
    },
    "metformin": { 
        "adult": "500-1000mg twice daily", 
        "child": "Not recommended under 10 years" 
    },
    "ibuprofen": { 
        "adult": "200-400mg three times daily", 
        "child": "5-10mg/kg every 6-8 hours" 
    },
    "azithromycin": { 
        "adult": "250-500mg once daily", 
        "child": "5-10mg/kg once daily" 
    },
    "simvastatin": { 
        "adult": "5-40mg once daily", 
        "child": "Not recommended under 18" 
    },
}

alternative_drugs = {
    "atorvastatin": ["rosuvastatin", "simvastatin", "pravastatin"],
    "clarithromycin": ["azithromycin", "amoxicillin", "doxycycline", "levofloxacin"],
    "aspirin": ["acetaminophen", "clopidogrel"],
    "ibuprofen": ["acetaminophen", "naproxen"],
    "warfarin": ["apixaban", "rivaroxaban", "dabigatran"],
    "simvastatin": ["atorvastatin", "rosuvastatin", "pravastatin"],
}

def check_interactions(drug_list, patient_age):
    """Check for interactions between drugs using the dummy data"""
    alerts = []
    drug_names = [d.name.lower() for d in drug_list]
    
    for i in range(len(drug_names)):
        for j in range(i + 1, len(drug_names)):
            drug_a, drug_b = drug_names[i], drug_names[j]
            
            # Check both possible orders of the drug pair
            pair = (drug_a, drug_b)
            rev_pair = (drug_b, drug_a)
            
            if pair in drug_interactions:
                alerts.append(InteractionAlert(
                    drug_a=drug_list[i].name,
                    drug_b=drug_list[j].name,
                    description=drug_interactions[pair],
                    severity="high" if any(word in drug_interactions[pair].lower() for word in ["bleeding", "damage", "serious", "toxicity"]) else "medium"
                ))
            elif rev_pair in drug_interactions:
                alerts.append(InteractionAlert(
                    drug_a=drug_list[j].name,
                    drug_b=drug_list[i].name,
                    description=drug_interactions[rev_pair],
                    severity="high" if any(word in drug_interactions[rev_pair].lower() for word in ["bleeding", "damage", "serious", "toxicity"]) else "medium"
                ))
    
    return alerts

def check_dosage(drug, patient_age):
    """Check dosage appropriateness using the dummy data"""
    alerts = []
    drug_name = drug.name.lower()
    
    if drug_name in age_dosage_recommendations:
        category = "child" if patient_age < 18 else "adult"
        recommended_dosage = age_dosage_recommendations[drug_name].get(category, "Dosage info not available")
        
        # Add alert if dosage recommendation exists
        if recommended_dosage != "Dosage info not available":
            alerts.append(DosageAlert(
                drug=drug.name,
                issue=f"Age-appropriate dosage recommendation",
                recommended_dosage=recommended_dosage
            ))
        
        # Special case for aspirin in children
        if drug_name == "aspirin" and patient_age < 18:
            alerts.append(DosageAlert(
                drug="Aspirin",
                issue="Contraindicated in patients under 18 due to risk of Reye's syndrome",
                recommended_dosage="Use acetaminophen instead"
            ))
        
        # Special case for atorvastatin in children
        if drug_name == "atorvastatin" and patient_age < 18:
            alerts.append(DosageAlert(
                drug="Atorvastatin",
                issue="Not recommended for patients under 18 years old",
                recommended_dosage="Consult pediatric specialist"
            ))
    
    return alerts

def get_alternatives(drug, patient, reason):
    """Suggest alternative medications using the dummy data"""
    alternatives = []
    drug_name = drug.name.lower()
    
    if drug_name in alternative_drugs:
        for alt_drug in alternative_drugs[drug_name]:
            alternatives.append(AlternativeSuggestion(
                original_drug=drug.name,
                suggested_drug=alt_drug.capitalize(),
                reason=f"Alternative to {drug.name} due to {reason}"  # ← Use 'reason' parameter, not alert.description
            ))
    
    return alternatives