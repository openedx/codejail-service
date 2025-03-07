.DEFAULT_GOAL := help

.PHONY: help clean clean_tox docs requirements ci_requirements dev_requirements \
        validation_requirements doc_requirements static shell \
        test coverage isort_check isort style lint qualityvalidate \
        migrate html_coverage upgrade extract_translation dummy_translations \
        compile_translations fake_translations pull_translations \
        detect_changed_source_translations validate_translations \
        install_transifex_client

# For opening files in a browser. Use like: $(BROWSER)relative/path/to/file.html
BROWSER := python -m webbrowser file://$(CURDIR)/

# Generates a help message. Borrowed from https://github.com/pydanny/cookiecutter-djangopackage.
help: ## display this help message
	@echo "Please use \`make <target>\` where <target> is one of"
	@awk -F ':.*?## ' '/^[a-zA-Z]/ && NF==2 {printf "\033[36m  %-25s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST) | sort

clean: ## delete generated byte code and coverage reports
	find . -name '*.pyc' -delete
	coverage erase
	rm -rf assets

clean_tox: ## clear tox requirements cache
	rm -fr .tox

docs: ## generate Sphinx HTML documentation, including API docs
	tox -e docs
	$(BROWSER)docs/_build/html/index.html

piptools: ## install pinned version of pip-compile and pip-sync
	pip install -r requirements/pip.txt
	pip install -r requirements/pip-tools.txt

requirements: dev_requirements ## sync to default requirements

ci_requirements: validation_requirements ## sync to requirements needed for CI checks

dev_requirements: clean_tox piptools ## sync to requirements for local development
	pip-sync -q requirements/dev.txt requirements/private.*

prod_requirements: piptools ## sync virtualenv to requirements needed for production
	pip-sync -q requirements/base.txt

validation_requirements: piptools ## sync to requirements for testing & code quality checking
	pip-sync -q requirements/validation.txt

doc_requirements: piptools
	pip-sync -q requirements/doc.txt

static: ## generate static files
	python manage.py collectstatic --noinput

shell: ## run Django shell
	python manage.py shell

test: clean ## run tests and generate coverage report
	pytest

# To be run from CI context
coverage: clean
	pytest --cov-report html
	$(BROWSER)htmlcov/index.html

isort_check: ## check that isort has been run
	isort --check-only codejail_service/

isort: ## run isort to sort imports in all Python files
	isort --atomic codejail_service/

style: ## run Python style checker
	pylint --rcfile=pylintrc codejail_service *.py

lint: ## run Python code linting
	pylint --rcfile=pylintrc codejail_service *.py

quality:
	tox -e quality

validate: test quality ## run tests, quality

migrate: ## apply database migrations
	python manage.py migrate

html_coverage: ## generate and view HTML coverage report
	coverage html && open htmlcov/index.html

# Define COMPILE_OPTS=-v to get more information during make upgrade.
PIP_COMPILE = pip-compile $(COMPILE_OPTS)

compile-requirements: export CUSTOM_COMPILE_COMMAND=make upgrade
compile-requirements: ## Re-compile *.in requirements to *.txt
	pip install -qr requirements/pip-tools.txt
	# Make sure to compile files after any other files they include!
	$(PIP_COMPILE) --allow-unsafe -o requirements/pip.txt requirements/pip.in
	$(PIP_COMPILE) -o requirements/pip-tools.txt requirements/pip-tools.in
	pip install -qr requirements/pip.txt
	pip install -qr requirements/pip-tools.txt
	$(PIP_COMPILE) -o requirements/base.txt requirements/base.in
	$(PIP_COMPILE) -o requirements/test.txt requirements/test.in
	$(PIP_COMPILE) -o requirements/doc.txt requirements/doc.in
	$(PIP_COMPILE) -o requirements/quality.txt requirements/quality.in
	$(PIP_COMPILE) -o requirements/validation.txt requirements/validation.in
	$(PIP_COMPILE) -o requirements/ci.txt requirements/ci.in
	$(PIP_COMPILE) -o requirements/dev.txt requirements/dev.in
	# Let tox control the Django version for tests
	grep -e "^django==" requirements/base.txt > requirements/django.txt
	sed '/^[dD]jango==/d' requirements/test.txt > requirements/test.tmp
	mv requirements/test.tmp requirements/test.txt

upgrade:  ## update the pip requirements files to use the latest releases satisfying our constraints
	$(MAKE) compile-requirements COMPILE_OPTS="--upgrade $(COMPILE_OPTS)"

extract_translations: ## extract strings to be translated, outputting .mo files
	cd codejail_service && i18n_tool extract --no-segment

dummy_translations: ## generate dummy translation (.po) files
	cd codejail_service && i18n_tool dummy

compile_translations: # compile translation files, outputting .po files for each supported language
	python manage.py compilemessages

fake_translations: extract_translations dummy_translations compile_translations ## generate and compile dummy translation files

ifeq ($(OPENEDX_ATLAS_PULL),)
pull_translations: ## pull translations from Transifex
	tx pull -af -t --mode reviewed
else
# Experimental: OEP-58 Pulls translations using atlas
pull_translations:
	find codejail_service/conf/locale -mindepth 1 -maxdepth 1 -type d -exec rm -r {} \;
	atlas pull $(OPENEDX_ATLAS_ARGS) translations/codejail-service/codejail_service/conf/locale:codejail_service/conf/locale
	python manage.py compilemessages

	@echo "Translations have been pulled via Atlas and compiled."
endif

detect_changed_source_translations: ## check if translation files are up-to-date
	cd codejail_service && i18n_tool changed

validate_translations: fake_translations detect_changed_source_translations ## install fake translations and check if translation files are up-to-date

selfcheck: ## check that the Makefile is well-formed
	@echo "The Makefile is well-formed."

install_transifex_client: ## Install the Transifex client
	# Installing client will skip CHANGELOG and LICENSE files from git changes
	# so remind the user to commit the change first before installing client.
	git diff -s --exit-code HEAD || { echo "Please commit changes first."; exit 1; }
	curl -o- https://raw.githubusercontent.com/transifex/cli/master/install.sh | bash
	git checkout -- LICENSE README.md ## overwritten by Transifex installer
