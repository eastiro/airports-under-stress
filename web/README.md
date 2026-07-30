# Web application

This directory contains the bilingual interactive frontend for Airports Under Stress.

```bash
npm ci
npm run dev
```

Useful checks:

```bash
npm run lint
npm run build
npm run test:ssr
```

The application reads versioned JSON snapshots from `app/`. Those snapshots are intentionally committed so the website can run without downloading the full BTS and weather datasets. Scientific source generation lives in the repository-level `scripts/` directory.
