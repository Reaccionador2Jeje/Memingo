# Meme Math & Data Packages

M3 expands Memingo's math and data capabilities with meme-first APIs.

| Package | Purpose | Key rituals |
| --- | --- | --- |
| `brainrot` | Math helpers | `sqrt_irl`, `powerlevel`, `factorial_arc`, `fibonacci_lore`, `is_prime_sus`, `radians`, `degrees`, `hypot`, `sin_irl`, `cos_irl` |
| `yapstats` | Statistics | `average_yap`, `median_lore`, `variance_arc`, `sample_variance`, `sample_stddev`, `geometric_mean`, `weighted_average`, `quartile_lore` |
| `whenisbro` | Timestamps and durations | `timestamp_irl`, `milliseconds_since_epoch`, `duration_parts`, `seconds_from_parts`, `weekday_lore` |
| `notfloating` | Fixed-point decimals | `fixed_from`, `fixed_to`, `fixed_add`, `fixed_sub`, `fixed_mul`, `fixed_div`, `decimal_round` |
| `brokefractions` | Rational arithmetic | `fraction_make`, `fraction_add`, `fraction_sub`, `fraction_mul`, `fraction_div`, `fraction_compare` |
| `touchgrass` | Gregorian calendar | `leap_year`, `days_in_month`, `valid_date`, `day_of_year`, `date_to_days`, `weekday_date`, `date_add_days` |

## Examples

```mgo
borrow "notfloating"
borrow "brokefractions"
borrow "touchgrass"
borrow "brainrot"

vibe price = fixed_from(1.25)
vibe tax = fixed_from(0.19)
spill fixed_to(fixed_add(price, tax))

vibe third = fraction_make(1, 3)
vibe half = fraction_make(1, 2)
spill fraction_add(third, half)

spill date_add_days(2024, 2, 28, 1)
spill sin_irl(radians(90))
```

## Semantics and limits

- `notfloating` uses integer millionths (scale 1,000,000); it is fixed-point arithmetic, not an arbitrary-precision decimal implementation.
- `brokefractions` stores fractions as two-element lists `[numerator, denominator]`, normalizes signs and reduces by the greatest common divisor. A zero denominator returns `ghost`.
- `touchgrass` uses the proleptic Gregorian calendar and Unix epoch day numbering. Supported input years are 1 through 9999 for date validation; date arithmetic returns a year/month/day list.
- `brainrot` includes common integer and geometry helpers plus Taylor-series sine/cosine approximations. It is not a replacement for a high-precision numerical library.
- `yapstats` includes population and sample statistics. Sample variance and sample standard deviation require at least two observations.

Every package exports `self_test()`. The interpreter-backed package tests run those checks in CI.
