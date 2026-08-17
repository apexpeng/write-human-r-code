# write-human-r-code

An AI coding guideline for writing maintainable, reproducible, human-readable R code.

## Overview

AI can generate R code quickly, but generated scripts often suffer from unclear structure, duplicated logic, poor naming, and hidden assumptions.

`write-human-r-code` helps AI generate R scripts that follow real scientific programming practices.

## Core Goal

> Write R code that another researcher can understand, modify, and reuse.

## Principles

### Human-readable first

Prefer:

- clear object names;
- meaningful comments;
- explicit workflows.

Avoid:

- unnecessary abstraction;
- unreadable one-line tricks;
- excessive engineering patterns.

### Scientific reproducibility

Generated code should clearly separate:

```text
Input data
    ↓
Data preparation
    ↓
Statistical analysis
    ↓
Visualization
    ↓
Output
```

### Preserve scientific meaning

AI should not silently change:

- statistical methods;
- sample definitions;
- biological interpretation.

## Suitable For

- ecology;
- microbiome research;
- transcriptomics;
- metabolomics;
- environmental science.

## Philosophy

Good scientific code is not only executable.

It is explainable, reproducible, and maintainable.
