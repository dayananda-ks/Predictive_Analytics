# Predictive Analytics for Prenatal Screening of Trisomy 21 and Trisomy 18 using AI & ML

This is a final-year academic research prototype for prenatal screening risk estimation. It is built around a synthetic dataset and is not a diagnostic system.

## What it does

- Inspects all CSV files in `data/raw/`
- Creates binary targets for Trisomy 21 and Trisomy 18 from the synthetic outcome labels
- Trains Logistic Regression, Random Forest, SVM, and XGBoost models
- Evaluates actual holdout metrics and generates charts
- Serves a Flask web app with screening, history, performance, and reporting pages
- Stores screening history in SQLite
- Generates a PDF screening report with feature contribution summaries

## Startup

```bash
python -m pip install -r requirements.txt
python -m ml.inspect_data
python -m ml.train
python app.py
```

Open `http://127.0.0.1:5000`.

## Render Deployment

This project is ready to deploy on Render as a Python web service.

### Build command

```bash
pip install -r requirements.txt && python -m ml.inspect_data && python -m ml.train
```

### Start command

```bash
gunicorn app:app
```

### Environment variables

Set these in the Render dashboard or use the included `render.yaml` file:

- `SECRET_KEY`
- `DATABASE_PATH=data/screening_history.sqlite3`
- `MODEL_DIR=models`
- `REPORT_DIR=reports`
- `RAW_DATA_DIR=data/raw`
- `T21_LOW_THRESHOLD=0.15`
- `T21_HIGH_THRESHOLD=0.35`
- `T18_LOW_THRESHOLD=0.10`
- `T18_HIGH_THRESHOLD=0.30`

### Notes for Render

- The app uses SQLite, so the database file should live on persistent disk if you want history to survive restarts.
- The training step runs during build so the deployed service starts with trained artifacts.
- The app serves on Render through Gunicorn using the Flask app object exposed in `app.py`.

## Important disclaimer

This application is an academic research prototype for prenatal screening risk estimation. It is not a medical diagnostic tool and must not be used independently for clinical decision-making. Results should be interpreted only by qualified healthcare professionals and, where appropriate, confirmed using established clinical diagnostic procedures.

## Structure

- `ml/` training, preprocessing, inspection, and prediction utilities
- `backend/` Flask app, validation, SQLite, and PDF generation
- `frontend/` Bootstrap 5 templates, styles, and client-side JavaScript
- `reports/` generated inspection, metrics, and figure outputs
- `models/` trained artifacts and metadata

## Notes

- The provided dataset is synthetic.
- Performance metrics are only valid for the synthetic research-prototype dataset.
- The app does not diagnose conditions or replace clinical workflows.

