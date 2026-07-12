# Hindi Answer Accuracy Improvements - Report

## Issues Found

### 1. **LLM Instructions Not Language-Aware**
- **Problem**: The `build_qa_prompt()` function always instructed the LLM to answer in English, regardless of the user's language
- **Impact**: Even when processing Hindi questions, the LLM would generate English answers first, then translate them
- **Result**: Translation quality degradation, loss of context, and inaccurate Hindi answers

### 2. **Lossy Translation Chain**
- **Problem**: 
  - Hindi question → translate to English
  - Process in English
  - LLM generates English answer
  - Translate English answer → Hindi
  - (Sometimes) Re-translate via LLM rewrite
- **Impact**: Each translation step introduces errors and loses contextual nuance
- **Result**: Final Hindi answer is multiple steps removed from original context

### 3. **No Script Validation**
- **Problem**: LLM had no explicit instruction to write in Devanagari script for Hindi/Marathi
- **Impact**: LLM sometimes mixed English and Hindi (code-switching)
- **Result**: Responses with English words mixed in, violating language purity

---

## Fixes Applied

### ✅ Fix 1: Enhanced Prompt Template (`app/utils/prompts.py`)

**Changes:**
- Added `{language_instruction}` placeholder to `ANSWER_PROMPT`
- Updated prompt to emphasize "MUST answer in {target_language}"
- Added explicit Devanagari script instruction for Hindi/Marathi
- New line: "Always respond entirely in {target_language}. Do not mix languages."

**Result:** LLM now receives clear, language-specific instructions from the start.

### ✅ Fix 2: Language-Aware Prompt Building (`app/utils/prompts.py`)

**Function: `build_qa_prompt(question, chunks, target_language='en', original_language='en')`**

**Changes:**
- Now accepts `target_language` and `original_language` parameters
- Auto-detects Devanagari language (Hindi/Marathi)
- Adds script-specific instructions:
  ```
  "Write EVERY word in Devanagari script. No English words except names/numbers/policy codes."
  ```
- Maps language codes to readable language names (hi → Hindi, mr → Marathi)

**Result:** Prompt is customized for each language at generation time.

### ✅ Fix 3: Improved QA Service (`app/services/qa_service.py`)

**Changes to `answer_question()` function:**
- Passes `original_language` to `build_qa_prompt()`
- Enhanced system prompt for Hindi/Marathi:
  ```python
  if original_language in {"hi", "mr"}:
      system_prompt = (
          f"You are a policy expert. Answer ONLY from the provided context. "
          f"You must respond entirely in {LANGUAGE_LABELS.get(original_language)}. "
          f"Never use the source language (English) in your answer unless for names or numbers."
      )
  ```
- Reduces unnecessary translation steps

**Result:** LLM generates answers directly in target language, not translated from English.

### ✅ Fix 4: Optimized Answer Finalization (`app/services/qa_service.py`)

**Function: `_finalize_answer()` - New Logic:**

```
1. If target language is English → return as-is
2. If answer already has Devanagari script → return (already in target language, no translation needed!)
3. If answer is in English → translate to target language
4. If translation fails → attempt rewrite via LLM
5. Last resort → return best available
```

**Result:** 
- Skips unnecessary translations when LLM already generates in target language
- Reduces error accumulation
- Faster response times

### ✅ Fix 5: Contradiction Service Updates (`app/services/contradiction_service.py`)

**Changes:**
- Updated `build_contradiction_prompt()` call to pass `language` parameter
- Enhanced system prompt to include language instruction:
  ```python
  f"...Respond entirely in {LANGUAGE_LABELS.get(language)}."
  ```

**Result:** Consistency across all API endpoints (ask, contradict).

---

## Expected Improvements

| Aspect | Before | After |
|--------|--------|-------|
| **Answer Generation** | English → Translate to Hindi | Direct Hindi generation |
| **Prompt Instructions** | Hardcoded to English | Language-specific |
| **Script Purity** | Mixed English/Hindi | Pure Devanagari script |
| **Translation Steps** | 2-3 steps (lossy) | 0-1 steps (minimal) |
| **Contextual Accuracy** | Low (translation loss) | High (direct generation) |
| **Response Time** | Slower (multiple LLM calls) | Faster (fewer calls) |

---

## Testing Recommendations

1. **Run the test script:**
   ```bash
   python test_accuracy_check.py
   ```

2. **Test specific Hindi questions:**
   - "छुट्टी नीति क्या है?" (What is the leave policy?)
   - "उपस्थिति नीति क्या है?" (What is the attendance policy?)

3. **Verify:**
   - ✓ Answers are in pure Devanagari script
   - ✓ No English word mixing (except policy names)
   - ✓ Answers match policy content accurately
   - ✓ Natural, flowing Hindi phrasing

---

## Files Modified

1. `app/utils/prompts.py` - Prompt templates and builders
2. `app/services/qa_service.py` - QA answer generation logic
3. `app/services/contradiction_service.py` - Contradiction detection
4. `test_accuracy_check.py` - New test script (created)

---

## Summary

The accuracy issues were caused by **language-agnostic LLM instructions combined with a lossy translation chain**. By making the system language-aware from the beginning, we:

- Eliminate unnecessary translation steps
- Reduce error accumulation
- Generate more accurate, contextually appropriate Hindi answers
- Ensure script purity (Devanagari only)
- Provide faster response times
