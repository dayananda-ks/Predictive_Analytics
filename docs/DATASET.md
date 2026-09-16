# Dataset

The workspace contains a synthetic CSV in `data/raw/`.

## Known schema

- `patient_id`
- `maternal_age`
- `gestational_age_weeks`
- `nuchal_translucency_mm`
- `crown_rump_length_mm`
- `nasal_bone_present`
- `papp_a_mom`
- `free_bhcg_mom`
- `fetal_fraction_pct`
- `maternal_bmi`
- `prior_aneuploidy_pregnancy`
- `ivf_conception`
- `smoking_status`
- `outcome`

## Target handling

The synthetic outcome labels are converted into two binary targets:

- T21: `Trisomy21 = 1`, `Unaffected = 0`, `Trisomy18 = 0`
- T18: `Trisomy18 = 1`, `Unaffected = 0`, `Trisomy21 = 0`

## Inspection output

Run:

```bash
python -m ml.inspect_data
```

This writes the actual dataset inspection results to `reports/data/` and updates `data/dataset_metadata.json`.
