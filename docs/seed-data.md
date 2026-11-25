# Synthetic seed data

Run `make up`, then `make seed` to load two courses, two instructors, 20
students and their enrollments. The fixtures also include four published
assignments, eight rubric criteria and approved keys, 16 submissions,
material records, and blog discussions. Everything is generated or written
for Rubrica. The chapter is team-written and represents a third-party source.

Faker (US English) supplies the names from a fixed seed. All addresses are
fixture identifiers under `example.edu`. Stable UUIDs identify rows and allow
the same command to run again without duplicating records. Answer keys contain
unique `KEYMARK` markers and stay in the answer-key table. The material text
fixtures are under `seed/materials/`. Their content hashes are stored with
the material records. D4 and D5 hook those source fixtures into the ingestion
and retrieval workflow.

The synthetic accounts use the local demo password declared in
`seed/generate.py`. Argon2id hashes use stable per-fixture salts. Person E's
identity work defines how to provision instructor second factors for the demo.

## Security fixtures

Run `make seed CANARIES=1` to add marked blog comments, an appeal with a
released grade, a third-party material record, two submissions with reserved
example citations, a pre-extracted PDF submission, and a formula-prefix display name. The fixture definitions
live in `seed/canaries/`. A later basic seed keeps any canaries already loaded.

The T03 chapter text will become searchable when ingestion and retrieval are
connected. The T04 PDF and T09 image reply fixtures are ready for the parser and FakeLLM
workflows. The T04 seed row represents the parser output until the upload
workflow can attach the PDF. The T07 and T21 pages still need a hosted fixture.
