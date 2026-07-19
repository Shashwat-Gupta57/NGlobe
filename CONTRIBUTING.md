# Contributing to NGlobe

Thank you for your interest in contributing to NGlobe! We welcome contributions of all kinds: bug reports, feature requests, documentation improvements, and code contributions.

## Getting Started

1. **Fork the repository** and clone it locally.
2. **Install dependencies**:
   ```bash
   pip install -e .[dev]
   ```
3. **Build the frontend**:
   ```bash
   cd frontend
   npm install
   npm run build
   ```

## Development Workflow

- Backend code is located in `src/nglobe/`. We use FastAPI and mitmproxy.
- Frontend code is located in `frontend/`. We use React, MapLibre, Deck.gl, and Zustand.

When making code changes:
- Write clear, concise commit messages.
- Ensure your code follows the existing style (we use `ruff` for Python and `eslint`/`prettier` for TypeScript).
- Run tests before submitting a Pull Request.

## Submitting a Pull Request

1. Create a new branch for your feature or bugfix.
2. Ensure your PR description clearly explains the problem you are solving and the proposed solution.
3. Reference any related issues (e.g., "Fixes #123").

Thank you for helping make NGlobe better!
