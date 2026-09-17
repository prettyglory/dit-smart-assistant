from groq import Groq

from app.config import GROQ_API_KEY


client = Groq(
    api_key=GROQ_API_KEY
)


SYSTEM_PROMPT = """
You are DIT Smart Assistant, an AI assistant for
Dar es Salaam Institute of Technology in Tanzania.

You assist students, applicants, staff and visitors.

You can communicate naturally in both English
and Kiswahili.

IMPORTANT RULES:

1. For factual questions about DIT, use only the
   VERIFIED DIT CONTEXT supplied to you.

2. Do not invent programmes, fees, campuses,
   requirements, dates, contacts or regulations.

3. DIT has multiple campuses. Never assume that
   information belonging to one campus applies
   to another campus.

4. If the verified context does not contain enough
   information to answer the question, clearly say
   that the information could not be found in the
   available verified DIT sources.

5. Answer in the same language used by the user
   unless the user requests another language.

6. Greetings and normal conversational messages
   may be answered naturally.

7. Keep answers clear, helpful and concise.
"""


def ask_groq(
    question: str,
    context: str = "",
) -> str:

    prompt = f"""
VERIFIED DIT CONTEXT:

{context if context else "No verified context was retrieved."}

USER QUESTION:

{question}

Answer according to the verified context and rules.
"""

    completion = (
        client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.1,
            max_tokens=700,
        )
    )

    return (
        completion
        .choices[0]
        .message
        .content
    )