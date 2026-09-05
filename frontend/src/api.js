// Base URL of the Flask backend. In production this is set as a Vercel
// environment variable (VITE_API_URL); in local dev it falls back to Flask's
// port.
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:5001";

export async function calculateLoan({ principal, annualRate, tenureMonths }) {
  const response = await fetch(`${API_URL}/api/calculate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      principal,
      annual_rate: annualRate,
      tenure_months: tenureMonths,
    }),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Could not calculate this loan.");
  }
  return data;
}

// Ask the AI advisor a question about the current loan. The question and the
// loan terms go to our backend, which adds the real numbers and calls the model.
export async function askAdvisor({ principal, annualRate, tenureMonths, question }) {
  const response = await fetch(`${API_URL}/api/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      principal,
      annual_rate: annualRate,
      tenure_months: tenureMonths,
      question,
    }),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "The advisor could not answer right now.");
  }
  return data.answer;
}
