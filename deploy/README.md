# VPS deployment preparation

The prepared unit is `stopnulis.service`. It is intentionally not installed, enabled, started, or copied to a VPS by local development work.

Expected layout:

```text
/home/stopnulis/app/
  .venv/bin/python
  main.py
  .env
```

The service runs as the unprivileged `stopnulis` user and group, uses the application directory as its working directory, loads `BOT_TOKEN` and other settings from `.env`, restarts after unexpected failures, and uses a private temporary directory. Install/start actions remain a separate, explicitly authorized deployment step.
