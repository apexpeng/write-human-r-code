---
name: write-human-r-code
description: Write, refactor, or review concise, scientifically transparent, human-readable R code for data analysis and plotting. Use when creating or materially revising R scripts, ggplot2 figures, independent manuscript panels, heatmaps, statistical workflows, microbiome or transcriptome analyses, or when reviewing possible AI-style verbosity, excessive logging or error recovery, manual geom stacking, hidden scientific decisions, stale data flow, copied workflows, or monolithic scripts.
---

# Write Human-Style R Code

Prioritize, in order: scientific correctness, traceable data flow, independent analysis units, readable self-contained scripts, project conventions, then reduction of repetition and line count. Simplify only when the result remains scientifically explicit.

## Start every task

1. Read project instructions and inspect nearby R scripts, manifests, inputs, outputs, and package conventions.
2. State the scientific unit being changed: authoritative input, transformation, statistic, comparison direction, and output.
3. Identify project rules for independent panels, treatment-specific analyses, local palettes, shared helpers, and reproducible execution. Project rules override generic DRY preferences.
4. Run this skill's `scripts/audit_r_style.py <path>` for an existing script or directory. Resolve it relative to this `SKILL.md`.
5. Also use `r-data-lineage-plotting` when the task reads, creates, migrates, or reuses data files or analysis objects. Pure label, font, theme, or legend edits do not require it.
6. Decide whether the target is one coherent analysis module or a shared compute stage with several downstream consumers. Do not assume a generic preparation stage exists.

## When to pair with `r-data-lineage-plotting`

- **Only this skill**: pure script style and structure work - labels, fonts, themes, legends, refactoring inside one script, reviewing verbosity, naming, or logging.
- **Only `r-data-lineage-plotting`**: directory reorganization, file migration, data-flow classification, rerun gates, stale-result diagnosis.
- **Both skills**: any task that creates, reads, migrates, or reuses data files or analysis objects while also touching script structure - e.g. adding a panel that reads a new computed table, or splitting a script into a generator plus consumers.

## Preserve scientific visibility

- Keep statistical thresholds, bootstrap counts, seeds, sample-inclusion rules, contrast direction, network parameters, and data versions in one authoritative location per analysis unit.
- Pin package versions with `renv`/`renv.lock` where the project uses it; otherwise record `sessionInfo()` output for the packages that affect results.
- Allow panel-local dimensions, colours, legend positions, label offsets, and one-off axis ranges to remain explicit in a self-contained panel script when project conventions prefer that.
- Give each distinct analysis unit one authoritative object. CK and SC networks may each have their own object; derive comparisons from both without merging them into shared mutable state.
- Put curated gene mappings, mechanism-layout coordinates, manual labels, and pathway claims in versioned, auditable inputs when they are substantial. Do not disguise curation as an ordinary function parameter.
- Compute P values, FDR, AUC, sample sizes, significance symbols, validation counts, and plot annotations from the corresponding authoritative object in the same run.
- Keep `/data` free of reproducible derived files, separate intermediates from final tables, and do not use a final-result directory as a downstream computation bus. Keep README and manifests aligned with real files.
- For an ordinary panel, prefer one readable top-level script that shows configure, read, validate, analysis-specific preparation, statistics, output, plot, and save. Reading, transforming, analysing, and plotting in one file is not mixed responsibility when all steps answer one coherent scientific question.
- Do not create generic `prepare_data.R`, `clean_data_final.R`, or `prepared_data.csv` layers merely to shorten plotting scripts. Preparation belongs to the analysis whose filtering, transformation, distance, model, or display semantics define it.
- Split preparation only when it is expensive or scientifically substantial and produces a formal object reused by multiple outputs in the same module. Give the object a generator, schema, parameter record, consumers, and invalidation rule.
- Make cross-module reads from `/output` exceptional and explicit. Convenience is not scientific justification; independent modules should normally return to authoritative inputs.

## Simplify conditionally

Consider `legendry::guide_axis_nested()`, `patchwork`, `ComplexHeatmap`, `ggrepel`, facets, guides, scales, or layout engines when they express the scientific structure more directly than manual drawing.

Before replacing a stable implementation, require all of the following:

- the package API exists in the installed version and works on the target platform;
- the replacement materially lowers maintenance or error risk;
- the output semantics and geometry remain unchanged;
- the change does not add unnecessary dependencies or obscure the current panel;
- the project is not in a release stage where changing plotting systems creates disproportionate regression risk.

Use `ComplexHeatmap` for genuinely annotated or composite heatmaps, not every `geom_tile()` plot. Use `patchwork` for ordinary panel composition, not precision grob work that it cannot express. Keep manual coordinates for bespoke schematics, but externalize large layout tables.

## Treat repetition by risk, not appearance

- Keep independent top-level scripts when treatments require separate filtering, modelling, seeds, inputs, or outputs.
- Do not merge CK and SC merely because their code is textually similar. Check for unintended drift in thresholds, algorithms, candidate sets, and cross-treatment object reuse.
- Prefer independent entry scripts plus a few pure computation helpers when shared helpers improve consistency without hiding treatment-specific decisions.
- Allow small, stable repetition when it makes a manuscript panel independently readable and runnable.
- Refactor repetition when one scientific change must be synchronized manually in several places or when copies have already diverged unintentionally.
- Do not flag repeated HEX values, a short local theme, or explicit export dimensions by count alone. Flag inconsistent mappings or repeated definitions scattered within the same script.

## Keep control flow readable

- Use `message()` for a few meaningful milestones. Avoid decorative `cat()` banners and operation-by-operation narration.
- Use `tryCatch()` only when failure is expected and recovery is defined. Let scientific gate failures stop loudly.
- Validate each invariant at the nearest meaningful boundary. Repeat a critical input check in independent panel scripts when that preserves standalone auditability.
- Name objects by scientific role. Keep the visible flow: configure, read, validate, transform, analyse, plot, save.
- Split a script when it mixes distinct scientific responsibilities, not merely because it exceeds a line threshold or lacks functions.
- Judge responsibility by the scientific question, not by operation type. `read -> prepare -> test -> export -> plot` may be one responsibility; constructing a network and assembling unrelated manuscript panels usually is not.
- Do not create layers of helpers solely to reduce line count or satisfy a function-count metric.

## Apply both gates

### Simplification gate

1. Does an existing grammar or package express this block more directly?
2. Is repetition likely to drift or already inconsistent?
3. Would one scientific change require edits in multiple places?
4. Does logging explain decisions rather than narrate syntax?
5. Is an error recoverable, or should execution stop?

### Scientific transparency gate

1. Would abstraction hide treatment-specific filtering, thresholds, inputs, or contrast direction?
2. Would a reader need unnecessary cross-file navigation to understand the panel?
3. Would it introduce a new dependency, stale cache, hidden source call, or derived input?
4. Would it reduce the script's ability to run and validate independently?
5. Is repetition intentional for analysis independence or accidental copying?
6. Would the proposed helper or prepared table turn a DAG of independent analyses into an undocumented linear chain?
7. If an `/output` object crosses a module boundary, is that edge scientifically required, registered, and invalidated when its producer changes?

Refactor only when the proposed change passes both gates.

## Worked example

A self-contained panel script that keeps one scientific responsibility visible. Obtain `script_dir` robustly (e.g. from `commandArgs(trailingOnly = FALSE)` or `rstudioapi::getSourceEditorContext()`); never rely on `setwd()`.

```r
# panel: CK network degree distribution (Figure 3B)
project_dir <- normalizePath(file.path(script_dir, ".."), winslash = "/")
data_dir    <- file.path(project_dir, "data")
output_dir  <- file.path(project_dir, "output")

# authoritative inputs
meta  <- read.csv(file.path(data_dir, "metadata_ck.csv"), check.names = FALSE)
abund <- read.csv(file.path(data_dir, "abundance_ck.csv"), row.names = 1)
edges <- readRDS(file.path(output_dir, "ck_network", "edges.rds"))  # one authoritative network object
seed <- 42; threshold <- 0.65; contrast <- "CK vs SC"

stopifnot(identical(rownames(abund), meta$sample_id))  # sample-alignment gate

deg <- as.data.frame(table(edges$from))                # analysis-specific preparation
p   <- wilcox.test(deg$Freq ~ meta$group[match(deg$Var1, meta$sample_id)])$p.value
stopifnot(!is.na(p))

write.csv(deg, file.path(output_dir, "ck_network", "degree_distribution.csv"), row.names = FALSE)

ggplot(deg, aes(Freq)) +
  geom_histogram(bins = 30, fill = "grey70", colour = "white") +
  annotate("text", x = Inf, y = Inf, hjust = 1.1, vjust = 1.5,
           label = sprintf("p = %.3f", p)) +           # annotation computed in-run, never hardcoded
  labs(x = "degree", y = "count", title = "CK network degree distribution")
ggsave(file.path(project_dir, "result", "figs", "fig3b_ck_degree.pdf"), width = 4, height = 3)
```

The example shows configure -> read -> validate -> prepare -> statistics -> output -> plot -> save as one visible flow, with the annotation computed from the authoritative object in the same run.

## Validate

Run, in proportion to scope:

```powershell
Rscript -e "parse(file='path/to/script.R')"
Rscript -e "lintr::lint('path/to/script.R')"
python <skill-dir>/scripts/audit_r_style.py path/to/project-or-scripts
```

When data or analysis objects change, run the lineage audit and affected generator-consumer chain. Execute representative scripts when result regeneration is authorized. Compare statistics, sample order, factor levels, labels, figure dimensions, and source-data rows before and after refactoring.

For split compute/plot modules, validate the shared object's schema and all registered consumers. For self-contained panels, validate that the script rebuilds its statistics and annotations directly from authoritative inputs without relying on a stale prepared-data file.

Read [references/review-checklist.md](references/review-checklist.md) for review severity and acceptable exceptions.

## Report

Report in this order:

1. data lineage and directory responsibilities;
2. statistical, sample-alignment, and treatment-independence boundaries;
3. README and manifest consistency;
4. mixed scientific responsibilities within scripts;
5. repetition with demonstrated drift risk;
6. externalization of substantial curation or layout data;
7. conditional package or abstraction opportunities;
8. formatting and local verbosity.

Separate static observations, review signals, confirmed risks, parse validation, and full execution. Do not infer AI authorship from code style.
