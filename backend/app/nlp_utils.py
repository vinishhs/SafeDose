import re
from typing import List, Dict

# Common drug names for pattern matching
COMMON_DRUGS = [
    "aspirin", "ibuprofen", "acetaminophen", "paracetamol", "metformin", 
    "lisinopril", "atorvastatin", "metoprolol", "omeprazole", "simvastatin",
    "losartan", "amlodipine", "hydrochlorothiazide", "prednisone", "tramadol",
    "gabapentin", "furosemide", "warfarin", "clopidogrel", "pantoprazole",
    "sertraline", "fluoxetine", "citalopram", "venlafaxine", "duloxetine",
    "albuterol", "montelukast", "fluticasone", "loratadine", "diphenhydramine",
    "amoxicillin", "azithromycin", "clarithromycin", "doxycycline", "cephalexin",
    "ciprofloxacin", "levofloxacin", "penicillin", "erythromycin", "tetracycline"
]

def extract_drugs_from_text(prescription_text: str) -> List[Dict[str, str]]:
    """
    Extract drug information from prescription text using pattern matching.
    Returns a list of dictionaries with drug details.
    """
    if not prescription_text:
        return []
    
    text_lower = prescription_text.lower()
    found_drugs = []
    
    # Look for common drug names with dosage patterns
    for drug in COMMON_DRUGS:
        if drug in text_lower:
            # Try to extract dosage and frequency for this drug
            dosage = extract_dosage_for_drug(text_lower, drug)
            frequency = extract_frequency_for_drug(text_lower, drug)
            
            found_drugs.append({
                "name": drug.title(),
                "dosage": dosage,
                "frequency": frequency
            })
    
    # Look for patterns like "Drug Name 500mg" or "Drug Name tablets"
    drug_patterns = [
        r'\b([A-Z][a-z]+(?:[A-Z][a-z]+)*)\s*(\d+\s*mg)\s*(?:once|twice|daily|bid|tid|qid)?',
        r'\b([A-Z][a-z]+(?:[A-Z][a-z]+)*)\s*(?:tablets?|capsules?)\s*(?:of\s*)?(\d+\s*mg)?',
        r'Rx:\s*([A-Z][a-z]+(?:[A-Z][a-z]+)*)\s*(\d+\s*mg)?',
        r'Take\s+([A-Z][a-z]+(?:[A-Z][a-z]+)*)\s*(\d+\s*mg)?',
    ]
    
    for pattern in drug_patterns:
        matches = re.finditer(pattern, prescription_text, re.IGNORECASE)
        for match in matches:
            drug_name = match.group(1).title()
            dosage = match.group(2) if len(match.groups()) > 1 else None
            
            # Check if we already found this drug
            if not any(d['name'].lower() == drug_name.lower() for d in found_drugs):
                frequency = extract_frequency(text_lower, drug_name.lower())
                found_drugs.append({
                    "name": drug_name,
                    "dosage": dosage,
                    "frequency": frequency
                })
    
    # Remove duplicates by drug name (case insensitive)
    unique_drugs = []
    seen_drugs = set()
    for drug in found_drugs:
        if drug['name'].lower() not in seen_drugs:
            unique_drugs.append(drug)
            seen_drugs.add(drug['name'].lower())
    
    return unique_drugs

def extract_dosage_for_drug(text: str, drug_name: str) -> str:
    """Extract dosage information for a specific drug"""
    # Look for patterns like "drugname 500mg" or "500mg drugname"
    patterns = [
        rf'{drug_name}\s+(\d+\s*mg)',
        rf'(\d+\s*mg)\s+{drug_name}',
        rf'{drug_name}\s+(\d+\s*mg)\s+',
        rf'tablets?\s+of\s+{drug_name}\s+(\d+\s*mg)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None

def extract_frequency_for_drug(text: str, drug_name: str) -> str:
    """Extract frequency information for a specific drug"""
    # Look for frequency patterns near the drug name
    frequency_patterns = [
        rf'{drug_name}.*?(once|twice|thrice|daily|every day|qd|bid|tid|qid)',
        rf'(once|twice|thrice|daily|every day|qd|bid|tid|qid).*?{drug_name}',
    ]
    
    for pattern in frequency_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None

def extract_frequency(text: str, drug_name: str) -> str:
    """Alternative frequency extraction"""
    # Common frequency terms
    frequency_terms = ['once', 'twice', 'thrice', 'daily', 'every day', 'qd', 'bid', 'tid', 'qid']
    
    # Look for frequency terms in the same sentence as the drug
    sentences = re.split(r'[.!?]', text)
    for sentence in sentences:
        if drug_name in sentence.lower():
            for term in frequency_terms:
                if term in sentence.lower():
                    return term
    return None