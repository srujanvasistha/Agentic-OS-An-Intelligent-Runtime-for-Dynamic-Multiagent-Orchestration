.PHONY: experiments test day5 day5-mock graphs graphs-cdf web-build

experiments:
	python experiments/run_experiments.py

test:
	AGENTOS_LLM_BACKEND=mock python -m pytest backend/tests -v

day5:
	python experiments/run_day5_real_qwen.py

day5-mock:
	python experiments/run_day5_real_qwen.py --backend mock

graphs:
	python scripts/make_graphs.py

graphs-cdf:
	python scripts/make_graphs.py --cdf

web-build:
	cd frontend && npm run build
