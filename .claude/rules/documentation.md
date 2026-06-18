# Documentation rule (project)

**ALWAYS use the Doc Beautifier for all documentation in this repo.**

Whenever you create or substantially edit any Markdown in this codebase
(`README.md`, everything under `docs/`, `data/README.md`, service `README.md`s,
`infra/azure/README.md`, the Databricks docs, etc.), run it through the
**`doc-beautifier`** skill so docs are visually rich and consistent:

- icons/emoji section markers, badges where useful;
- **mermaid** diagrams for flows/architecture/sequences;
- tables for comparisons and structured data;
- callouts/admonitions (`>` blockquotes) for notes/warnings;
- a table of contents for long docs;
- consistent headings, spacing, and link hygiene.

Also keep the substance correct: documentation must reflect the actual codebase,
architecture, and deployment state, and must carry the synthetic-data / disclaimer
notice where relevant (see `docs/DISCLAIMER.md`).

Do **not** ship doc changes that haven't been beautified.
