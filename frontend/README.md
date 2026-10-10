# Clipseek frontend

React + TypeScript + Vite client for the Clipseek video-search API.

See the [project README](../README.md) for architecture, backend setup, benchmarks, and limitations.

```sh
npm ci
npm run dev
```

Copy `.env.example` to `.env` and set `VITE_API_URL` if the backend runs somewhere other than `http://127.0.0.1:8001`.

```sh
npm test
npm run build
npm run lint
```

Source is organized into `app/` (routing), `features/` (auth, library, search, marketing, legal), `shared/` (API client and UI primitives), and `styles/`.

Authentication is enabled by default. The API client refreshes expired access tokens and fetches clips through authenticated requests. Configure your static host to serve `index.html` for client-side routes such as `/app` and `/login`.
