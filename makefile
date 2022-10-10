docs:
	cd docs
	make html
isort:
	isort --profile=black declaracad tests
typecheck:
	mypy declaracad tests --ignore-missing-imports
lintcheck:
	flake8 --ignore=E501,E203,W503 declaracad tests
reformat:
	black declaracad tests
	clang-format -i src/*.cpp
	clang-format -i src/*.h
test:
	pytest -v tests --cov declaracad --cov-report xml --asyncio-mode auto
cleancache:
	find ./ -type d -name "__enamlcache__" -exec rm -rf {} \;
precommit: isort reformat lintcheck typecheck
