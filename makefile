docs:
	cd docs
	make html
isort:
	isort --profile=black declaracad
	isort --profile=black tests
typecheck:
	mypy declaracad --ignore-missing-imports
lintcheck:
	flake8 --ignore=E203,E266,E501,W503,E731 declaracad
	flake8 --ignore=E203,E266,E501,W503,E731 tests
reformat:
	black declaracad
	black tests
test:
	pytest -v tests --cov declaracad --cov-report xml --asyncio-mode auto

precommit: isort reformat typecheck lintcheck
