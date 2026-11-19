# SOCHI Ross Course Review

Render app for the Fall course-automation deliverables. Local ridge regression plus deterministic schedule reconciliation; four workbooks in, reviewable suggestions out. No API required.

Read [GUIDE.md](GUIDE.md) for the complete workflow, boundaries and sources. Run `python -m unittest discover -s tests -v`. Install `requirements.txt`, then run `python app.py` locally. Deploy with the production Gunicorn command in the guide.

The repository contains code, a trained coefficient model and a clearly synthetic demonstration. Original Drive exports, emails and raw schedules are excluded from Git. UMGPT_API_KEY is optional and must be kept in Render environment settings, never committed.
