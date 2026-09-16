# Model

## Pipeline

The project trains separate binary classifiers for T21 and T18 using the same feature set from the selected compatible dataset.

Models:

- Logistic Regression
- Random Forest
- SVM
- XGBoost

## Preprocessing

The preprocessing pipeline is built with `Pipeline` and `ColumnTransformer`.

It handles:

- missing numerical values
- missing categorical values
- standard scaling for numeric inputs
- one-hot encoding for categorical and binary inputs
- unknown categories at prediction time

## Selection

Model selection is based on a composite validation score using cross-validated balanced accuracy, PR-AUC, and ROC-AUC. Accuracy alone is not used as the selector.

## Outputs

Training writes actual artifacts to:

- `models/t21_model.joblib`
- `models/t18_model.joblib`
- `models/preprocessing_t21.joblib`
- `models/preprocessing_t18.joblib`
- `models/model_metadata.json`

Metrics and figures are written under `reports/`.
