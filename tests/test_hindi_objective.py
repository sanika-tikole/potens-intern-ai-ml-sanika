#!/usr/bin/env python
"""Test Hindi question for policy objective."""

import json
import requests

API_URL = "http://localhost:8000/ask"

# Hindi question about policy objective
question = "उद्देश्य यह नीति क्या है?"

print("=" * 80)
print("TESTING HINDI QUESTION")
print("=" * 80)
print(f"\nQuestion (Hindi): {question}")
print(f"\nEnglish translation: What is the objective/purpose of this policy?")
print("\n" + "-" * 80)

try:
    response = requests.post(
        API_URL,
        json={"question": question},
        timeout=30
    )
    
    if response.status_code == 200:
        data = response.json()
        
        print(f"\n✓ Response Language: {data.get('language')}")
        print(f"\n✓ Answer (Hindi):")
        print(f"{data.get('answer')}")
        
        print(f"\n✓ Citations Count: {len(data.get('citations', []))}")
        
        # Check if answer has Devanagari script
        answer = data.get('answer', '')
        has_devanagari = any('\u0900' <= char <= '\u097F' for char in answer)
        print(f"\n✓ Contains Devanagari Script: {has_devanagari}")
        
        if len(data.get('citations', [])) > 0:
            print(f"\n✓ Top Citation:")
            cite = data['citations'][0]
            print(f"  - Source: {cite.get('source_file')}")
            print(f"  - Doc ID: {cite.get('doc_id')}")
        
    else:
        print(f"✗ Error: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"✗ Connection Error: {e}")

print("\n" + "=" * 80)
