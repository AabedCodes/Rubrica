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


## Material jobs

The ingestion service leases due jobs of kind `parse_material` from PostgreSQL.
The upload writer places a UUID-named file in `/data/uploads` and enqueues a job
with status `queued` and payload fields `upload_id`, `material_id`, `course_id`,
and `content_type`. These values come from the authenticated upload path. The
worker uses the stored material hash, version, course, status and title when
indexing. Chunk IDs are stable across retries. The initial chunk size is 300
words with 30 words of overlap, and the encoder truncates at 512 model tokens.

A `parse_submission` job uses `submission_id` instead of `material_id`. It
writes extracted text only when the stored upload hash and course match.
Submission text stays out of the retrieval index.
