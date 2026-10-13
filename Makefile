# This repo is the index, the working instructions, the cq wrapper and the
# portfolio generator -- the things that sit above the individual projects.
#
# The suite lives under .portfolio/t/ because that is what it tests. commitq
# discovers a suite by looking for a Makefile `test:` target, then t/test_*.py,
# then t/run.sh; without this target it finds nothing here and reports the repo
# as ungateable, which is exactly what it did when the test moved.
# The audit runs first because it takes four seconds and the suite below takes
# about fifteen minutes. Every check in it exists because the thing it checks
# for actually happened and nothing caught it, so finding out before the long
# run is the whole point.
test:
	@python3 .portfolio/audit.py
	@python3 .portfolio/t/test_audit.py
	@python3 .portfolio/t/test_portfolio.py

# The clean-clone check: every repository cloned alone, with no siblings, and
# `make test` run there. It is how gitobj's suite was found to require eight
# named neighbours and wasmi/hist/build.py to be pointed at an absolute path.
audit-deep:
	@python3 .portfolio/audit.py --deep

portfolio:
	@python3 .portfolio/extract.py > .portfolio/repos.json.new && \
	 mv .portfolio/repos.json.new .portfolio/repos.json
	@cd .portfolio && ./render.sh

.PHONY: test portfolio audit-deep
