# DharmaCodex Internal Runtime v1.1.6-container.1

Deployable private calculation runtime for the existing `dharmacodex.org` project.

- Python/FastAPI container using real `pyswisseph` and Python `sqlite3`.
- Immutable canonical master loaded through an AST adapter; Colab top-level code is never executed.
- Private R2 asset bridge with SHA-256 startup verification.
- Dynamic calculations and canonical renderers for Astrology, Human Design, Numerology, and Destiny Matrix.
- Existing Pages UI and `/internal/api/reading` gateway through a Service Binding.

Local tests use the checked-in private test asset directory and do not call R2 or external geocoding.

