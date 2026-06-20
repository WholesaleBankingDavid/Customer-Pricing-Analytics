# Data Folder

This folder contains the existing project workbook `data.xlsx`.

The MVP code treats the workbook defensively:

- sheet names are discovered dynamically
- workbook schemas are profiled before use
- no loader assumes that `data.xlsx` already follows the target data model
- examples and tests use synthetic data only

Do not commit real customer names, confidential client identifiers, or live negotiation notes in new sample files.

The current workbook includes historical fields that may not be suitable for the target MVP, including competitor-related columns. Competitor data must not be used as a pricing guidance feature.
