# Archive and baseline

On November 7, 2026, the owner confirmed that 4.5.0 works well: AF, photos,
aperture-dial control and shutdown. It becomes the active working baseline.
Earlier failed or diagnostic firmware, scripts, research models and detailed
campaign records were removed from the active project.

The annotated Git tag `archive/pre-4.5-baseline` points to the complete old
tree at commit `9a6905c`. All prior image bytes, manifests and original test
results remain there. This preserves recovery and research provenance without
shipping failed firmware in the daily app. Old app journals retain read-only
validation via code digests; no retired installation command remains.

```sh
git show archive/pre-4.5-baseline:README.md
# To inspect the full historical tree independently:
git archive archive/pre-4.5-baseline | tar -x -C EXISTING_EMPTY_DIRECTORY
```

The active tree retains 4.4.0 as a known fallback, 4.5.0 as the working baseline,
and separately prepared 4.6.0. Original stock 1.8.0 recovery and its encrypted
same-unit archive remain in `firmware/recovery/stock-1.8.0/`; the key stays outside
Git. Private backups and scratch data are untouched. No hardware operation is
part of the restructure or preview workflow.
