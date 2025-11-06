# ProDuckt Frontend Architecture Guide

## Overview

This document outlines the complete frontend architecture for ProDuckt, a React-based single-page application (SPA) that provides an intuitive interface for AI-powered product discovery.

## Tech Stack

- **React 18** - UI library
- **Vite** - Build tool and dev server
- **React Router** - Client-side routing
- **TanStack Query** - Server state management and caching
- **Axios** - HTTP client
- **Lucide React** - Icon library
- **React Markdown** - MRD rendering

## Project Structure

```
frontend/
├── src/
│   ├── api/              # API client and endpoints
│   │   ├── client.js     # Axios instance with interceptors
│   │   ├── auth.js       # Authentication endpoints
│   │   ├── initiatives.js # Initiative endpoints
│   │   ├── questions.js  # Question/answer endpoints
│   │   ├── mrd.js        # MRD endpoints
│   │   ├── scoring.js    # Scoring endpoints
│   │   └── context.js    # Context endpoints
│   │
│   ├── components/       # Reusable components
│   │   ├── common/       # Generic UI components
│   │   │   ├── Button.jsx
│   │   │   ├── Card.jsx
│   │   │   ├── Input.jsx
│   │   │   ├── Badge.jsx
│   │   │   ├── Modal.jsx
│   │   │   └── Spinner.jsx
│   │   │
│   │   ├── layout/       # Layout components
│   │   │   ├── Header.jsx
│   │   │   ├── Sidebar.jsx
│   │   │   └── Layout.jsx
│   │   │
│   │   └── features/     # Feature-specific components
│   │       ├── initiatives/
│   │       ├── questions/
│   │       ├── mrd/
│   │       ├── scoring/
│   │       └── context/
│   │
│   ├── pages/            # Page components
│   │   ├── Login.jsx
│   │   ├── Register.jsx
│   │   ├── Dashboard.jsx
│   │   ├── InitiativeList.jsx
│   │   ├── InitiativeDetail.jsx
│   │   ├── Questions.jsx
│   │   ├── MRDView.jsx
│   │   ├── Scoring.jsx
│   │   └── Settings.jsx
│   │
│   ├── hooks/            # Custom React hooks
│   │   ├── useAuth.js
│   │   ├── useInitiatives.js
│   │   ├── useQuestions.js
│   │   └── useMRD.js
│   │
│   ├── context/          # React Context providers
│   │   ├── AuthContext.jsx
│   │   └── ThemeContext.jsx
│   │
│   ├── utils/            # Utility functions
│   │   ├── formatting.js
│   │   ├── validation.js
│   │   └── storage.js
│   │
│   ├── App.jsx           # Main app component
│   ├── main.jsx          # Entry point
│   └── index.css         # Global styles
│
├── public/               # Static assets
├── package.json
└── vite.config.js
```

## Key Pages and Features

### 1. Authentication Pages

#### Login Page (`/login`)
- Email and password input
- Session-based authentication
- Remember me option
- Error handling for invalid credentials

#### Register Page (`/register`)
- Create new account
- Join existing organization or create new
- Form validation
- Success redirect to dashboard

### 2. Dashboard (`/dashboard`)

**Overview metrics:**
- Total initiatives (by status)
- Questions answered vs. unanswered
- MRDs generated
- Average RICE/FDV scores

**Quick actions:**
- Create new initiative
- View recent initiatives
- Access organizational context

### 3. Initiative Management

#### Initiative List (`/initiatives`)
- Filterable by status (Draft, In QA, Ready, etc.)
- Sortable by creation date, RICE score, FDV score
- Search by title
- Quick status badges
- Action buttons (edit, delete, generate questions)

#### Initiative Detail (`/initiatives/:id`)
**Tabs:**
1. **Overview**
   - Title, description, status
   - Readiness score
   - Created by, last updated
   - Quick actions (edit, delete)

2. **Questions** (`/initiatives/:id/questions`)
   - List of generated questions by category
   - Priority badges (P0, P1, P2)
   - Answer input forms
   - Progress tracker (X/Y answered)
   - "Generate Questions" button
   - "Regenerate Questions" button

3. **MRD** (`/initiatives/:id/mrd`)
   - Rendered Markdown view
   - Quality disclaimer banner
   - Metadata (version, word count, completeness)
   - "Generate MRD" button
   - "Download as Markdown" button
   - "Export to PDF" button (future)

4. **Scoring** (`/initiatives/:id/scoring`)
   - RICE score breakdown
     - Reach visualization
     - Impact chart
     - Confidence meter
     - Effort display
     - Final RICE score (large)
   - FDV score breakdown
     - Feasibility gauge
     - Desirability gauge
     - Viability gauge
     - Final FDV score
   - Reasoning display for each component
   - "Calculate Scores" button
   - Comparison chart (compare with other initiatives)

### 4. Question Answering Interface

**Features:**
- Category grouping (Product, Technical, Business_Dev, Operations, Financial)
- Priority filtering (show P0 only, etc.)
- Answer types:
  - Answered (with text)
  - Unknown (with reason)
  - Skipped (with reason)
- Save draft / Submit answer
- Progress tracker
- "Mark as complete" when all P0 answered

**UX Flow:**
1. View questions by category
2. Click to expand question
3. See rationale
4. Input answer or select Unknown/Skipped
5. Save answer
6. See progress update
7. Move to next question

### 5. MRD Viewer

**Features:**
- Full Markdown rendering
- Table of contents (auto-generated from headers)
- Quality disclaimer banner (color-coded by readiness)
- Metadata sidebar:
  - Version number
  - Word count
  - Completeness score
  - Readiness score
  - Generated date
  - Generated by
- Export actions:
  - Copy to clipboard
  - Download as .md
  - Export to PDF (future)

### 6. Scoring Visualization

**RICE Score Display:**
```
┌────────────────────────────────────┐
│  RICE Score: 20,000                │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│                                    │
│  Reach:       50,000 users         │
│  Impact:      2.0 (High)           │
│  Confidence:  80% (Medium)         │
│  Effort:      4.0 person-months    │
│                                    │
│  Reasoning:                        │
│  • Reach: 50K enterprise users...  │
│  • Impact: High impact on...       │
│  • Confidence: Based on...         │
│  • Effort: 4 PM estimated...       │
└────────────────────────────────────┘
```

**FDV Score Display:**
```
┌────────────────────────────────────┐
│  FDV Score: 8.0 / 10               │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│                                    │
│  Feasibility:   7/10  ███████░░░   │
│  Desirability:  9/10  █████████░   │
│  Viability:     8/10  ████████░░   │
│                                    │
│  Reasoning:                        │
│  • Feasibility: Moderate...        │
│  • Desirability: Strong demand...  │
│  • Viability: Good business...     │
└────────────────────────────────────┘
```

### 7. Context Management (`/settings/context`)

**Features:**
- View current organizational context
- Edit context fields:
  - Company mission
  - Strategic objectives
  - Target markets
  - Competitive landscape
  - Technical constraints
- Version history
- "Create New Version" action
- "Restore Previous Version"

### 8. Settings Page (`/settings`)

**Tabs:**
1. **Profile**
   - User info
   - Change password
   - Session management

2. **Organization**
   - Organization details
   - Member list
   - Invite users

3. **Context**
   - (See Context Management above)

4. **Preferences**
   - Theme (light/dark)
   - Notifications
   - Default views

## API Integration

### API Client Setup

```javascript
// src/api/client.js
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true, // For session cookies
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for auth
apiClient.interceptors.request.use(
  (config) => {
    // Add any auth headers if needed
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Redirect to login
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default apiClient;
```

### Example API Endpoints

```javascript
// src/api/initiatives.js
import apiClient from './client';

export const initiativesApi = {
  // List initiatives
  list: async (filters) => {
    const { data } = await apiClient.get('/api/initiatives', { params: filters });
    return data;
  },

  // Get single initiative
  get: async (id) => {
    const { data } = await apiClient.get(`/api/initiatives/${id}`);
    return data;
  },

  // Create initiative
  create: async (initiativeData) => {
    const { data } = await apiClient.post('/api/initiatives', initiativeData);
    return data;
  },

  // Update initiative
  update: async (id, initiativeData) => {
    const { data } = await apiClient.patch(`/api/initiatives/${id}`, initiativeData);
    return data;
  },

  // Delete initiative
  delete: async (id) => {
    await apiClient.delete(`/api/initiatives/${id}`);
  },

  // Update status
  updateStatus: async (id, status) => {
    const { data } = await apiClient.put(`/api/initiatives/${id}/status`, { status });
    return data;
  },
};
```

## State Management with TanStack Query

```javascript
// src/hooks/useInitiatives.js
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { initiativesApi } from '../api/initiatives';

export function useInitiatives(filters) {
  return useQuery({
    queryKey: ['initiatives', filters],
    queryFn: () => initiativesApi.list(filters),
  });
}

export function useInitiative(id) {
  return useQuery({
    queryKey: ['initiative', id],
    queryFn: () => initiativesApi.get(id),
    enabled: !!id,
  });
}

export function useCreateInitiative() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: initiativesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['initiatives'] });
    },
  });
}

export function useUpdateInitiative() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }) => initiativesApi.update(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['initiative', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['initiatives'] });
    },
  });
}
```

## UI Component Examples

### Button Component

```jsx
// src/components/common/Button.jsx
export function Button({ children, variant = 'primary', size = 'md', loading, disabled, onClick, ...props }) {
  const baseClasses = 'rounded-lg font-medium transition-colors focus:outline-none focus:ring-2';

  const variants = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500',
    secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300 focus:ring-gray-500',
    danger: 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500',
    ghost: 'bg-transparent hover:bg-gray-100 focus:ring-gray-500',
  };

  const sizes = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg',
  };

  return (
    <button
      className={`${baseClasses} ${variants[variant]} ${sizes[size]} ${(disabled || loading) && 'opacity-50 cursor-not-allowed'}`}
      disabled={disabled || loading}
      onClick={onClick}
      {...props}
    >
      {loading ? 'Loading...' : children}
    </button>
  );
}
```

### Card Component

```jsx
// src/components/common/Card.jsx
export function Card({ title, children, action }) {
  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      {title && (
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">{title}</h3>
          {action && <div>{action}</div>}
        </div>
      )}
      {children}
    </div>
  );
}
```

## Routing Structure

```jsx
// src/App.jsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './context/AuthContext';
import Layout from './components/layout/Layout';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import InitiativeList from './pages/InitiativeList';
import InitiativeDetail from './pages/InitiativeDetail';
import ProtectedRoute from './components/ProtectedRoute';

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />

            {/* Protected routes */}
            <Route element={<ProtectedRoute />}>
              <Route element={<Layout />}>
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/initiatives" element={<InitiativeList />} />
                <Route path="/initiatives/:id" element={<InitiativeDetail />} />
                <Route path="/settings" element={<Settings />} />
              </Route>
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
```

## Styling Approach

### Option 1: Tailwind CSS (Recommended)
- Install: `npm install -D tailwindcss postcss autoprefixer`
- Configure: `npx tailwindcss init -p`
- Utility-first approach
- Rapid development
- Small bundle size

### Option 2: Plain CSS Modules
- Component-scoped styles
- No additional dependencies
- More manual work

### Option 3: CSS-in-JS (Styled Components)
- Dynamic styling
- Theme support
- Slightly larger bundle

## Environment Configuration

```bash
# .env.development
VITE_API_BASE_URL=http://localhost:8000

# .env.production
VITE_API_BASE_URL=https://api.produck.com
```

## Development Workflow

```bash
# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run linting
npm run lint
```

## Next Steps for Implementation

1. **Phase 1: Foundation** (2-3 hours)
   - Set up routing structure
   - Create API client and auth context
   - Build basic layout (header, sidebar)
   - Implement login/register pages

2. **Phase 2: Core Features** (4-5 hours)
   - Initiative list and detail pages
   - Question answering interface
   - MRD viewer component
   - Basic CRUD operations

3. **Phase 3: AI Features** (3-4 hours)
   - Question generation UI
   - MRD generation UI
   - Score calculation UI
   - Loading states and progress indicators

4. **Phase 4: Polish** (2-3 hours)
   - Responsive design
   - Error handling
   - Empty states
   - Animations and transitions
   - Toast notifications

5. **Phase 5: Advanced** (Optional)
   - PDF export
   - Dark mode
   - Keyboard shortcuts
   - Advanced filtering/search
   - Analytics dashboard

## Key UX Principles

1. **Progressive Disclosure**: Show only what users need at each step
2. **Clear Feedback**: Loading states, success/error messages
3. **Guided Workflow**: Step-by-step wizard for complex tasks
4. **Mobile-First**: Responsive design from the start
5. **Accessibility**: Semantic HTML, ARIA labels, keyboard navigation

## Complete Example: Initiative Detail Page

See the next section for a full implementation example...
