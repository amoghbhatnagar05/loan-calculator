# True Cost — a loan calculator that shows what a loan really costs

## Why this exists

Most loan calculators tell you the monthly payment and stop. They don't show
the two things a borrower actually needs to judge a loan: how much interest
they pay in total, and whether the rate they were quoted is a *reducing-balance*
rate or a *flat* rate. The gap between those two, at the same headline
percentage, is large and deliberate — flat-rate lending is a common way to make
an expensive loan look cheap. This tool makes that gap visible.

## What it does

Enter a loan amount, an annual interest rate, and a term. It returns:

- the **EMI** (equated monthly instalment), using the reducing-balance method;
- the **total interest** and **total repayment** over the life of the loan;
- the **flat-rate comparison** — what the same nominal rate would cost if it
  were charged flat, and how much extra that is;
- a **month-by-month amortization schedule** and a chart of the balance falling
  to zero.

## Who it's for

Anyone comparing a loan offer — personal, vehicle, or consumer-durable — who
wants to see past the monthly-payment headline to the real cost. Especially
useful against flat-rate offers, which sound competitive but rarely are.

## Architecture

The stack mirrors Better's `flask-react-template`: a Python/Flask API and a
React frontend, deployed separately.

```
backend/            Flask API
  loan_calculator.py    The domain logic — a LoanCalculator class. All the
                        interesting maths lives here and nowhere else.
  app.py                Thin HTTP layer: one POST endpoint + a health check.
  test_loan_calculator.py   Unit tests for the calculator.
frontend/           React (Vite) single-page app
  src/App.jsx           UI: inputs, results, flat-rate reveal, schedule.
  src/api.js            Talks to the backend.
.github/workflows/  CI that runs the backend tests on every push and PR.
```

The design choice worth calling out: **all financial logic sits in one plain
class with no framework dependencies.** The Flask layer only parses input and
serialises output. That keeps the maths trivially unit-testable and means the
same class could power a CLI, a mobile app, or a batch job unchanged.

### Edge cases handled deliberately

- **Zero interest rate.** The EMI formula divides by zero when the rate is 0.
  A valid interest-free loan would crash a naive implementation, so it's
  special-cased to principal ÷ term.
- **Final-instalment rounding.** Rounding each month leaves a few paise of
  phantom balance by the end. The last instalment is adjusted so the loan
  closes at exactly zero.
- **Invalid input.** Non-positive principal, negative rate, and non-integer or
  zero terms are rejected with a clear error, returned as HTTP 400.

## Run it locally

Backend:

```bash
cd backend
pip install -r requirements.txt
pytest                 # run the tests
python app.py          # serve on http://localhost:5000
```

Frontend (in a second terminal):

```bash
cd frontend
npm install
npm run dev            # serve on http://localhost:5173
```

## Deploy

**Backend on Render**

1. Push this repo to GitHub.
2. New → Web Service → point it at this repo, root directory `backend`.
3. Build command `pip install -r requirements.txt`, start command
   `gunicorn app:app`.
4. Copy the resulting URL (e.g. `https://loan-api.onrender.com`).

**Frontend on Vercel**

1. New Project → import the repo, root directory `frontend`.
2. Vercel auto-detects Vite. Add an environment variable
   `VITE_API_URL` set to the Render URL from above.
3. Deploy. Vercel gives you the public link.

## Tests

```bash
cd backend && pytest -v
```

CI runs the same suite on every push and pull request
(`.github/workflows/ci.yml`).
