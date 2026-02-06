.PHONY: help install test test-unit test-integration test-integration-tencent test-integration-aliyun test-coverage clean lint format

help:  ## Show this help message
	@echo "Cloud Storage Cleanup Tool - Make Commands"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}'

install:  ## Install package in development mode
	pip install -e .
	pip install pytest pytest-cov pytest-mock black ruff mypy

test:  ## Run all tests (unit only, no credentials needed)
	pytest tests/unit/ -v --cov=src/cloud_storage_clean --cov-report=html

test-unit:  ## Run unit tests only
	pytest tests/unit/ -v --cov=src/cloud_storage_clean --cov-report=term-missing

test-integration:  ## Run all integration tests (requires credentials)
	@echo "⚠️  This requires valid cloud credentials in .env file"
	pytest tests/integration/ -v -s

test-integration-tencent:  ## Run Tencent integration tests
	@echo "⚠️  Testing Tencent COS - requires credentials"
	pytest tests/integration/test_tencent_provider.py -v -s

test-integration-aliyun:  ## Run Aliyun integration tests
	@echo "⚠️  Testing Aliyun OSS - requires credentials"
	pytest tests/integration/test_aliyun_provider.py -v -s

test-integration-scanner-tencent:  ## Run scanner tests with Tencent
	@echo "⚠️  Testing scanner with Tencent - requires credentials"
	pytest tests/integration/test_scanner_integration.py -v -s --provider=tencent

test-integration-scanner-aliyun:  ## Run scanner tests with Aliyun
	@echo "⚠️  Testing scanner with Aliyun - requires credentials"
	pytest tests/integration/test_scanner_integration.py -v -s --provider=aliyun

test-coverage:  ## Generate HTML coverage report
	pytest tests/unit/ --cov=src/cloud_storage_clean --cov-report=html
	@echo ""
	@echo "✓ Coverage report generated in htmlcov/index.html"
	@echo "  Open with: open htmlcov/index.html"

test-all:  ## Run unit and integration tests
	@echo "Running unit tests..."
	pytest tests/unit/ -v
	@echo ""
	@echo "Running integration tests..."
	pytest tests/integration/ -v -s

lint:  ## Run linters (ruff)
	ruff check src/ tests/

format:  ## Format code with black
	black src/ tests/

type-check:  ## Run mypy type checking
	mypy src/

clean:  ## Clean up generated files
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Example integration test commands with test bucket

example-tencent-bucket:  ## Example: Run Tencent tests with test bucket
	@echo "Example command (replace YOUR-BUCKET):"
	@echo "  pytest tests/integration/test_tencent_provider.py -v -s --test-bucket=YOUR-BUCKET"

example-aliyun-bucket:  ## Example: Run Aliyun tests with test bucket
	@echo "Example command (replace YOUR-BUCKET):"
	@echo "  pytest tests/integration/test_aliyun_provider.py -v -s --test-bucket=YOUR-BUCKET"

example-delete-test:  ## Example: Run destructive delete tests
	@echo "⚠️  WARNING: This will DELETE files from your bucket!"
	@echo ""
	@echo "Example command (replace YOUR-BUCKET):"
	@echo "  pytest tests/integration/test_tencent_provider.py::test_batch_delete_success \\"
	@echo "    -v -s --test-bucket=YOUR-BUCKET --enable-delete"
