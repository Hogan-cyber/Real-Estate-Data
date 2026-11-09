# Mortgage registration lag implementation plan

Goal: apply the user's explicit fixed one-month LR registration-lag assumption to
existing comparison estimates, while keeping every official observation unchanged.

Design: calculated rows use LR registration month t. LR inputs stay at t; HKMA
bank drawdowns and the count/amount refinancing-approval shares both use t-1.
The user chose this fixed assumption over parallel 0/1/2-month scenarios. Keep
existing IDs, numeric columns and missing-value behavior. Label the assumption
in flags, source notes, formulas, workbook opening view and collection status.
This does not identify actual money-lender lending or remove LR refinancing.

1. Add regressions for default lag, December/January rollover, absent prior
   months, unchanged raw inputs and separate count/amount refinancing shares.
2. Implement month-key matching in mortgage_estimates.build (default lag=1),
   retaining older inputs needed at a requested export start boundary.
3. Update visible Excel formulas, calculation documentation and README; keep
   the model's mortgage-mix and amount limitations explicit.
4. Check cross-format equality, compare all official rows unchanged, review
   independently, publish 0.6.3 and verify the released data and reader cache.
