# Data Dictionary

## Cancelled appointments
- slot_id: anonymized slot identifier
- service_line: service category
- urgency_tier: Emergency / High / Standard / Routine
- slot_date: available appointment date
- slot_start: appointment start time
- max_travel_minutes: operational travel ceiling
- readiness_required: minimum readiness score
- verification_required: whether verified queue status is required

## Verified waitlist
- candidate_id: anonymized candidate identifier
- service_line: service category
- urgency_tier: candidate urgency tier
- travel_minutes: estimated travel time to site
- readiness_score: 0–100 operational readiness estimate
- verified: verification status
- available_today: same-day availability flag
- earliest_date: earliest acceptable appointment date
- contactable: operationally contactable flag
- prior_declines: prior decline count
- last_updated: record freshness date
