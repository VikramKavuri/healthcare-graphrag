# Contributing to Healthcare GraphRAG

Thanks for your interest in contributing! This document explains how to set up
the project, the quality bar, and how to propose changes.

## Development setup

```bash
git clone https://github.com/VikramKavuri/healthcare-graphrag.git
cd healthcare-graphrag

python -m venv .venv
# Windows: .venv\Scripts\activate   |   macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt

uvicorn graphrag.app:app --reload   # http://127.0.0.1:8000
```

## Running the checks

The same checks run in CI on every push and pull request:

```bash
ruff check .     # lint
pytest           # tests
```

Please make sure both pass before opening a pull request.

## Coding standards

- **Python 3.10+** with type hints and concise docstrings on public functions.
- **Ruff** is the linter/formatter of record (configuration in `pyproject.toml`).
- **Keep the serverless runtime lean.** Data libraries (pandas, scikit-learn,
  numpy) belong in build-time scripts only — the deployed function must stay on
  the standard library plus the few packages in `requirements.txt`. If you add a
  runtime dependency, justify it in the PR.
- **Add or update tests** for any behavior change. Engine logic goes in
  `tests/test_engine.py`; API behavior in `tests/test_api.py`.

## Regenerating the dataset

The runtime loads the committed `graphrag/dataset.json`. If you change the source
spreadsheets in `data/`, regenerate the snapshot and commit it:

```bash
python scripts/prepare_data.py
```

## Pull request process

1. Create a topic branch from `main`.
2. Make focused changes; keep unrelated refactors out of the PR.
3. Ensure `ruff check .` and `pytest` pass locally.
4. Open a pull request describing **what** changed and **why**.

## Data &amp; safety

All bundled data is **synthetic**. Never commit secrets, API keys, or real
protected health information (PHI). The API key is read from the environment only
(`.env` is git-ignored).

## License

By contributing, you agree that your contributions are licensed under the
project's [MIT License](LICENSE).
