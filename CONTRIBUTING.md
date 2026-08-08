# Contributing to Dotify

## Development setup

```bash
python -m pip install -e '.[dev]'
pytest -m 'not performance'
ruff check dotify tests
python -m build
```

Run performance budgets separately with `pytest -m performance`.

## Architecture boundaries

- Spotify HTTP details belong in `dotify/api/api.py`.
- Upstream response compatibility belongs in `dotify/api/adapter.py`.
- Reusable application orchestration belongs in `dotify/client.py`.
- CLI code translates command-line configuration into the reusable layer.
- Optional integrations implement a protocol in `dotify/plugins.py`.
- User-facing text belongs in `dotify/i18n.py`, not inline in new UI code.
- Transport progress is emitted from `dotify/downloader/progress.py` and rendered in `dotify/tui.py`.

When an upstream response changes, add or update an anonymized JSON fixture in
`tests/fixtures/api/` and adjust the adapter contract before changing media
parsers.

## Compatibility

Public API changes must follow `docs/PUBLIC_API.md`. New behavior should be
additive where possible; incompatible proposals require an API-major change
and a documented migration path.
