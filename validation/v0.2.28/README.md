# v0.2.28 version-only validation

- Baseline: revised v0.2.27, commit `236350b`.
- Only runtime change: `sidpulse/__init__.py` version constant, 0.2.27 to 0.2.28.
- `version-tests.*`: 15 passing version-dependent tests.
- `results.jsonl`: 24 serial matched GUI/audio timing records, three trials.
- `environment.json`: input hash, dependencies, workload and affinity.
- `runtime-sha256.json`: delivered runtime identity.

Complete pre-bump 1,375-test, native PCM, live playback and bundled-example
export records remain under `validation/v0.2.27/inline-revision/`.
