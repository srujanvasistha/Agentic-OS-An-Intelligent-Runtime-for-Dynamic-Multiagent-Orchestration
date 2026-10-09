PY=python3

.PHONY: all suite test attacks benign bench summary demo legacy sandbox qwen

all: suite test attacks benign bench summary

suite:
	$(PY) suite/build_suite.py

test:
	$(PY) -m pytest -q

attacks:
	$(PY) run_attacks.py --llm scripted

legacy:
	$(PY) run_attacks.py --llm scripted --legacy-policy

benign:
	$(PY) run_benign.py

bench:
	$(PY) bench_overhead.py

summary:
	$(PY) summarize.py

demo:
	$(PY) demo.py

sandbox:
	$(PY) sandbox_check.py

qwen:
	$(PY) run_attacks.py --llm qwen --configs off,caps+taint --only A01,A02,A08,A09,A11,A14,A16,A19,A20
