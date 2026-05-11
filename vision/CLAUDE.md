# Vision Subsystem Guide

## Scope

Vision, image, and visual intelligence systems only.

## Includes

- image ingestion
- visual analysis
- screenshots
- UI screenshots
- property images
- design audits
- image metadata

## Rules

- Do not mix vision context with backend runtime unless required.
- Do not mutate operational state from vision output without approval.
- Preserve source traceability.
- Preserve confidence metadata.

## Do Not Load Unless Required

- workflow runtime
- realtime runtime
- AI orchestration
- unrelated frontend systems

## Validation

Vision changes require:
- relevant image pipeline tests
- schema validation
- source/metadata checks