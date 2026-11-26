# Citation fetcher

The grading agent calls `POST /internal/fetch` with JSON fields
`submission_id` and `url`. It supplies the shared grading service credential in
`X-Service-Auth` and the verified job’s UUIDs in `X-Run-Id` and `X-Course-Id`.
The fetcher checks the submission belongs to the run and course before any
external lookup. The snapshot insert applies the same scope in PostgreSQL.

The response contains `status` and `snapshot_id`. The grading agent can read
the snapshot under its run-scoped database role. Blocked and unavailable
results have no page text. The fetcher logs fixed reason codes and record IDs.

The DNS-only `web-dns` service resolves public hostnames from the proxy
network. It has no published ports or mounted credentials. The fetcher still
checks every returned address before using it.

The HTTPS transport sends a numeric address in CONNECT to `web-proxy:3128`.
TLS certificate verification and the origin Host header use the original
hostname. Every redirect starts again at URL and address validation. The
fetcher processes at most three redirects and two million body bytes. It
accepts plain text and HTML and discards script, style, template and noscript
content. HTTP URLs and HTTPS URLs on port 80 return a blocked snapshot because
the current proxy only permits CONNECT on port 443.

Hashed audit-chain events and the grading agent call site still need the shared
audit writer and grading integration. The second-stage proxy policy stays in
`deploy/proxy/web-proxy.conf`.
