#!/usr/bin/env python
"""Test Marathi language support for PolicyLens."""

import json
import requests

API_URL = "http://localhost:8000/ask"

# Test questions in Marathi
marathi_questions = [
    {
        "question": "रजाईची नीती काय आहे?",
        "english": "What is the leave policy?",
    },
    {
        "question": "कर्मचाऱ्यांना किती दिवसांची रजा मिळते?",
        "english": "How many days of leave are employees entitled to?",
    },
    {
        "question": "उपस्थिती नीती काय आहे?",
        "english": "What is the attendance policy?",
    },
]

print("=" * 90)
print("MARATHI LANGUAGE SUPPORT TEST")
print("=" * 90)

for idx, test in enumerate(marathi_questions, 1):
    question = test["question"]
    english = test["english"]
    
    print(f"\n{'─' * 90}")
    print(f"Test {idx}:")
    print(f"{'─' * 90}")
    print(f"Question (Marathi):  {question}")
    print(f"English Translation: {english}")
    print(f"\n⏳ Fetching answer...")
    
    try:
        response = requests.post(
            API_URL,
            json={"question": question},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\n✓ Response Language: {data.get('language')} {'(MARATHI)' if data.get('language') == 'mr' else ''}")
            print(f"\n✓ Answer (Marathi):")
            print(f"  {data.get('answer')}")
            
            # Check if answer has Devanagari script
            answer = data.get('answer', '')
            has_devanagari = any('\u0900' <= char <= '\u097F' for char in answer)
            print(f"\n✓ Devanagari Script: {has_devanagari} ✅")
            
            print(f"\n✓ Citations: {len(data.get('citations', []))} found")
            
            if data.get('citations'):
                cite = data['citations'][0]
                print(f"  Source: {cite.get('source_file')}")
            
        else:
            print(f"✗ Error: {response.status_code}")
            print(f"  {response.text}")
            
    except Exception as e:
        print(f"✗ Connection Error: {e}")

print(f"\n{'=' * 90}")
print("MARATHI TEST COMPLETED")
print("=" * 90)
