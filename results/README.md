# Results

This directory is reserved for frozen run artifacts and reports. The repository intentionally does not claim frontier-model findings without executed, clean, repeated trials and transcript review. Generate an offline smoke run with:

```bash
python scripts/run_eval.py --runner mock --trials 3 --output results/mock.json
python scripts/report.py results/mock.json --markdown results/mock.md
```

For a submission report, preserve model name/version, settings, trial counts, cost/runtime telemetry, failure transcripts, and limitations. Do not use the mock run as evidence about real model capability.
