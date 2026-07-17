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
    effective_annual_rate: Decimal | None
    schedule: list[ScheduleEntry]


def compute(
    *,
    principal_amount: int,
    tenor_months: int,
    nominal_annual_rate: Decimal,
    upfront_fee: int,
    amortization_method: AmortizationEnum,
    financed_fee: int = 0,
    service_fee: int = 0,
    admin_fee: int = 0,
) -> LoanMathResult:
    """Build a monthly schedule from the financed balance.

    Upfront, service, and admin fees are unfinanced and reduce proceeds.
    `financed_fee` is added to the balance and repaid through the schedule.
    Late penalties are intentionally not an input because they are excluded
    from normal scheduled cash flows (PLAN §5.7).
    """
    financed_balance = principal_amount + financed_fee
    if amortization_method is AmortizationEnum.REDUCING_BALANCE:
        schedule = _reducing_balance_schedule(financed_balance, tenor_months, nominal_annual_rate)
    else:
        schedule = _flat_schedule(financed_balance, tenor_months, nominal_annual_rate)

    total_repayment = sum(e.payment_amount for e in schedule)
    interest_amount = sum(e.interest_component for e in schedule)
    instalment_amount = schedule[0].payment_amount if schedule else 0

    return LoanMathResult(
        net_disbursed_amount=principal_amount - upfront_fee - service_fee - admin_fee,
        instalment_amount=instalment_amount,
        interest_amount=interest_amount,
        total_repayment=total_repayment,
        effective_annual_rate=_effective_annual_rate(
            net_proceeds=principal_amount - upfront_fee - service_fee - admin_fee,
            payments=[entry.payment_amount for entry in schedule],
        ),
        schedule=schedule,
    )


def safe_principal_for_terms(
    *,
    maximum_safe_instalment: int,
    tenor_months: int,
    nominal_annual_rate: Decimal,
    amortization_method: AmortizationEnum,
    upfront_fee_ratio: Decimal = Decimal(0),
    financed_fee: int = 0,
    service_fee: int = 0,
    admin_fee: int = 0,
) -> int:
    """Return the greatest whole-IDR principal whose complete schedule fits.

    Every candidate uses :func:`compute`, including the offer's financed and
    unfinanced fee treatments. Unfinanced fees affect proceeds/effective cost,
    while financed fees affect the repayment ceiling. Checking every rounded
    payment, rather than only the first instalment, covers final-period
    rounding remainders.
    """
    if maximum_safe_instalment <= 0 or tenor_months <= 0:
        return 0

    def fits(principal: int) -> bool:
        result = compute(
            principal_amount=principal,
            tenor_months=tenor_months,
            nominal_annual_rate=nominal_annual_rate,
            upfront_fee=_to_money(Decimal(principal) * upfront_fee_ratio),
            financed_fee=financed_fee,
            service_fee=service_fee,
            admin_fee=admin_fee,
            amortization_method=amortization_method,
        )
        return (
            bool(result.schedule)
            and max(entry.payment_amount for entry in result.schedule) <= maximum_safe_instalment
        )

    if not fits(0):
        return 0

    low = 0
    high = maximum_safe_instalment * tenor_months
    while fits(high):
        low = high
        high *= 2

    while low + 1 < high:
        midpoint = (low + high) // 2
        if fits(midpoint):
            low = midpoint
        else:
            high = midpoint
    return low


def effective_annual_reference_rate(
    *, principal_amount: int, tenor_months: int, annual_flat_rate: Decimal
) -> Decimal | None:
    """Convert a no-fee flat reference to effective annual IRR like-for-like."""
    return compute(
        principal_amount=principal_amount,
        tenor_months=tenor_months,
        nominal_annual_rate=annual_flat_rate,
        upfront_fee=0,
        amortization_method=AmortizationEnum.FLAT,
    ).effective_annual_rate


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
    net_proceeds: int,
    payments: list[int],
) -> Decimal | None:
    """Annualized monthly IRR from actual proceeds and every scheduled cash flow."""
    if net_proceeds <= 0 or not payments or any(payment < 0 for payment in payments):
        return None
    if all(payment == 0 for payment in payments):
        return Decimal(0) if net_proceeds == 0 else None

    proceeds = Decimal(net_proceeds)

    def npv(monthly_rate: Decimal) -> Decimal:
        one_plus_rate = Decimal(1) + monthly_rate
        return proceeds - sum(
            (Decimal(payment) / (one_plus_rate**period))
            for period, payment in enumerate(payments, start=1)
        )

    low = Decimal("-0.999999")
    high = Decimal("1")
    low_npv = npv(low)
    high_npv = npv(high)
    while high_npv < 0 and high < Decimal("1024"):
        high *= 2
        high_npv = npv(high)
    if low_npv > 0 or high_npv < 0:
        return None

    for _ in range(160):
        midpoint = (low + high) / Decimal(2)
        if npv(midpoint) < 0:
            low = midpoint
        else:
            high = midpoint
    monthly_rate = (low + high) / Decimal(2)
    annual_rate = (Decimal(1) + monthly_rate) ** 12 - Decimal(1)
    return annual_rate.quantize(_RATE_Q, rounding=ROUND_HALF_UP)
