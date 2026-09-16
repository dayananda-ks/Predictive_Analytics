# System

## Architecture

- `ml/inspect_data.py` discovers and inspects CSV files in `data/raw/`
- `ml/train.py` preprocesses data, trains models, evaluates them, and saves artifacts
- `ml/predict.py` loads saved models and returns screening probabilities plus prototype risk categories
- `backend/routes.py` exposes the API and HTML routes
- `backend/database.py` stores screening history in SQLite
- `backend/report_generator.py` creates PDF reports with ReportLab
- `frontend/templates/` contains the Bootstrap 5 UI

## API

- `GET /api/health`
- `POST /api/predict`
- `GET /api/history`
- `POST /api/history`
- `DELETE /api/history/<id>`
- `GET /api/model-info`
- `GET /api/metrics`
- `POST /api/report`

## Startup flow

```bash
python -m ml.inspect_data
python -m ml.train
python app.py
```

## Limitations

- The dataset is synthetic.
- The project is a research prototype only.
- Results are screening risk estimates, not diagnoses.
