# AI Beauty Assistant (Web Frontend) Architecture

Date: 2026-03-19

## 1. Purpose
This document describes the architecture of the AI Beauty Assistant web frontend contained in this repository. It focuses on how the UI is composed, how network requests are organized, and how data flows through the application (auth, image upload + analysis, scan history, and user profile management).

## 2. High-level Overview
The application is a single-page React app (SPA) using client-side routing. Users navigate between pages (Login, Dashboard, Image Analysis, Diagnosis Report, Scan History, and User Profile) without full page reloads.

Network communication is handled by a centralized Axios client:
- A base URL is configured in `src/api/config.js`
- Requests are performed through the shared Axios instance in `src/api/client.js`
- Services in `src/services/` provide thin wrappers around the Axios calls
- Hooks in `src/hooks/` provide UI-friendly state (`loading`, `error`, and `result/profile`)

Authentication and theme are handled via React Context:
- `src/contexts/AuthContext.js` stores auth state and provides `login/register/logout/updateProfile`
- `src/contexts/ThemeContext.js` toggles a `dark` CSS class on `document.body`

Images are uploaded from the React UI to the Django backend using `multipart/form-data`:
- `POST /api/analysis/upload/` with fields `image` and `analysis_type` (`skin` | `scalp`)
- Django returns JSON when the request includes `Accept: application/json`

The React UI also caches the last backend response in `localStorage.lastAnalysis` so `/diagnosis` can render reliably.

## 3. Tech Stack
- Frontend: React 18
- Routing: `react-router-dom` (code uses `BrowserRouter`, `Routes`, `Route`, `Navigate`)
- HTTP Client: Axios
- UI:
  - Icons: `lucide-react`
  - Styling: Plain CSS + CSS variables defined in `src/index.css`
- Build tooling: Create React App via `react-scripts`

Key dependencies (from `package.json`):
- `axios`
- `lucide-react`
- `react`, `react-dom`
- `react-router-dom`
- `react-scripts`

## 4. Repository Structure (Frontend)
The relevant source folders are:
- `src/index.js` / `src/App.js` (app bootstrap + routes)
- `src/api/`
  - `config.js` (base URL + endpoint map)
  - `client.js` (Axios instance + interceptors)
- `src/services/`
  - `analysisService.js` (analysis upload/history/detail/delete)
  - `profileService.js` (profile read/update/health/picture upload)
- `src/hooks/`
  - `useAnalysis.js` (calls analysis service, manages loading/error/result)
  - `useProfile.js` (calls profile service, manages loading/error/profile)
  - `useCamera.js` (camera/capture utilities)
- `src/contexts/`
  - `AuthContext.js` (auth state + mock login/register + local profile update)
  - `ThemeContext.js` (theme toggle)
- `src/pages/`
  - `Login.js`, `SignUp.js`, `Home.js`
  - `ImageAnalysis.js`, `DiagnosisReport.js`
  - `History.js`, `AnalysisHistory.js`
  - `UserProfile.js`
- `src/components/`
  - `Navbar.js`, `Footer.js`, `EditProfileModal.js`

## 5. Runtime Architecture (Module Responsibilities)

### 5.1 App Bootstrap and Routing
`src/index.js` renders `<App />` under `React.StrictMode`.

`src/App.js` wraps:
1. `ThemeProvider`
2. `AuthProvider`
3. `BrowserRouter` with routes:
   - `/` -> `Login`
   - `/signup` -> `SignUp`
   - `/home` -> `Home`
   - `/analysis` -> `ImageAnalysis`
   - `/diagnosis` -> `DiagnosisReport`
   - `/history` -> `History`
   - `/analysis-history` -> `AnalysisHistory`
   - `/profile` -> `UserProfile`

### 5.2 Auth & Theme Contexts
#### Auth (`src/contexts/AuthContext.js`)
State stored in React:
- `user` (initially `null`)
- `isAuthenticated` (`false` initially)
- `loading` (`true` until mount completes)

Initialization (on mount):
- Reads `localStorage.getItem('user')` and `localStorage.getItem('authToken')`
- If both exist, sets:
  - `user` (parsed JSON)
  - `isAuthenticated=true`
  - `loading=false`

Auth actions:
- `login(email, password)`:
  - **MOCK** implementation (does not call backend)
  - creates a `mockUser` and `mockToken`
  - stores them in `localStorage`
  - returns `{ success: true, user }`
- `register(userData)`:
  - **MOCK** implementation (does not call backend)
  - stores a generated mock user + token in `localStorage`
  - returns `{ success: true, user }`
- `logout()`:
  - clears `localStorage` keys `user` and `authToken`
  - resets context state
- `updateProfile(updatedData)`:
  - merges into current `user`
  - writes updated user back to `localStorage`
  - returns success + updated user

#### Theme (`src/contexts/ThemeContext.js`)
- `theme` state: `'light' | 'dark'` (default: `'light'`)
- On changes, adds/removes `dark` class to `document.body`
- Provides `toggleTheme(t)` to callers

### 5.3 API Configuration and HTTP Client
#### Endpoint Map (`src/api/config.js`)
Defines:
- `API_BASE_URL` from `import.meta.env.VITE_API_BASE_URL` with default `/api` (relative URLs)
- `API_ENDPOINTS` including:
  - `AUTH.LOGIN`, `AUTH.REGISTER`, `AUTH.LOGOUT`, `AUTH.ME`
  - `ANALYSIS.UPLOAD`, `ANALYSIS.HISTORY`, `ANALYSIS.DETAIL(id)`
  - `PROFILE.GET`, `PROFILE.UPDATE`, `PROFILE.HEALTH`

#### Axios Client (`src/api/client.js`)
Creates `apiClient` with:
- `baseURL: API_BASE_URL`
- `Accept: application/json` (does not force JSON content-type for `FormData`)
- `timeout: 15000`

Interceptors:
- Request interceptor:
  - reads `localStorage.getItem('authToken')`
  - if present, sets `Authorization: Bearer <token>`
- Response interceptor:
  - on `401`:
    - clears `authToken` and `user` from `localStorage`
    - redirects browser to `/`
  - on other errors:
    - extracts an error message from `error.response?.data?.message` / `.error` / `.message`
    - rejects with `new Error(errorMessage)`

### 5.4 Services (Thin Backend Wrappers)
#### Analysis (`src/services/analysisService.js`)
Exports `analysisService` with:
- `uploadImage(imageFile, analysisType)`
  - sends `POST API_ENDPOINTS.ANALYSIS.UPLOAD`
  - payload: `FormData`
    - `image`: file
    - `analysis_type`: `'skin'` or `'scalp'`
  - content type: `multipart/form-data`
  - returns `response.data`
- `getHistory(filters)`
  - sends `GET API_ENDPOINTS.ANALYSIS.HISTORY` with `params: filters`
  - returns `response.data`
- `getAnalysisById(id)`
  - `GET API_ENDPOINTS.ANALYSIS.DETAIL(id)`
- `deleteAnalysis(id)`
  - `DELETE API_ENDPOINTS.ANALYSIS.DETAIL(id)`

#### Profile (`src/services/profileService.js`)
Exports `profileService` with:
- `getProfile()`: `GET /profile/`
- `updateProfile(profileData)`: `PUT /profile/update/`
- `updateHealthProfile(healthData)`: `PUT /profile/health/`
- `uploadProfilePicture(imageFile)`:
  - `POST /profile/update/picture/`
  - `FormData` field: `profile_picture`
  - content type: `multipart/form-data`

### 5.5 Hooks (UI-friendly State)
#### Analysis Hook (`src/hooks/useAnalysis.js`)
Manages:
- `loading`, `error`, `result`

Exposes:
- `uploadImage(imageFile, analysisType)` -> `{ success, data }` or `{ success:false, error }`
- `getHistory(filters)` -> `{ success, data }` or `{ success:false, error }`
- `getAnalysisById(id)` (sets `result`)
- `deleteAnalysis(id)` (no result, returns success/failure)
- `clearResult()`

#### Profile Hook (`src/hooks/useProfile.js`)
Manages:
- `loading`, `error`, `profile`

Exposes:
- `getProfile()` -> `{ success, data }`
- `updateProfile(profileData)` -> `{ success, data }`
- `updateHealthProfile(healthData)` -> updates `profile.healthProfile`
- `uploadProfilePicture(imageFile)` -> sets `profile`
- `clearProfile()`

#### Camera Hook (`src/hooks/useCamera.js`)
Utilities used by `ImageAnalysis`:
- `openCamera()`: requests webcam and attaches stream to `videoRef`
- `closeCamera()`: stops tracks and closes stream
- `capturePhoto()`: captures current frame to a `File` (via canvas `toBlob`)
  - also returns a data URL (`canvas.toDataURL(...)`) for preview usage
- `openNativeCamera(onCapture)`:
  - creates hidden file input with `input.capture = 'user'`
  - on change, sets `capturedImage` and calls `onCapture(file)`
- `clearCapturedImage()`, `checkCameraAvailability()`

## 6. UI Pages and Flows

### 6.1 `/` (Login) - `src/pages/Login.js`
User inputs:
- `email`, `password`

Flow:
1. Submits form and calls `useAuth().login(email, password)`
2. On `{ success:true }`, navigates to `/home`

Note:
- `AuthContext.login` is currently mocked and does not call `/auth/login/` yet.

### 6.2 `/signup` (Sign Up) - `src/pages/SignUp.js`
User inputs:
- name, email, password, confirmPassword
- account type selection (`free` or `premium`)
- health conditions selection

Flow:
1. On submit, constructs `userData`
2. Stores it in `localStorage` under `userProfile`
3. Navigates to `/home`

Note:
- Sign up is also currently not calling backend `/auth/register/`.

### 6.3 `/home` (Dashboard) - `src/pages/Home.js`
This page is primarily a marketing/dashboard UI:
- Uses `Navbar` and `Footer`
- Contains “Quick actions” that navigate to:
  - `/analysis` for skin/scalp analysis
  - `/analysis-history` for “My Reports” (static page, see below)

### 6.4 `/analysis` (Image Upload + Submit) - `src/pages/ImageAnalysis.js`
User selects:
- analysis type:
  - `'skin'` or `'scalp'` (stored in `analysisType` state)
- image input:
  - drag-and-drop or file picker
  - “Take Photo” uses `useCamera.openNativeCamera`

Validation:
- Allowed MIME types: `image/jpeg`, `image/png`, `image/heic`
- Max size: `10 * 1024 * 1024` bytes

Flow:
1. User picks/records an image
2. `Analyze Now` triggers:
   - `useAnalysis.uploadImage(file, analysisType)`
3. On success:
   - the response payload is saved to `localStorage.lastAnalysis`
   - the app navigates to `/diagnosis` so it can render the backend results immediately

### 6.5 `/diagnosis` (Diagnosis Report) - `src/pages/DiagnosisReport.js`
Currently:
- Renders backend analysis results:
  - `conditions` (with severities/confidences)
  - `recommendations`
- Renders AI charts/images returned by the backend:
  - Skin: `efficientnet_visualization`
  - Scalp: `yolo_chart` / `yolo_visualization`
- Provides action buttons like “Download PDF”, “Save Scan”, “Set Reminder”

Behavior:
- Uses `location.state` if present
- Otherwise falls back to `localStorage.lastAnalysis`

### 6.6 `/history` (Scan History - API-backed) - `src/pages/History.js`
State:
- `scanType`: default `'All Types'`
- `severity`: default `'All Severities'`
- `scans`: array from API
- `liked`: local UI state only

Flow:
1. On mount and whenever `scanType` or `severity` change:
   - calls `getHistory({ type: scanType, severity })`
2. If successful, sets `scans` to returned data
3. Renders scan cards with “View Details” and “Report” buttons (not wired to actions)

Potential contract mismatch:
- Frontend filter values like `'All Types'` / `'Skin Scan'` may not match backend expectations (e.g., `type: 'skin' | 'scalp'`).

### 6.7 `/analysis-history` (Static Record List) - `src/pages/AnalysisHistory.js`
This page is hardcoded (`records` array) and does not call backend services.

It provides UI links to:
- `/diagnosis` (but diagnosis is static anyway)
- `/home` and `/analysis`

### 6.8 `/profile` (User Profile) - `src/pages/UserProfile.js`
Data sources:
- API: `useProfile.getProfile()` sets `profile`
- Offline fallback: `localStorage.getItem('userProfile')` sets `localProfile`

Priority:
- `activeProfile = profile || localProfile`

Flow on mount:
1. Load `userProfile` from `localStorage` (if present)
2. Always attempt API `getProfile()` (even if local fallback exists)

Editing:
- UI opens `EditProfileModal`
- `UserProfile` defines `handleSave(formData)` that:
  - writes to `localStorage.userProfile`
  - calls backend `useProfile.updateProfile(formData)`

Gap / mismatch:
- `EditProfileModal` currently does NOT use the `onSave` prop passed by `UserProfile`.
- `EditProfileModal` instead updates auth context (`useAuth().updateProfile`) using a mock local-only update.

## 7. API Endpoints (What the Frontend Expects)

Base URL:
- `API_BASE_URL` = `VITE_API_BASE_URL` (optional) or fallback `/api` (single-server mode)

Auth (expected endpoints, not currently called by mock auth):
- `POST /auth/login/`
- `POST /auth/register/`
- `POST /auth/logout/`
- `GET /auth/me/`

Analysis:
- `POST /analysis/upload/`
  - `multipart/form-data` fields:
    - `image` (file)
    - `analysis_type` (`skin` or `scalp`)
- `GET /analysis/history/`
  - query parameters are sent from `History.js` via `{ type, severity }` (plus optional date filters supported in service comment)
- `GET /analysis/:id/`
- `DELETE /analysis/:id/`

Profile:
- `GET /profile/`
- `PUT /profile/update/`
- `PUT /profile/health/`
- `POST /profile/update/picture/`
  - `multipart/form-data` field: `profile_picture`

## 8. State and Storage

### 8.1 localStorage Keys
The app uses `localStorage` for persistence:
- `authToken`, `user`:
  - managed by `AuthContext`
  - used by Axios request interceptor for Bearer auth
- `userProfile`:
  - used for offline fallback on `/profile`
  - populated during `/signup`
  - updated during profile save logic in `UserProfile` (but may not be triggered due to modal mismatch)

### 8.2 React State Ownership
- Network state:
  - owned by `useAnalysis` and `useProfile`
- UI-only state:
  - example: `liked` map in `History.js`
- Global UI state:
  - theme: `ThemeContext`
  - auth: `AuthContext`

## 9. Styling and Theming

### 9.1 Design Tokens
`src/index.css` defines CSS variables for colors/shadows and base typography/layout styles.

### 9.2 Theme Switching
- `ThemeContext` toggles `document.body.classList` with `dark`
- CSS overrides are controlled by `body.dark { ... }`

### 9.3 CSS Organization
- Global styles: `src/index.css`
- Page-specific styles: `src/pages/*.css`
- Component styles:
  - `src/components/Navbar.css`
  - `src/components/EditProfileModal.css`
  - `src/components/Footer.css`
  - optional shared button styling: `src/components/common/Button.css`

### 9.4 Potential Styling Inconsistency (Important)
Many components/pages use Tailwind-like utility class strings such as:
- `min-h-screen`, `bg-gray-50`, `bg-gray-950`, `text-gray-400`, `grid`, `grid-cols-*`, etc.

In this repository’s CSS (`src/index.css`), only a limited subset of utility classes are defined (e.g., `.flex`, `.grid`, `.grid-cols-*`, some spacing and typography basics).
Classes like `bg-gray-50` and `text-gray-400` are not defined in the inspected CSS, which can lead to missing visual styling unless additional CSS/framework setup exists outside what’s currently in `src/index.css`.

If you expect Tailwind behavior, verify whether Tailwind is actually installed/configured.

## 10. Build, Configuration, and Environment Variables

Start/build scripts (CRA):
- `npm start` -> `react-scripts start`
- `npm run build` -> `react-scripts build`

Environment file:
- `.env.example` defines:
  - `VITE_API_BASE_URL=/api`
  - `VITE_APP_NAME=AI Beauty Assistant`

Important note:
- This repo runs the React build through Django (single-server mode), so API calls are typically relative to `/api`.
- `VITE_API_BASE_URL` is optional; if it’s not set, the app falls back to `/api`.

## 11. Known Gaps and Technical Debt (Based on Current Code)
These are architectural issues affecting end-to-end correctness.

1. Auth is mocked:
   - `AuthContext.login` and `register` do not call backend auth endpoints.
2. Diagnosis report is no longer static:
  - `DiagnosisReport` renders backend payload from `location.state` and/or `localStorage.lastAnalysis` fallback.
3. History wiring is partial:
   - `/history` calls backend `getHistory`, but the UI filter values may not match backend expectations.
   - “View Details” / “Report” buttons are not connected.
4. Duplicate history UI:
   - `/analysis-history` is fully static (`records` hardcoded).
5. Profile edit flow mismatch:
   - `UserProfile` passes `onSave` to `EditProfileModal`, but `EditProfileModal` ignores it.
   - `EditProfileModal` updates `AuthContext` profile state (local-only mock behavior) rather than backend via `useProfile`.
6. Styling/utilities may not be fully defined:
   - Tailwind-like utility class names appear, but the CSS utilities defining them are not present in `src/index.css`.

## 12. Suggested Next Steps (Optional)
If you want the frontend to become fully backend-driven and consistent, typical next steps are:
- Replace `AuthContext.login/register` mock logic with real calls to `API_ENDPOINTS.AUTH.*`.
- Make `DiagnosisReport` either:
  - consume `location.state.data`, or
  - parse a route param/id and call `useAnalysis.getAnalysisById`.
- Unify `/history` and `/analysis-history` so one is API-backed.
- Fix modal save wiring:
  - update `EditProfileModal` to accept/use `onSave`, and let `UserProfile` decide whether to call backend.
- Align filter and payload contract with backend expectations (e.g., `type` values).
- Ensure env var support works with CRA (replace `import.meta.env` with CRA-compatible env access).

