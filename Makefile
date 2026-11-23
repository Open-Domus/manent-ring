.PHONY: all test fit cad drawings power schematic board clean

all: schematic board test fit drawings power cad

test:
	uv run pytest -q

fit:
	uv run python -m mechanical.manent_mech.checks

drawings:
	uv run python -m mechanical.manent_mech.drawings

cad:
	uv run python -m mechanical.manent_mech.cad

power:
	uv run python tools/power_budget.py > /dev/null
	uv run python tools/space_budget.py

schematic:
	uv run python -m electrical.gen
	tools/kicad.sh
	uv run python -m electrical.gen.checks

board:
	uv run python -m electrical.gen.board
	tools/kicad.sh board

clean:
	rm -f mechanical/out/*.step mechanical/out/*.svg mechanical/out/fit-report.json
