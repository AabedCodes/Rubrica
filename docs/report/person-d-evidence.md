# Person D verification evidence

| Control | Implementation | Evidence |
| --- | --- | --- |
| C03, C24 | `backend/retrieval/search.py` searches inside the scoped database transaction. The grading path reads published course material. The chat path can also read blog chunks and labels their origin and trust. | PostgreSQL retrieval tests cover cross-course exclusion, publication status, blog separation and the result limit. |
| C04 | The worker matches uploaded content to the stored digest and copies course, version, title and visibility from the material record. | The indexing regression test checks digest mismatch, repeat processing and pending chunk visibility. |
| C06 | `backend/fetcher/url_policy.py` validates a single URL and resolves a set of addresses that the transport can pin. | Unit tests check mixed public and private DNS records and reject unsupported schemes, credentials and ports. The proxy transport and redirect checks remain open. |
| C07, C08, C09 | The existing output helpers remove active Markdown images and raw HTML, generate a fixed grade email, and protect formula-prefixed CSV cells. | Sink tests exercise image, HTML, recipient, header and CSV behavior. Application-route and Mailpit delivery evidence remain open. |
| C15 | `aibom/models.lock` pins the BAAI embedding model, its safetensors weights and tokenizer files. The embedding image verifies file hashes at build time and before loading. | The checksum regression rejects a synthetic one-byte modification. |
| C31 | Database roles and forced RLS protect grades, submissions, keys, materials and job records. | PostgreSQL tests cover course and grading-run scope, released feedback, audit writes, queue leasing and the parsed-submission update. |

The demo dataset is synthetic and documented in [seed-data.md](../seed-data.md).
The T-03 and T-20 live results still depend on the real provider and the
verification framework. The upload, grading, release, and export walkthrough
requires the corresponding authenticated service routes.
