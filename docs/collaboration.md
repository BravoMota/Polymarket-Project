# Collaboration Guide

## Branch Strategy

- Protect `main`.
- Use short-lived feature branches: `feat/*`, `fix/*`, `docs/*`.
- Merge through PR only.

## PR Checklist

- tests pass (`pytest`)
- lint passes (`ruff check .`)
- no secrets in code or history
- docs updated for public interfaces
- risk defaults still safe (`paper_mode=true`)

## Issues

- Use `strategy` issue template for new signal ideas.
- Use `postmortem` template for paper-trading failures.
