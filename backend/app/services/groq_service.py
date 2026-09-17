from groq import Groq

from app.config import GROQ_API_KEY


client = Groq(api_key=GROQ_API_KEY)


SYSTEM_PROMPT = """
You are DIT Smart Assistant, an AI assistant for the
Dar es Salaam Institute of Technology (DIT), Tanzania.

Your role is to assist students, applicants, staff,
and visitors with information about DIT.

You can communicate in both English and Kiswahili.

Important rules:

1. Give clear and simple answers.
2. Do not invent official DIT information.
3. If you do not have verified information, say so.
4. DIT has multiple campuses.
5. Do not assume that every programme or service is
   available at every campus.
6. When campus information is available, clearly state
   the relevant campus.
7. Later you will receive verified DIT information
   through a RAG knowledge base.
"""


def ask_groq(question: str) -> str:
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": question,
            },
        ],
        temperature=0.2,
        max_tokens=700,
    )

    return completion.choices[0].message.content