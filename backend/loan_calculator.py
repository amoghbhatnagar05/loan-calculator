"""Reducing-balance loan mathematics.

The whole product hangs on one idea: a loan is repaid in equal monthly
instalments (EMIs), but each instalment is split between interest (charged on
the *outstanding* balance) and principal. Early on you mostly pay interest;
later you mostly pay down principal. This module models that precisely.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScheduleRow:
    """One month of the amortization schedule."""

    month: int
    emi: float
    interest: float
    principal: float
    balance: float


class LoanCalculator:
    """Computes EMI, total cost, and the amortization schedule for a loan.

    Uses the reducing-balance method, which is how real lenders (and RBI
    guidelines) work: interest each month is charged only on the balance that
    is still outstanding, not on the original principal.

    Args:
        principal: Amount borrowed, in currency units. Must be > 0.
        annual_rate: Nominal annual interest rate as a percentage, e.g. 12.5.
            Must be >= 0. A rate of 0 is allowed (interest-free loan).
        tenure_months: Loan duration in months. Must be a positive integer.
    """

    def __init__(self, principal: float, annual_rate: float, tenure_months: int) -> None:
        if principal <= 0:
            raise ValueError("principal must be greater than 0")
        if annual_rate < 0:
            raise ValueError("annual_rate cannot be negative")
        if tenure_months <= 0 or int(tenure_months) != tenure_months:
            raise ValueError("tenure_months must be a positive whole number")

        self.principal = float(principal)
        self.annual_rate = float(annual_rate)
        self.tenure_months = int(tenure_months)

    @property
    def monthly_rate(self) -> float:
        """Monthly interest rate as a decimal fraction (not a percentage)."""
        return self.annual_rate / 12 / 100

    def emi(self) -> float:
        """Equated Monthly Instalment, rounded to 2 decimals.

        Standard formula:  EMI = P * r * (1+r)^n / ((1+r)^n - 1)

        Edge case: when the rate is 0 the formula divides by zero, so the EMI
        is simply the principal spread evenly across the tenure. Handling this
        explicitly is the difference between a calculator that works and one
        that crashes on a valid, real-world input.
        """
        r = self.monthly_rate
        n = self.tenure_months

        if r == 0:
            return round(self.principal / n, 2)

        growth = (1 + r) ** n
        emi = self.principal * r * growth / (growth - 1)
        return round(emi, 2)

    def amortization_schedule(self) -> list[ScheduleRow]:
        """Month-by-month breakdown of interest, principal, and balance.

        The final instalment is adjusted so the balance closes at exactly 0.
        Without this correction, accumulated rounding leaves a few paise of
        phantom balance (or overpayment) at the end of the loan.
        """
        emi = self.emi()
        r = self.monthly_rate
        balance = self.principal
        rows: list[ScheduleRow] = []

        for month in range(1, self.tenure_months + 1):
            interest = round(balance * r, 2)

            if month == self.tenure_months:
                # Last month: principal is whatever is left, EMI absorbs the
                # rounding drift so the loan closes cleanly at zero.
                principal_paid = round(balance, 2)
                emi_this_month = round(principal_paid + interest, 2)
                balance = 0.0
            else:
                principal_paid = round(emi - interest, 2)
                balance = round(balance - principal_paid, 2)
                emi_this_month = emi

            rows.append(
                ScheduleRow(
                    month=month,
                    emi=emi_this_month,
                    interest=interest,
                    principal=principal_paid,
                    balance=balance,
                )
            )

        return rows

    def total_payment(self) -> float:
        """Total amount paid over the life of the loan (principal + interest)."""
        return round(sum(row.emi for row in self.amortization_schedule()), 2)

    def total_interest(self) -> float:
        """Total interest paid over the life of the loan."""
        return round(self.total_payment() - self.principal, 2)

    def flat_rate_equivalent_total_interest(self) -> float:
        """Interest this loan *would* cost if quoted as a 'flat rate' loan.

        Flat-rate lending charges interest on the original principal for the
        whole tenure, ignoring that you are steadily paying the loan down. It
        is a common way to make a loan look cheaper than it is: the same
        nominal rate costs far more under 'flat' than under 'reducing balance'.
        Exposing this lets a borrower see the trick.
        """
        years = self.tenure_months / 12
        return round(self.principal * (self.annual_rate / 100) * years, 2)

    def summary(self) -> dict:
        """A compact result object suitable for returning from an API."""
        return {
            "principal": round(self.principal, 2),
            "annual_rate": self.annual_rate,
            "tenure_months": self.tenure_months,
            "emi": self.emi(),
            "total_payment": self.total_payment(),
            "total_interest": self.total_interest(),
            "flat_rate_total_interest": self.flat_rate_equivalent_total_interest(),
            "schedule": [row.__dict__ for row in self.amortization_schedule()],
        }
