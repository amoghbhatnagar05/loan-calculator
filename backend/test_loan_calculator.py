"""Tests for LoanCalculator.

Test names follow the "it should ..." convention so each name reads as a
statement of expected behaviour, not a description of the implementation.
"""

import pytest

from loan_calculator import LoanCalculator


def test_it_should_compute_the_known_emi_for_a_standard_loan():
    # 100,000 at 12% annual over 12 months has a well-known EMI of 8884.88.
    loan = LoanCalculator(principal=100_000, annual_rate=12, tenure_months=12)
    assert loan.emi() == pytest.approx(8884.88, abs=0.01)


def test_it_should_spread_principal_evenly_when_the_rate_is_zero():
    # No interest: EMI is just principal / tenure, and no division by zero.
    loan = LoanCalculator(principal=120_000, annual_rate=0, tenure_months=12)
    assert loan.emi() == pytest.approx(10_000.00, abs=0.01)
    assert loan.total_interest() == pytest.approx(0.0, abs=0.01)


def test_it_should_repay_the_full_principal_across_the_schedule():
    loan = LoanCalculator(principal=250_000, annual_rate=9.5, tenure_months=36)
    total_principal = sum(row.principal for row in loan.amortization_schedule())
    assert total_principal == pytest.approx(loan.principal, abs=0.01)


def test_it_should_close_the_balance_at_zero_on_the_final_instalment():
    loan = LoanCalculator(principal=750_000, annual_rate=8.75, tenure_months=60)
    schedule = loan.amortization_schedule()
    assert schedule[-1].balance == pytest.approx(0.0, abs=0.01)


def test_it_should_produce_one_schedule_row_per_month():
    loan = LoanCalculator(principal=50_000, annual_rate=11, tenure_months=24)
    assert len(loan.amortization_schedule()) == 24


def test_it_should_report_total_interest_as_total_payment_minus_principal():
    loan = LoanCalculator(principal=500_000, annual_rate=10, tenure_months=48)
    expected = round(loan.total_payment() - loan.principal, 2)
    assert loan.total_interest() == pytest.approx(expected, abs=0.01)


def test_it_should_show_flat_rate_costing_more_than_reducing_balance():
    # The whole point of exposing flat rate: same nominal %, higher cost.
    loan = LoanCalculator(principal=200_000, annual_rate=12, tenure_months=24)
    assert loan.flat_rate_equivalent_total_interest() > loan.total_interest()


@pytest.mark.parametrize(
    "principal, rate, tenure",
    [
        (0, 10, 12),        # zero principal
        (-1000, 10, 12),    # negative principal
        (100_000, -5, 12),  # negative rate
        (100_000, 10, 0),   # zero tenure
        (100_000, 10, 12.5),  # fractional tenure
    ],
)
def test_it_should_reject_invalid_inputs(principal, rate, tenure):
    with pytest.raises(ValueError):
        LoanCalculator(principal=principal, annual_rate=rate, tenure_months=tenure)
