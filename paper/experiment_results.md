# Experiment Results

Generated at: 2026-09-16T13:40:24.920694+00:00

## Dataset
Number of records: 5000
Features: maternal_age, gestational_age_weeks, nuchal_translucency_mm, crown_rump_length_mm, nasal_bone_present, papp_a_mom, free_bhcg_mom, fetal_fraction_pct, maternal_bmi, prior_aneuploidy_pregnancy, ivf_conception, smoking_status
Class distribution: {"T21": 130, "T18": 45, "Unaffected": 4825}
Missing values: {"patient_id": 0, "maternal_age": 0, "gestational_age_weeks": 0, "nuchal_translucency_mm": 156, "crown_rump_length_mm": 0, "nasal_bone_present": 149, "papp_a_mom": 0, "free_bhcg_mom": 0, "fetal_fraction_pct": 143, "maternal_bmi": 152, "prior_aneuploidy_pregnancy": 0, "ivf_conception": 0, "smoking_status": 0, "outcome": 0, "t21_target": 0, "t18_target": 0}

## Training
Train size: 4000
Test size: 1000
Models: logistic_regression, random_forest, svm, xgboost

## Results
### T21
Selected model: logistic_regression
Actual metrics: {"accuracy": 0.946, "precision": 0.2602739726027397, "recall": 1.0, "f1": 0.41304347826086957, "balanced_accuracy": 0.9724770642201834, "roc_auc": 0.9976930092816138, "pr_auc": 0.8677626836075589}

### T18
Selected model: logistic_regression
Actual metrics: {"accuracy": 0.993, "precision": 0.46153846153846156, "recall": 1.0, "f1": 0.631578947368421, "balanced_accuracy": 0.9964788732394366, "roc_auc": 1.0, "pr_auc": 1.0}

Performance on the synthetic research-prototype dataset.

This application is an academic research prototype for prenatal screening risk estimation. It is not a medical diagnostic tool and must not be used independently for clinical decision-making.