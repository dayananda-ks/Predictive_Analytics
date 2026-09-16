# prenatal_screening_synthetic_dataset.csv

## What this is
A **synthetic** research-prototype dataset for building/testing an ML pipeline
for prenatal Trisomy 21 / Trisomy 18 risk screening. 5,000 rows, 14 columns.

**This is not real patient data.** No public dataset of real, labeled prenatal
screening data (maternal age + NT + PAPP-A + hCG + cfDNA + trisomy outcome)
is openly downloadable — every published study in this space uses private
hospital data (e.g., Çukurova University, Cruces University Hospital,
University of Debrecen, George Washington University). This file was
generated to let you build and demonstrate the full pipeline honestly.

## How it was generated
Feature distributions were calibrated using patterns reported in the
first-trimester combined screening literature:
- Maternal age shifted older in T21/T18 groups (well-documented effect)
- Nuchal translucency (NT) elevated in aneuploidy, with realistic overlap
- PAPP-A (MoM) suppressed in T21, more severely in T18
- Free β-hCG (MoM) elevated in T21, suppressed in T18 (the classic divergent
  pattern used in real combined screening)
- cfDNA fetal fraction slightly reduced in T18, inversely related to BMI
- Nasal bone absence more frequent in T21/T18
- ~2.6% T21, ~0.9% T18 prevalence (enriched screening-cohort rate, not true
  birth prevalence) to keep the class-imbalance problem realistic but workable
- ~3% missingness injected into ultrasound/lab columns (real screening data
  always has missing values)
- Patient IDs included for correct patient-level train/test splitting

Random seed = 42 (reproducible).

## Columns
| Column | Description |
|---|---|
| patient_id | Synthetic patient identifier |
| maternal_age | Years |
| gestational_age_weeks | Weeks at testing (11.0–13.9) |
| nuchal_translucency_mm | Ultrasound NT measurement |
| crown_rump_length_mm | Ultrasound CRL |
| nasal_bone_present | 0/1 |
| papp_a_mom | PAPP-A, multiples of median |
| free_bhcg_mom | Free β-hCG, multiples of median |
| fetal_fraction_pct | cfDNA fetal fraction (%) |
| maternal_bmi | kg/m² |
| prior_aneuploidy_pregnancy | 0/1 history flag |
| ivf_conception | 0/1 |
| smoking_status | 0/1 |
| outcome | Target: Unaffected / Trisomy21 / Trisomy18 |

## Required disclosure for your report
State explicitly in your methodology chapter that this dataset is synthetic,
generated to reflect literature-reported statistical patterns, and that any
performance metrics reflect your pipeline's ability to recover known
patterns — NOT real-world clinical accuracy. This is exactly the honest
framing your project guide recommends (Section 1: "present as a research
prototype... not a diagnostic tool").

## Getting real data (for a stronger project)
If time allows, follow your guide's Phase 2 recommendation: contact an
obstetrics/genetics department for anonymized, IRB-approved data, or check
PhysioNet for any newly released relevant datasets.
