"""
ICD-10-CM Chapter Reference Data
Official 21 chapters plus a special-purpose chapter for U-codes.
Each chapter maps a code range to its clinical domain.
"""

ICD10_CHAPTERS = [
    {"id": 1,  "name": "Certain infectious and parasitic diseases",
     "range": "A00-B99",  "start": "A00", "end": "B99"},
    {"id": 2,  "name": "Neoplasms",
     "range": "C00-D49",  "start": "C00", "end": "D49"},
    {"id": 3,  "name": "Diseases of the blood and blood-forming organs",
     "range": "D50-D89",  "start": "D50", "end": "D89"},
    {"id": 4,  "name": "Endocrine, nutritional and metabolic diseases",
     "range": "E00-E89",  "start": "E00", "end": "E89"},
    {"id": 5,  "name": "Mental, behavioral and neurodevelopmental disorders",
     "range": "F01-F99",  "start": "F01", "end": "F99"},
    {"id": 6,  "name": "Diseases of the nervous system",
     "range": "G00-G99",  "start": "G00", "end": "G99"},
    {"id": 7,  "name": "Diseases of the eye and adnexa",
     "range": "H00-H59",  "start": "H00", "end": "H59"},
    {"id": 8,  "name": "Diseases of the ear and mastoid process",
     "range": "H60-H95",  "start": "H60", "end": "H95"},
    {"id": 9,  "name": "Diseases of the circulatory system",
     "range": "I00-I99",  "start": "I00", "end": "I99"},
    {"id": 10, "name": "Diseases of the respiratory system",
     "range": "J00-J99",  "start": "J00", "end": "J99"},
    {"id": 11, "name": "Diseases of the digestive system",
     "range": "K00-K95",  "start": "K00", "end": "K95"},
    {"id": 12, "name": "Diseases of the skin and subcutaneous tissue",
     "range": "L00-L99",  "start": "L00", "end": "L99"},
    {"id": 13, "name": "Diseases of the musculoskeletal system and connective tissue",
     "range": "M00-M99",  "start": "M00", "end": "M99"},
    {"id": 14, "name": "Diseases of the genitourinary system",
     "range": "N00-N99",  "start": "N00", "end": "N99"},
    {"id": 15, "name": "Pregnancy, childbirth and the puerperium",
     "range": "O00-O9A",  "start": "O00", "end": "O9A"},
    {"id": 16, "name": "Certain conditions originating in the perinatal period",
     "range": "P00-P96",  "start": "P00", "end": "P96"},
    {"id": 17, "name": "Congenital malformations, deformations and chromosomal abnormalities",
     "range": "Q00-Q99",  "start": "Q00", "end": "Q99"},
    {"id": 18, "name": "Symptoms, signs and abnormal clinical and laboratory findings, not elsewhere classified",
     "range": "R00-R99",  "start": "R00", "end": "R99"},
    {"id": 19, "name": "Injury, poisoning and certain other consequences of external causes",
     "range": "S00-T88",  "start": "S00", "end": "T88"},
    {"id": 20, "name": "External causes of morbidity",
     "range": "V00-Y99",  "start": "V00", "end": "Y99"},
    {"id": 21, "name": "Factors influencing health status and contact with health services",
     "range": "Z00-Z99",  "start": "Z00", "end": "Z99"},
    {"id": 22, "name": "Codes for special purposes",
     "range": "U00-U85",  "start": "U00", "end": "U85"},
]


def code_in_range(code_3: str, start: str, end: str) -> bool:
    """Check if a 3-char ICD-10 code falls within a chapter range (lexicographic)."""
    return start <= code_3 <= end


def get_chapter_for_code(code: str) -> dict | None:
    """Return the chapter dict for a given ICD-10 code."""
    c3 = code[:3].upper()
    for ch in ICD10_CHAPTERS:
        if code_in_range(c3, ch["start"], ch["end"]):
            return ch
    return None


def get_chapters_for_letter(letter: str) -> list[dict]:
    """Return chapters that contain codes starting with the given letter."""
    letter = letter.upper()
    result = []
    for ch in ICD10_CHAPTERS:
        start_letter = ch["start"][0]
        end_letter = ch["end"][0]
        if start_letter <= letter <= end_letter:
            result.append(ch)
    return result
