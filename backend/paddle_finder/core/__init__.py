"""The recommendation engine: pure Python, no third-party dependencies.

Modules:
    config:        Metric definitions, the ``Level`` enum and constants.
    models:        Data classes (Paddle, MetricStats, Preference, Filters, ScoredPaddle, Preset).
    summary_stats: Percentiles, per-metric statistics and counts.
    catalog:       ``PaddleCatalog``: paddles plus pre-computed stats and indexes.
    filters:       Hard filters (budget, approval, shape...) and name search.
    scoring:       Similarity scoring, ranking and "similar paddles".
    presets:       Ready-made play-style profiles.
"""
