# Terminal Aggregation Schema Compatibility Details

Research Logger schema v2 can serialize selected thread groups and candidate observations as strings or dictionaries. The offline terminal aggregation validator now normalizes both representations before copying observational metadata. No Production traversal or scoring behavior changes.
