APP_VERSION := $(shell grep -oP '(?<=^version = ")[^"]*' pyproject.toml)
APP_DIR := "s3proxy"
NPROCS = $(shell grep -c 'processor' /proc/cpuinfo)
MAKEFLAGS += -j$(NPROCS)
PYTEST_FLAGS := --failed-first -x


install:
	poetry install --with dev
	test -d .git/hooks/pre-commit || poetry run pre-commit install

e2e-test:
	poetry export --with dev --without-hashes --format=requirements.txt > requirements.txt
	docker compose build proxy-e2e-tests s3proxy
	docker compose run --rm proxy-e2e-tests

e2e-testloop:
	for number in ``seq 1 1000``; do \
	    docker compose build proxy-e2e-tests; \
        docker compose run --rm proxy-e2e-tests || (echo "e2e test failed with $$?"; exit 1); \
        docker compose down --remove-orphans ; \
    done

unit-test:
	poetry run pytest ${PYTEST_FLAGS}

testloop:
	watch -n 3 poetry run pytest ${PYTEST_FLAGS}

lint-fix:
	poetry run isort --profile black .
	poetry run black ${APP_DIR}

lint-check:
	poetry run flake8 ${APP_DIR}
	poetry run mypy .

lint: lint-fix lint-check

run-proxy:
	poetry run dotenv uvicorn --reload --factory s3proxy:main.app_factory

run-boto-client:
	poetry run dotenv boto-client
