# Isolated parser

The Compose parser watches its read-only `/data/parse-in` mount. The ingestion
worker publishes each input atomically as `<job-uuid>.pdf`, `<job-uuid>.txt`, or
`<job-uuid>.md`. UUIDs must use lowercase hexadecimal and hyphens. Give each
job one input file. The parser writes and atomically renames a JSON result to
`/data/parse-out/<job-uuid>.json`. A result already present for the job is reused.
The ingestion worker owns input and result cleanup after processing.

Success returns `text`, `pages`, and `has_text_layer`. Failures return a fixed
`error` code. `scanned_document` also includes the page count and
`has_text_layer: false`. Present that code as “Scanned documents are not
supported.” The parser applies file, page, extracted-text, memory, and execution
time limits. The Compose service has no network or mounted credentials.
