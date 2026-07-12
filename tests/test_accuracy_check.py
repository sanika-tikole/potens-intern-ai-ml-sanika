#!/usr/bin/env python
"""Test script to verify Hindi answer accuracy improvements."""

import os
import sys

# Load .env manually
env_file = '.env'
if os.path.exists(env_file):
    with open(env_file, 'r') as f:
        for line in f:
            if '=' in line and not line.strip().startswith('#'):
                key, val = line.strip().split('=', 1)
                os.environ[key] = val

from app.services.qa_service import answer_question
from app.services.translation_service import detect_language
from app.utils.language_utils import contains_devanagari

# Test questions
test_questions = [
    ("What is the leave policy?", "en"),  # English
    ("छुट्टी नीति क्या है?", "hi"),  # Hindi
    ("रजाईची नीती कोणती आहे?", "mr"),  # Marathi
]

print("=" * 80)
print("HINDI ANSWER ACCURACY TEST")
print("=" * 80)

for question, expected_lang in test_questions:
    print(f"\n{'─' * 80}")
    print(f"Question ({expected_lang}): {question}")
    print(f"{'─' * 80}")
    
    try:
        # Detect language
        detected = detect_language(question)
        print(f"✓ Detected language: {detected} (expected: {expected_lang})")
        
        # Get answer
        result = answer_question(question)
        
        print(f"✓ Response language: {result.language}")
        print(f"✓ Answer preview: {result.answer[:200]}...")
        
        # Check if answer is in correct script
        if result.language in {"hi", "mr"}:
            has_devanagari = contains_devanagari(result.answer)
            print(f"✓ Contains Devanagari script: {has_devanagari}")
            if not has_devanagari:
                print(f"⚠ WARNING: Answer should contain Devanagari but doesn't!")
        
        print(f"✓ Citation count: {len(result.citations)}")
        
    except Exception as e:
        print(f"✗ ERROR: {type(e).__name__}: {e}")

print(f"\n{'═' * 80}")
print("Test completed!")
print("=" * 80)
