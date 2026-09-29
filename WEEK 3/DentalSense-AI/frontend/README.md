# DentalSense AI Frontend

React/Vite client for the DentalSense AI feedback analytics platform.

The complete project overview, backend setup, AI methodology, privacy constraints, and API reference are documented in the [project README](../README.md).

## Local Development

The FastAPI backend must be available at `http://localhost:8000`.

```powershell
npm install
npm run dev
```

Open `http://localhost:5173`.

## Quality Checks

```powershell
npm run lint
npm run build
```

## Main Routes

| Route | Page |
| :--- | :--- |
| `/` | Analytics Dashboard |
| `/analyze` | Individual Feedback Analyzer |
| `/batch` | CSV Batch Analysis |
| `/explore` | Feedback Explorer |
| `/methodology` | Methodology, Privacy, and Limitations |

## Source Layout

```text
src/
├── pages/       # Route-level application views
├── services/    # Axios API client
├── assets/      # Local visual assets
├── App.jsx      # Navigation and route definitions
├── index.css    # Tailwind theme and global styles
└── main.jsx     # React entry point
```
