import logging
import sys
from app.services.qa_service import answer_question
from app.services.translation_service import detect_language

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

q = "?????? ?? ???? ???? ???"
print("Detected lang:", detect_language(q))
res = answer_question(q)
print("FINAL RESULT:", res)
