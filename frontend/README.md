# ProDuckt Frontend

Modern React frontend for ProDuckt - AI-powered product discovery platform.

## Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Development

The development server runs on `http://localhost:5173` by default.

Make sure the backend API is running on `http://localhost:8000`.

## Environment Variables

**Important:** The project uses a single `.env` file at the **project root** (not in the frontend directory).

The frontend will automatically load environment variables from the root `.env` file. The `VITE_API_BASE_URL` variable is already configured there.

## Project Structure

- `/src/api` - API client and endpoint definitions
- `/src/components` - Reusable React components
- `/src/pages` - Page components
- `/src/hooks` - Custom React hooks
- `/src/context` - React Context providers
- `/src/utils` - Utility functions

## Key Features

1. **Authentication** - Session-based login/register
2. **Initiative Management** - CRUD operations for initiatives
3. **Question Answering** - Interactive Q&A interface
4. **MRD Generation** - AI-powered document creation
5. **Scoring** - RICE and FDV score visualization
6. **Context Management** - Organizational context configuration

## Tech Stack

- React 18
- Vite
- React Router
- TanStack Query
- Axios
- Lucide React (icons)
- React Markdown

## Architecture

See [FRONTEND_GUIDE.md](./FRONTEND_GUIDE.md) for detailed architecture documentation.

## Next Steps

1. Implement authentication pages (Login/Register)
2. Create dashboard layout
3. Build initiative list and detail pages
4. Implement question answering interface
5. Add MRD viewer component
6. Create scoring visualization
7. Add context management UI

## Contributing

1. Follow React best practices
2. Use functional components and hooks
3. Implement proper error handling
4. Add loading states
5. Write clean, readable code
