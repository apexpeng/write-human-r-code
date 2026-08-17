# Human-style scientific R review checklist

Judge scientific transparency and maintenance risk, not whether code resembles a preferred software architecture.

## Evidence classes

- **Observation**: objective count or location; no defect implied.
- **Review signal**: requires project context and human interpretation.
- **Risk**: evidence indicates possible effect on scientific results, data lineage, sample mapping, analysis independence, or formal outputs.

## Review signals

- Decorative `cat()` banners or line-by-line progress narration.
- Broad `tryCatch()` blocks that continue after an undefined scientific failure.
- Hand-stacked geoms or coordinates where the layout changes whenever data or labels change.
- A script that mixes several distinct responsibilities such as data preparation, modelling, network construction, unrelated figures, and final assembly.
- Similar paired scripts whose scientific thresholds or algorithms may have drifted.
- Large curated mappings or layout tables hidden inside executable code.
- Absolute project-root paths repeated across many scripts.
- Palettes, themes, or exporters defined inconsistently or scattered repeatedly within one script.

Script length, function count, number of HEX values, numeric coordinates, and textual similarity are observations only. They do not independently justify refactoring.

## Strong human-style signals

- A reader can see the authoritative input, scientific parameters, comparison direction, and output without tracing hidden dependencies.
- Each analysis unit has its own authoritative object and explicit validation gates.
- Treatment-specific analyses remain independent when scientifically required.
- Similar scripts are checked for algorithmic consistency without automatically sharing intermediate state.
- Statistical labels and source data derive from the same analysis objects.
- Manual curation is versioned and reviewable.
- The top-level flow follows configure, read, validate, transform, analyse, plot, save.
- A panel can remain self-contained when that is an explicit project requirement.
- Complexity protects a documented boundary rather than narrating routine operations.
- Ordinary analyses keep preparation beside the statistics and plot whose semantics define it.
- Shared compute stages exist because several named consumers need the same formal object, not because every project is forced through a generic prepare step.
- The dependency graph branches from authoritative inputs; cross-module edges are rare, scientifically justified, and invalidated explicitly.

## Conditional package choices

| Need | Consider | Do not force when |
|---|---|---|
| Nested categorical axes | `legendry::guide_axis_nested()` | current guide is stable or package support is uncertain |
| Multi-panel figures | `patchwork` | precise grob placement is required |
| Annotated composite heatmaps | `ComplexHeatmap` | a simple `geom_tile()` already expresses the panel |
| Label collision | `ggrepel` | fixed placement is a deliberate part of the design |
| Plot alignment | `patchwork` or `cowplot` | project constraints require another verified mechanism |

Verify package API, installed version, target platform, and output equivalence before replacement.

## Acceptable complexity and repetition

- Heterogeneous external file formats and compatibility workarounds.
- Explicit provenance, checksum, sample-alignment, and statistical-assumption gates.
- Independent treatment scripts required to avoid shared candidate sets or state.
- Standalone manuscript-panel scripts with short local themes, colours, dimensions, and input checks.
- Bespoke biological mechanism schematics.
- Versioned manual gene-to-pathway curation.
- Re-reading small formal inputs to avoid implicit caches.
- Retaining a stable plotting system during submission or revision.

Even when accepted, document why the complexity exists and isolate substantial curation or layout data from mechanics.

## Scientific risk checks

- Reproducible derived data written into `/data`.
- Intermediate objects or plot data written into final-result tables.
- Downstream computation reading from a final-result directory.
- `.RData`, `.Rhistory`, `load()`, `save.image()`, or `setwd()` introducing implicit state.
- README or manifest references to missing scripts or stale output formats.
- Multiple scripts writing the same output unexpectedly.
- Hardcoded P values, FDR, AUC, sample sizes, pass counts, or conclusion text.
- The same scientific threshold having unexplained different values across paired scripts.
- One treatment reading another treatment's intermediate object or candidate set.
- Cached objects without a generator, version, or invalidation rule.
- A generic prepared-data table silently reused by analyses with different filtering, transformation, normalization, or sample-inclusion requirements.
- An independent analysis consuming another module's convenient output without a documented scientific dependency.

## Severity

- **P1**: may change scientific conclusions, data lineage, sample correspondence, treatment independence, or formal outputs.
- **P2**: does not immediately alter results but creates substantial future drift or maintenance risk.
- **P3**: local verbosity, naming, formatting, comments, or logging noise.
- **Info**: heuristic observation needing project context; no required change by itself.

## Review order

1. Data lineage and directory roles.
2. Statistics, sample alignment, and treatment independence.
3. README, manifest, and real-file consistency.
4. Mixed scientific responsibilities.
5. Duplicated workflows with evidence of drift risk.
6. Curated data and layout externalization.
7. Conditional package or abstraction improvements.
8. `lintr`, `styler`, and formatting.

Always distinguish static review, parse success, representative execution, and full dependency-chain validation.
