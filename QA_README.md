# PolicyLens Q&A System - Documentation

## Overview

The PolicyLens Q&A system allows users to ask questions about policy documents and receive accurate, context-based answers. The system supports multiple languages including English, Hindi, and Marathi.

---

## Features

✅ **Multilingual Support**
- English (en)
- Hindi (hi) - with Devanagari script
- Marathi (mr) - with Devanagari script

✅ **Language-Aware Responses**
- Questions in any language are automatically detected
- Answers are generated directly in the target language (not translated)
- Higher accuracy by generating native language responses

✅ **Evidence-Based Answers**
- Answers backed by document excerpts
- Citations from source documents
- Transparent source information

✅ **Smart Fallbacks**
- Graceful handling when documents don't contain answer
- Safe fallback messages in all supported languages
- No hallucinated information

---

## API Endpoint

### **POST /ask**

Ask a question and get an answer from the policy documents.

#### Request Format

```json
{
  "question": "What is the leave policy?"
}
```

#### Response Format

```json
{
  "question": "What is the leave policy?",
  "answer": "The policy allows employees to take paid leave according to the leave types defined...",
  "language": "en",
  "citations": [
    {
      "source_file": "LEAVE POLICY – VERSION 1",
      "doc_id": "LEAVE POLICY – VERSION 1",
      "snippet": "Leave is granted to employees in accordance with the following rules...",
      "page_no": 1,
      "chunk_id": "chunk_123"
    }
  ]
}
```

---

## Usage Examples

### Example 1: English Question

**cURL Command:**
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the leave policy?"
  }'
```

**Response:**
```json
{
  "question": "What is the leave policy?",
  "answer": "The leave policy grants employees different types of paid leave including sick leave, earned leave, and planned leave. Employees must follow notice periods and procedures as specified.",
  "language": "en",
  "citations": [...]
}
```

---

### Example 2: Hindi Question

**cURL Command:**
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "छुट्टी की नीति क्या है?"
  }'
```

**Response:**
```json
{
  "question": "छुट्टी की नीति क्या है?",
  "answer": "छुट्टी की नीति कर्मचारियों को विभिन्न प्रकार की सवेतन छुट्टी देती है जिसमें बीमारी की छुट्टी, अर्जित छुट्टी और नियोजित छुट्टी शामिल हैं। कर्मचारियों को नोटिस अवधि और प्रक्रियाओं का पालन करना चाहिए।",
  "language": "hi",
  "citations": [...]
}
```

---

### Example 3: Marathi Question

**cURL Command:**
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "रजाईची नीती काय आहे?"
  }'
```

**Response:**
```json
{
  "question": "रजाईची नीती काय आहे?",
  "answer": "रजाईची नीती कर्मचाऱ्यांना विविध प्रकारच्या भाड़ी रजाई देते ज्यात आजारी रजाई, कमावलेली रजाई आणि नियोजित रजाई समाविष्ट आहे।",
  "language": "mr",
  "citations": [...]
}
```

---

### Example 4: Using PowerShell

```powershell
$body = @{
    question = "What are the medical certificate requirements for sick leave?"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/ask" `
  -Method POST `
  -Headers @{"Content-Type" = "application/json"} `
  -Body $body

$response | ConvertTo-Json -Depth 10
```

---

### Example 5: Specific Policy Topic

**Question in English:**
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How many days notice is required for planned leave?"
  }'
```

**Expected Answer:** The notice period requirement from the LEAVE POLICY document.

---

## Response Fields Explained

| Field | Type | Description |
|-------|------|-------------|
| `question` | string | The question asked by the user |
| `answer` | string | The generated answer based on documents |
| `language` | string | Detected language of the question (en/hi/mr) |
| `citations` | array | List of evidence/sources supporting the answer |

### Citation Object Fields

| Field | Type | Description |
|-------|------|-------------|
| `source_file` | string | Name of the document file |
| `doc_id` | string | Document identifier in vectorstore |
| `snippet` | string | Relevant text excerpt from document |
| `page_no` | integer | Page number (if available) |
| `chunk_id` | string | Internal chunk identifier |

---

## Supported Questions

The Q&A system can answer questions about:

### Leave Policy
- Leave types and eligibility
- Notice periods
- Medical certificate requirements
- Carry-forward of unused leave
- Planned vs unplanned leave
- Leave procedures

### Attendance Policy
- Attendance requirements
- Exemptions and special cases
- Reporting procedures
- Penalties for low attendance

### Reimbursement Policy
- Eligible expenses
- Reimbursement limits
- Documentation requirements
- Approval processes

### Grievance Policy
- Grievance filing procedures
- Resolution timelines
- Escalation procedures
- Employee rights

### Internship Policy
- Internship terms
- Leave policies for interns
- Responsibilities
- Contract details

---

## Language Detection

The system automatically detects the language of your question:

| Language | How It Works |
|----------|------------|
| **English** | Default if Devanagari script not detected |
| **Hindi** | Detected by Devanagari script characters |
| **Marathi** | Detected by Devanagari script characters |

You don't need to specify the language - the system handles it automatically.

---

## Answer Generation Process

1. **Language Detection**: System detects question language
2. **Question Translation**: Question normalized to English for retrieval
3. **Document Retrieval**: Relevant policy document chunks retrieved from vectorstore
4. **Answer Generation**: LLM generates answer directly in target language
5. **Citation Extraction**: Sources identified and formatted
6. **Response Delivery**: Complete answer with citations returned

---

## Important Notes

### ✅ What Works Well
- Questions about specific policy requirements
- Questions about procedures and processes
- Questions comparing different leave types
- Questions about eligibility criteria
- Questions about notice periods and deadlines

### ⚠️ Limitations
- Answers based only on provided documents
- No outside knowledge or assumptions
- If document doesn't contain information, system says so
- Cannot answer questions about policies not in documents

### 🔴 Error Handling

**Missing Document:**
```json
{
  "answer": "मुझे सुरक्षित रूप से उत्तर देने के लिए पर्याप्त संदर्भ नहीं मिला।",
  "language": "hi",
  "citations": []
}
```

**Invalid Request:**
```json
{
  "error": "Invalid request format",
  "details": "Question field is required"
}
```

---

## Quick Test Script (PowerShell)

Save this as `test_qa.ps1` and run:

```powershell
# Test 1: English Question
Write-Host "TEST 1: English Question" -ForegroundColor Cyan
$q1 = @{ question = "What is the leave policy?" } | ConvertTo-Json
$r1 = Invoke-RestMethod -Uri "http://localhost:8000/ask" -Method POST `
  -Headers @{"Content-Type"="application/json"} -Body $q1
Write-Host "Answer: $($r1.answer)" -ForegroundColor Green
Write-Host "Language: $($r1.language)`n"

# Test 2: Hindi Question
Write-Host "TEST 2: Hindi Question" -ForegroundColor Cyan
$q2 = @{ question = "चिकित्सा प्रमाणपत्र की आवश्यकता क्या है?" } | ConvertTo-Json
$r2 = Invoke-RestMethod -Uri "http://localhost:8000/ask" -Method POST `
  -Headers @{"Content-Type"="application/json"} -Body $q2
Write-Host "Answer: $($r2.answer)" -ForegroundColor Green
Write-Host "Language: $($r2.language)`n"

# Test 3: Notice Period Question
Write-Host "TEST 3: Notice Period" -ForegroundColor Cyan
$q3 = @{ question = "How many days notice required for leave?" } | ConvertTo-Json
$r3 = Invoke-RestMethod -Uri "http://localhost:8000/ask" -Method POST `
  -Headers @{"Content-Type"="application/json"} -Body $q3
Write-Host "Answer: $($r3.answer)" -ForegroundColor Green
Write-Host "Citations: $($r3.citations.Count) sources`n"
```

---

## Backend Requirements

✅ **FastAPI Backend** - Running on `http://localhost:8000`
✅ **ChromaDB** - Vector database with policy documents
✅ **Groq LLM** - Language model (llama-3.1-8b-instant)
✅ **Environment Variable** - `GROQ_API_KEY` must be set

---

## Common Questions

**Q: Can I ask follow-up questions?**
A: Each question is independent. The system doesn't maintain conversation history.

**Q: What if the answer is wrong?**
A: Check the citations - they show what the system based its answer on. If the citation is incorrect, the document data may need review.

**Q: How long does it take to get an answer?**
A: Typically 1-3 seconds depending on document size and network.

**Q: Can I ask questions in mix of languages?**
A: The system detects the primary language. Use single language per question for best results.

**Q: What if no documents contain the answer?**
A: System returns safe fallback: "Could not find enough supporting information in the documents."

---

## Troubleshooting

**Error: Cannot connect to http://localhost:8000**
- Make sure FastAPI backend is running
- Check that port 8000 is not in use
- Terminal should show: `INFO: Uvicorn running on http://127.0.0.1:8000`

**Error: GROQ_API_KEY not found**
- Set environment variable: `$env:GROQ_API_KEY = "your-key"`
- Restart the backend

**Answer is blank or says "Could not find"**
- The question topic may not be covered in documents
- Try rephrasing the question
- Check if the document has been ingested properly

**Wrong language detected**
- For Hindi/Marathi, ensure you're using Devanagari script
- English is detected by default if no Devanagari found

---

## API Reference

### Ask Endpoint

**Method:** POST  
**URL:** `http://localhost:8000/ask`  
**Content-Type:** `application/json`

**Request Body:**
```json
{
  "question": "string - Your question about the policies"
}
```

**Response Body:**
```json
{
  "question": "string",
  "answer": "string",
  "language": "string (en|hi|mr)",
  "citations": [
    {
      "source_file": "string",
      "doc_id": "string",
      "snippet": "string",
      "page_no": "integer or null",
      "chunk_id": "string"
    }
  ]
}
```

**Status Codes:**
- `200` - Success
- `400` - Bad request (invalid format)
- `500` - Server error

---

## Related Features

- **Contradiction Detection** - Compare two policies for conflicts (see CONTRADICTION_README.md)
- **Document Ingestion** - Add new policies to the system (see README.md)
- **Streamlit UI** - User-friendly interface (run `streamlit run ui/streamlit_app.py`)

---

## Support

For issues or questions:
1. Check the citations to verify sources
2. Review the troubleshooting section
3. Check backend logs on the terminal running uvicorn
4. Verify document ingestion was successful

---

**Last Updated:** 2026-07-11  
**Version:** 1.0
