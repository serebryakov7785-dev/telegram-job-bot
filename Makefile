.PHONY: install-dev lint lint-fix test test-cov clean

install-dev:
	pip install -r requirements-dev.txt

lint:
	@echo "Running all linters..."
	isort . --check-only
	black . --check
	flake8 .
	mypy .

lint-fix:
	@echo "Auto-fixing code issues..."
	isort .
	black .

test:
	pytest -v

test-cov:
	pytest --cov=. --cov-report=term-missing

clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +