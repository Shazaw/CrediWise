# Public Dataset Attribution

CrediWise owns the feature schema, training pipeline, model artifact, runtime,
and evaluation produced in this directory. It does not claim ownership of the
public source records.

## Berka / PKDD'99 Financial

- Source: CTU Relational Dataset Repository, `financial` database
- URL: https://relational.fel.cvut.cz/dataset/Financial
- Original challenge: PKDD'99 Discovery Challenge
- Use: pre-loan transaction feature research and the historical A-vs-B
  finished-loan benchmark
- Redistribution: no explicit open-data license was found. Raw and transformed
  rows are therefore excluded from Git and must not be redistributed without
  permission.

Only transactions strictly before `loan.date` are acquired. Running-loan
statuses C and D are excluded because they are censored and are not equivalent
to completed outcomes.

## UCI Default of Credit Card Clients

- DOI: https://doi.org/10.24432/C55S3H
- URL: https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients
- Creator: I-Cheng Yeh
- License: Creative Commons Attribution 4.0 International
- Use: separate payment-history benchmark; never pooled with Berka

## UCI South German Credit

- DOI: https://doi.org/10.24432/C5QG88
- URL: https://archive.ics.uci.edu/dataset/573/south+german+credit+update
- License: Creative Commons Attribution 4.0 International
- Use: separate robustness teaching benchmark; never pooled with Berka

No source listed here establishes predictive validity for Indonesian thin-file,
gig-worker, or UMKM users. The exported model is a research signal and cannot
approve, reject, price, or determine a safe loan.
