# Performance evidence for v0.2.27

See `docs/PERFORMANCE-v0.2.27.md` for methods, interpretation and tables.
All trials were serial, separate from tests and profiling. Original input bytes
were preserved. Each batch includes raw JSONL and environment/input hashes.

- `starter-23-vs-26`: 148 records comparing the starter and previous release.
- `interim-26-vs-27`: 147 records from the first optimization pass. Its 70 audio
  records feed the final audio table; audio/SID/sequencer Python files match the
  delivered source exactly. One interim GUI record is absent (candidate Info,
  scopes off, 1280x900, repetition 4); the final UI batch supersedes these GUI
  results. The incomplete interim data is retained without fabricated values.
- `interim-buttons`: 40 early bank-button drawing measurements, retained as
  supporting evidence; final tables use the repeated final UI batch instead.
- `interim-live512-repeat`: four follow-up trials. Scheduling lateness occurred
  in both releases, with zero gaps/missing frames. All results are retained.
- `final-ui-and-live`: 144 records, including 135 GUI and nine live measurements.
  Channel recording and centered list layout are included. Two missing GUI
  records were completed with fresh trials, annotated in the records and in
  `completion-notes.json`; existing results were never replaced or discarded.
- `final-navigation`: 20 additional scrolling trials after the final sample
  mouse-wheel input handler, using the delivered runtime. Drawing/audio/recording
  code is unchanged from the preceding final batch.

`runtime-sha256.json` fingerprints the delivered Python runtime. The final
navigation snapshot was checked byte-for-byte against these files. The prior
final snapshot differs only in the two-line sample mouse-wheel event branch.
`profile-*.txt` contains separate v0.2.26 profiles with local paths removed.
No input-song copies or private machine/configuration files are included here.
