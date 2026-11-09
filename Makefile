.PHONY: install seed api ui test lint
install: ; pip install -r requirements-dev.txt
seed:    ; python scripts/seed_demo_db.py
api:     ; PYTHONPATH=src flask --app "aihub.api.app:app_factory" run --port 8000
ui:      ; PYTHONPATH=src streamlit run src/aihub/ui/streamlit_app.py
test:    ; pytest -q --cov=aihub
lint:    ; ruff check src tests
