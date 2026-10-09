# This repo is the index, the working instructions, the cq wrapper and the
# portfolio generator -- the things that sit above the individual projects.
#
# The suite lives under .portfolio/t/ because that is what it tests. commitq
# discovers a suite by looking for a Makefile `test:` target, then t/test_*.py,
# then t/run.sh; without this target it finds nothing here and reports the repo
# as ungateable, which is exactly what it did when the test moved.
test:
	@python3 .portfolio/t/test_portfolio.py

portfolio:
	@python3 .portfolio/extract.py > .portfolio/repos.json.new && \
	 mv .portfolio/repos.json.new .portfolio/repos.json
	@cd .portfolio && ./render.sh

.PHONY: test portfolio
