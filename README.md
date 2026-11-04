# jp-meeting-extraction-service

**Status: In progress, started 2026-11-04.** [日本語](README.ja.md)

Live service that turns Japanese business meeting notes into structured CRM fields, with an automated evaluation and prompt-injection gate in CI.

Core (evaluation and defences): https://github.com/Retro099/jp-meeting-to-crm-fields
This repo is the service part (live deployment with CI gate) of the same project.

## Overview
## Architecture
See [docs/architecture.md](docs/architecture.md).
## Evaluation and CI gate
See [eval/README.md](eval/README.md) and [PLAN.md](PLAN.md).
## Security / threat model
See [docs/threat-model.md](docs/threat-model.md).
## Known limitations
See [PLAN.md](PLAN.md).
## License
MIT
