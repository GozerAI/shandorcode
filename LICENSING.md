# Commercial Licensing — ShandorCode

This project is dual-licensed:

- **AGPL-3.0** — Free for open-source use with copyleft obligations
- **Commercial License** — Proprietary use without AGPL requirements

## Tiers

| Feature | Community (Free) | Pro ($149/mo) | Enterprise ($499/mo) |
|---------|:---:|:---:|:---:|
| Code analysis & entity graph | Yes | Yes | Yes |
| Basic metrics (files, LOC, entities) | Yes | Yes | Yes |
| Analysis history | Yes | Yes | Yes |
| Detailed metrics & complexity | — | Yes | Yes |
| AI insights & semantic search | — | Yes | Yes |
| Boundary validation | — | — | Yes |
| Real-time WebSocket updates | — | — | Yes |
| Fleet-wide code analysis | — | — | Yes |
| Support SLA | Community | 48h email | 4h priority |

## Getting a License

Visit **https://gozerai.com/pricing** or contact sales@gozerai.com.

```bash
export SHANDORCODE_LICENSE_KEY="your-key-here"
export SHANDORCODE_SERVER="https://api.gozerai.com"
```

## Feature Flags

| Flag | Tier |
|------|------|
| `std.shandorcode.metrics` | Pro |
| `std.shandorcode.ai_insights` | Enterprise |
| `std.shandorcode.boundaries` | Enterprise |
