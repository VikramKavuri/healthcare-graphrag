# Source data

Synthetic Healthcare GraphRAG dataset. **All records are fabricated for
demonstration purposes — do not use for clinical decisions.**

These Excel tables are the source of truth. They are converted into the runtime
snapshot `graphrag/dataset.json` by:

```bash
python scripts/prepare_data.py
```

The runtime application loads only the generated JSON snapshot, so pandas and
openpyxl are required for data preparation but not at serving time.

`data_dictionary.csv` / `data_dictionary.xlsx` describe every table and column.
