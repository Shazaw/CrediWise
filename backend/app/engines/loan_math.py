"""Pure loan-mathematics helpers (PLAN §5.7 "Loan Mathematics Contract",
FR-11 AC3; CLAUDE.md §4.1: financial calculations are ordinary deterministic
code, never AI-derived).

No DB, network, filesystem, clock, or RNG (PLAN §10.1). Consumed by the
offer-seeding service to turn a seeded offer template's terms into the full
§5.7 contract: net amount received, scheduled interest, amortisation
schedule, total scheduled repayment, and an effective annual rate where
computable.

Two amortisation methods are implemented (`AmortizationEnum.FLAT` mirrors
`app/engines/safe_borrowing.py`'s `principal_from_instalment`;
`.REDUCING_BALANCE` is a standard declining-balance annuity).
`FIXED_SCHEDULE` is reserved for a future lender-supplied schedule this
module does not compute.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.models.enums import AmortizationEnum

_MONEY_Q = Decimal("1")
_RATE_Q = Decimal("0.0001")


@dataclass(frozen=True)
class ScheduleEntry:
    period: int
    payment_amount: int
    principal_component: int
    interest_component: int
    remaining_balance: int


@dataclass(frozen=True)
class LoanMathResult:
    net_disbursed_amount: int
    instalment_amount: int
    interest_amount: int
    total_repayment: int
    effective_annual_rate: Decimal
    schedule: list[ScheduleEntry]


def compute(
    *,
    principal_amount: int,
    tenor_months: int,
    nominal_annual_rate: Decimal,
    upfront_fee: int,
    amortization_method: AmortizationEnum,
) -> LoanMathResult:
    if amortization_method is AmortizationEnum.REDUCING_BALANCE:
        schedule = _reducing_balance_schedule(principal_amount, tenor_months, nominal_annual_rate)
    else:
        schedule = _flat_schedule(principal_amount, tenor_months, nominal_annual_rate)

    total_repayment = sum(e.payment_amount for e in schedule)
    interest_amount = sum(e.interest_component for e in schedule)
    instalment_amount = schedule[0].payment_amount if schedule else 0

    return LoanMathResult(
        net_disbursed_amount=principal_amount - upfront_fee,
        instalment_amount=instalment_amount,
        interest_amount=interest_amount,
        total_repayment=total_repayment,
        effective_annual_rate=_effective_annual_rate(
            principal_amount=principal_amount,
            interest_amount=interest_amount,
            tenor_months=tenor_months,
            nominal_annual_rate=nominal_annual_rate,
            amortization_method=amortization_method,
        ),
        schedule=schedule,
    )


def _to_money(value: Decimal) -> int:
    return int(value.quantize(_MONEY_Q, rounding=ROUND_HALF_UP))


def _flat_schedule(
    principal: int, tenor_months: int, annual_flat_rate: Decimal
) -> list[ScheduleEntry]:
    """PLAN §5.7 flat-rate amortisation: total interest = principal *
    annual_rate * (tenor/12) (identical formula to `safe_borrowing.py`'s
    `principal_from_instalment`), spread evenly with the whole-rupiah
    rounding remainder pushed onto the final period so the schedule sums to
    exactly `principal + total_interest` (§5.1: "half-up ... at each
    scheduled payment"). Every period's payment is derived *from* its own
    principal/interest components (not computed independently) so
    `payment == principal_component + interest_component` always holds.
    """
    if tenor_months <= 0:
        return []
    total_interest = _to_money(
        Decimal(principal) * annual_flat_rate * Decimal(tenor_months) / Decimal(12)
    )
    base_principal, principal_remainder = divmod(principal, tenor_months)
    base_interest, interest_remainder = divmod(total_interest, tenor_months)

    schedule = []
    remaining = principal
    for period in range(1, tenor_months + 1):
        is_last = period == tenor_months
        principal_component = base_principal + (principal_remainder if is_last else 0)
        interest_component = base_interest + (interest_remainder if is_last else 0)
        remaining -= principal_component
        schedule.append(
            ScheduleEntry(
                period=period,
                payment_amount=principal_component + interest_component,
                principal_component=principal_component,
                interest_component=interest_component,
                remaining_balance=max(0, remaining),
            )
        )
    return schedule


def _reducing_balance_schedule(
    principal: int, tenor_months: int, annual_nominal_rate: Decimal
) -> list[ScheduleEntry]:
    """Standard declining-balance annuity: monthly rate = nominal/12; the
    fixed instalment solves `P * r / (1 - (1+r)^-n)`. Interest/principal
    split is recomputed each period against the declining balance; the final
    period's principal component is forced to exactly clear the remaining
    balance so whole-rupiah rounding never leaves a residual (§5.1).
    """
    if tenor_months <= 0:
        return []
    monthly_rate = annual_nominal_rate / Decimal(12)
    if monthly_rate == 0:
        level_payment = _to_money(Decimal(principal) / Decimal(tenor_months))
    else:
        factor = (Decimal(1) + monthly_rate) ** tenor_months
        level_payment = _to_money(
            Decimal(principal) * monthly_rate * factor / (factor - Decimal(1))
        )

    schedule = []
    remaining = Decimal(principal)
    for period in range(1, tenor_months + 1):
        interest_component = _to_money(remaining * monthly_rate)
        if period == tenor_months:
            principal_component = _to_money(remaining)
        else:
            principal_component = level_payment - interest_component
        payment_amount = principal_component + interest_component
        remaining -= Decimal(principal_component)
        schedule.append(
            ScheduleEntry(
                period=period,
                payment_amount=payment_amount,
                principal_component=principal_component,
                interest_component=interest_component,
                remaining_balance=max(0, _to_money(remaining)),
            )
        )
    return schedule


def _effective_annual_rate(
    *,
    principal_amount: int,
    interest_amount: int,
    tenor_months: int,
    nominal_annual_rate: Decimal,
    amortization_method: AmortizationEnum,
) -> Decimal:
    if principal_amount <= 0 or tenor_months <= 0:
        return Decimal(0)
    if amortization_method is AmortizationEnum.REDUCING_BALANCE:
        monthly_rate = nominal_annual_rate / Decimal(12)
        ear = (Decimal(1) + monthly_rate) ** 12 - Decimal(1)
        return ear.quantize(_RATE_Q, rounding=ROUND_HALF_UP)
    # FLAT: interest is charged on the full principal for the whole tenor
    # even though the outstanding balance actually declines each period --
    # the commonly used conversion re-expresses that same total interest as
    # a rate against the *average* outstanding balance (~principal/2),
    # annualised over the tenor. Documented gap-fill (§24.11): PLAN §5.7
    # requires "effective annual rate where computable" but not a specific
    # flat-to-effective conversion formula.
    ear = (Decimal(interest_amount) / (Decimal(principal_amount) / Decimal(2))) * (
        Decimal(12) / Decimal(tenor_months)
    )
    return ear.quantize(_RATE_Q, rounding=ROUND_HALF_UP)
