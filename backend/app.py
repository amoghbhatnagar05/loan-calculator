"""Flask API for the loan calculator.

Endpoints:
- GET  /api/health    liveness probe for the hosting platform
- POST /api/calculate EMI, totals, and amortization schedule
- POST /api/ask        AI loan advisor, grounded in the caller's real numbers

The AI call is proxied through this backend on purpose: the model API key
lives here as an environment variable and is never sent to the browser.
"""

import os

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

from loan_calculator import LoanCalculator

load_dotenv()  # reads backend/.env so GEMINI_API_KEY is available locally

app = Flask(__name__)
CORS(app)

# A Flash model on Gemini's free tier is plenty for a chat advisor. Kept in an
# env var so the model can be swapped without touching code if Google retires it.
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)

# Guardrails for the advisor: stay grounded in the numbers we give it, stay brief.
SYSTEM_INSTRUCTION = (
    "You are a concise, honest loan advisor built into a loan calculator. "
    "Answer only using the loan figures provided in the message. Do not invent "
    "numbers. Keep answers under 120 words, in plain language. When it helps, "
    "explain the difference between reducing-balance and flat-rate interest. "
    "End with a one-line reminder that this is general information, not "
    "personalised financial advice."
)


@app.get("/api/health")
def health():
    """Liveness probe used by the hosting platform."""
    return jsonify(status="ok")


@app.post("/api/calculate")
def calculate():
    """Compute EMI, totals, and the amortization schedule for a loan.

    Expects JSON: {"principal": number, "annual_rate": number,
                   "tenure_months": integer}
    """
    data = request.get_json(silent=True) or {}

    try:
        loan = LoanCalculator(
            principal=float(data["principal"]),
            annual_rate=float(data["annual_rate"]),
            tenure_months=int(data["tenure_months"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        # Bad input is the caller's fault, not a server error.
        message = str(error) if isinstance(error, ValueError) else "principal, annual_rate and tenure_months are required"
        return jsonify(error=message), 400

    return jsonify(loan.summary())


@app.post("/api/ask")
def ask():
    """Answer a natural-language question about a specific loan.

    Expects JSON: {"principal", "annual_rate", "tenure_months", "question"}

    We recompute the loan here rather than trusting figures from the frontend,
    so the AI is grounded in the same source of truth as the calculator.
    """
    data = request.get_json(silent=True) or {}

    question = (data.get("question") or "").strip()
    if not question:
        return jsonify(error="Please include a question."), 400
    if len(question) > 500:
        # Cap input length so a single request can't blow the token budget.
        return jsonify(error="Question is too long (max 500 characters)."), 400

    try:
        loan = LoanCalculator(
            principal=float(data["principal"]),
            annual_rate=float(data["annual_rate"]),
            tenure_months=int(data["tenure_months"]),
        )
    except (KeyError, TypeError, ValueError):
        return jsonify(error="Valid loan details are required."), 400

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return jsonify(error="The AI advisor is not configured (missing API key)."), 500

    s = loan.summary()
    context = (
        f"Loan amount: {s['principal']}. "
        f"Annual interest rate: {s['annual_rate']}% (reducing balance). "
        f"Term: {s['tenure_months']} months. "
        f"Monthly EMI: {s['emi']}. "
        f"Total repayment: {s['total_payment']}. "
        f"Total interest (reducing balance): {s['total_interest']}. "
        f"Total interest if charged as a flat rate: {s['flat_rate_total_interest']}."
    )
    prompt = f"{context}\n\nUser question: {question}"

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
        "contents": [{"parts": [{"text": prompt}]}],
    }

    try:
        response = requests.post(
            GEMINI_URL,
            params={"key": api_key},
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        body = response.json()
        answer = body["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (requests.RequestException, KeyError, IndexError):
        # Network trouble, a bad key, or an unexpected response shape all land
        # here. We fail with a clean message instead of a stack trace.
        return jsonify(error="The AI advisor could not answer right now."), 502

    return jsonify(answer=answer)


if __name__ == "__main__":
    app.run(debug=True, port=5001)
