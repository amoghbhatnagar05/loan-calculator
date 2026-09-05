import { useEffect, useState } from "react";
import { calculateLoan, askAdvisor } from "./api.js";

const money = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

function BalanceChart({ schedule }) {
  // A lightweight inline SVG of the outstanding balance falling to zero.
  // No charting library: the shape is simple enough to draw directly.
  if (!schedule.length) return null;

  const width = 520;
  const height = 180;
  const pad = 4;
  const start = schedule[0].balance + schedule[0].principal; // ~ principal
  const points = schedule.map((row, i) => {
    const x = pad + (i / (schedule.length - 1)) * (width - pad * 2);
    const y = pad + (1 - row.balance / start) * (height - pad * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const area = `${pad},${height - pad} ${points.join(" ")} ${width - pad},${height - pad}`;

  return (
    <svg
      className="chart"
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label="Outstanding balance falling to zero over the loan term"
    >
      <polygon points={area} className="chart-area" />
      <polyline points={points.join(" ")} className="chart-line" />
    </svg>
  );
}

const SUGGESTED = [
  "Is this a good interest rate?",
  "Should I make a prepayment?",
  "Explain the flat-rate difference.",
];

function Advisor({ principal, annualRate, tenureMonths }) {
  const [messages, setMessages] = useState([]); // {role: 'you'|'advisor', text}
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  async function send(question) {
    const q = question.trim();
    if (!q || loading) return;

    setMessages((prev) => [...prev, { role: "you", text: q }]);
    setInput("");
    setLoading(true);

    try {
      const answer = await askAdvisor({ principal, annualRate, tenureMonths, question: q });
      setMessages((prev) => [...prev, { role: "advisor", text: answer }]);
    } catch (err) {
      setMessages((prev) => [...prev, { role: "advisor", text: err.message, error: true }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="advisor">
      <h2 className="advisor-title">Ask about this loan</h2>
      <p className="advisor-sub">
        The advisor answers using the numbers above. General information, not
        financial advice.
      </p>

      <div className="chips">
        {SUGGESTED.map((s) => (
          <button key={s} className="chip" onClick={() => send(s)} disabled={loading}>
            {s}
          </button>
        ))}
      </div>

      {messages.length > 0 && (
        <div className="messages">
          {messages.map((m, i) => (
            <div key={i} className={`msg msg-${m.role}${m.error ? " msg-error" : ""}`}>
              {m.text}
            </div>
          ))}
          {loading && <div className="msg msg-advisor msg-typing">Thinking…</div>}
        </div>
      )}

      <div className="ask-row">
        <input
          type="text"
          className="ask-input"
          placeholder="Type a question…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send(input)}
          disabled={loading}
        />
        <button className="ask-btn" onClick={() => send(input)} disabled={loading || !input.trim()}>
          Ask
        </button>
      </div>
    </section>
  );
}

export default function App() {
  const [principal, setPrincipal] = useState(500000);
  const [annualRate, setAnnualRate] = useState(11);
  const [tenureMonths, setTenureMonths] = useState(60);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [showSchedule, setShowSchedule] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      calculateLoan({ principal, annualRate, tenureMonths })
        .then((data) => {
          setResult(data);
          setError(null);
        })
        .catch((err) => setError(err.message));
    }, 250);
    return () => clearTimeout(timer);
  }, [principal, annualRate, tenureMonths]);

  const hiddenCost = result
    ? result.flat_rate_total_interest - result.total_interest
    : 0;

  return (
    <main className="page">
      <header className="masthead">
        <h1>Know what a loan really costs.</h1>
        <p>
          Enter the terms your lender quoted. See the monthly payment, the total
          interest, and how much a “flat rate” would quietly add.
        </p>
      </header>

      <div className="grid">
        <section className="controls" aria-label="Loan details">
          <Field
            label="Loan amount"
            value={principal}
            display={money.format(principal)}
            min={10000}
            max={5000000}
            step={10000}
            onChange={setPrincipal}
          />
          <Field
            label="Interest rate (per year)"
            value={annualRate}
            display={`${annualRate}%`}
            min={0}
            max={30}
            step={0.25}
            onChange={setAnnualRate}
          />
          <Field
            label="Loan term"
            value={tenureMonths}
            display={`${tenureMonths} months`}
            min={6}
            max={360}
            step={6}
            onChange={setTenureMonths}
          />
        </section>

        <section className="results" aria-live="polite">
          {error && <p className="error">{error}</p>}

          {result && !error && (
            <>
              <div className="headline">
                <span className="headline-label">Monthly payment</span>
                <span className="headline-number">{money.format(result.emi)}</span>
              </div>

              <dl className="totals">
                <div>
                  <dt>You repay in total</dt>
                  <dd>{money.format(result.total_payment)}</dd>
                </div>
                <div>
                  <dt>Interest you pay</dt>
                  <dd>{money.format(result.total_interest)}</dd>
                </div>
              </dl>

              <div className="reveal">
                <p className="reveal-lead">
                  If this were sold as a <strong>flat-rate</strong> loan at the
                  same {result.annual_rate}%, the interest would be{" "}
                  {money.format(result.flat_rate_total_interest)}.
                </p>
                <p className="reveal-gap">
                  That is {money.format(hiddenCost)} more than a reducing-balance
                  loan — the same headline rate, quietly costing you extra.
                </p>
              </div>

              <BalanceChart schedule={result.schedule} />

              <button
                className="disclosure"
                onClick={() => setShowSchedule((open) => !open)}
                aria-expanded={showSchedule}
              >
                {showSchedule ? "Hide" : "Show"} month-by-month breakdown
              </button>

              {showSchedule && (
                <div className="table-wrap">
                  <table className="schedule">
                    <thead>
                      <tr>
                        <th scope="col">Month</th>
                        <th scope="col">Payment</th>
                        <th scope="col">Interest</th>
                        <th scope="col">Principal</th>
                        <th scope="col">Balance</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.schedule.map((row) => (
                        <tr key={row.month}>
                          <td>{row.month}</td>
                          <td>{money.format(row.emi)}</td>
                          <td>{money.format(row.interest)}</td>
                          <td>{money.format(row.principal)}</td>
                          <td>{money.format(row.balance)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </section>
      </div>

      {result && !error && (
        <Advisor
          principal={principal}
          annualRate={annualRate}
          tenureMonths={tenureMonths}
        />
      )}
    </main>
  );
}

function Field({ label, value, display, min, max, step, onChange }) {
  return (
    <label className="field">
      <span className="field-top">
        <span className="field-label">{label}</span>
        <span className="field-value">{display}</span>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  );
}
