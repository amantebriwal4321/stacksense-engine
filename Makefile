.PHONY: run test scenarios catalog package

run:
	python -m stacksense serve

test:
	python -m unittest discover -s tests -v

scenarios:
	python -m stacksense recommend scenarios/public.json outputs

catalog:
	python -m stacksense catalog knowledge/CATALOG.md

package:
	bash scripts/package_submission.sh
