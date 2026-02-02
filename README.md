# Moltbot

Lightweight AI assistant with Moltbook integration.

## Quick start

1. Create and activate a virtualenv:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the bot:

   ```bash
   python moltbot.py
   ```

4. Run tests locally:

   ```bash
   pytest -q
   ```

## Docker

Build and run:

```bash
make build
docker run --env MOLTBOOK_API_KEY="$MOLTBOOK_API_KEY" -it moltbot:latest
```

## Notes

- The GitHub Actions workflow `CI` runs `pytest` on every push and PR to `main`.
- Set `MOLTBOOK_API_KEY` environment variable before enabling Moltbook features.
