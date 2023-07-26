APP_VERSION := $(shell grep -oP '(?<=^version = ")[^"]*' pyproject.toml)
APP_DIR := s3proxy
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
	poetry run uvicorn --reload --factory s3proxy:main.app_factory

authorize-ecr:
	aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $(ECR_REPO_URI)

bump-version:
	echo '__version__ = "$(APP_VERSION)"' > $(APP_DIR)/version.py
	git add $(APP_DIR)/version.py
	git commit -m "Bump version to $(APP_VERSION)" || true

build-docker-image:
	docker build -f Dockerfile -t $(ECR_REPO_URI)/$(APP_DIR):$(APP_VERSION) -t $(ECR_REPO_URI)/$(APP_DIR):latest .

publish-docker-image: build-docker-image authorize-ecr
	docker push $(ECR_REPO_URI)/$(APP_DIR):$(APP_VERSION)

publish-new-version: bump-version publish-docker-image

.NOTPARALLEL: publish-docker-image publish-new-version
