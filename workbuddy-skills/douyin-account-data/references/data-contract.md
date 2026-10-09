# Workbench Douyin data contract

The stable entry point is:

```text
<Vault>/30_self_media/douyin/current.json
```

The collector must populate the data required by the Workbench Douyin pages:

- complete public work list and current cumulative work metrics;
- monthly work-performance aggregation;
- content-line, format, and content-role distributions; user configuration takes precedence and missing classifications are explicitly published as `未分类` rather than guessed from private strategy;
- account daily content and follower series;
- account overview and content overview;
- collection list and collection metrics;
- per-work lifecycle history;
- per-work deep details when the Creator Center exposes them, including hourly views, follower changes, completion/retention/bounce curves, traffic sources, search terms, geography, interests, audience hot words, and comment keywords;
- source coverage, quality flags, capture time, and demo/live mode markers.

The stable directory also contains auditable projections:

```text
README.md
current.json
account-daily.csv
works.csv
work-history.csv
work-details.json
collections.csv
analysis.json
last-run.json
```

`current.json` is replaced only after the entire collection and validation cycle succeeds. Failed or partial runs may update only an existing `last-run.json`; they must not replace the last valid Workbench data.

All official Excel files, page snapshots, inventory CSV files, and analysis intermediates remain in the system temporary directory and are deleted at the end of the run.
