# Website Preview App

A full-stack application built with React (frontend) and FastAPI (backend).

Users can:

- Sign up and log in
- Submit a website URL
- Generate and store a screenshot preview using Playwright
- View all previously saved URLs/screenshots for their own account

## Project Structure

```text
website-preview-app/
|
|-- frontend/
|   |-- src/
|   |   |-- components/
|   |   |   `-- WebsitePreview.jsx
|   |   |-- pages/
|   |   |   |-- Signup.jsx
|   |   |   |-- Login.jsx
|   |   |   `-- Dashboard.jsx
|   |   |-- App.jsx
|   |   |-- main.jsx
|   |   `-- index.css
|   |-- index.html
|   `-- package.json
|
|-- backend/
|   |-- main.py
|   |-- database.py
|   |-- models.py
|   |-- requirements.txt
|   `-- screenshots/
|
`-- README.md
```

## Backend Setup (FastAPI)

1. Open terminal and go to backend folder:

```bash
cd backend
```

2. Create and activate a virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate
```

3. Install backend dependencies:

```bash
pip install -r requirements.txt
```

4. Install Playwright browser (required for screenshots):

```bash
playwright install chromium
```

5. Run FastAPI server:

```bash
uvicorn main:app --reload
```

Backend API will run at `http://localhost:8000`.

## Frontend Setup (React)

1. Open a new terminal and go to frontend folder:

```bash
cd frontend
```

2. Install dependencies:

```bash
npm install
```

3. Run React development server:

```bash
npm run dev
```

Frontend will run at `http://localhost:5173`.

## APIs Implemented

- `POST /signup` - register user (rejects duplicate emails)
- `POST /login` - authenticate user and return JWT token
- `POST /preview` - save URL, generate screenshot with Playwright, store record
- `GET /websites` - get logged-in user's saved website previews

## Testing Flow

1. Open frontend at `http://localhost:5173`.
2. Create a new account on Signup page.
3. Login with your registered credentials.
4. On dashboard, submit this URL:

```text
https://www.justdial.com/Hyderabad/Dr-Sarita-Rao-Tx-Hospitals-Near-Masjid-Uppal-Bus-Stand-Bharath-Nagar-Colony-Uppal/040PXX40-XX40-231215200040-Y2E1_BZDET
```

5. Wait for "Generating preview...".
6. Confirm a preview card appears with:

- URL
- Screenshot
- Saved date/time

7. Logout and login again.
8. Confirm previously saved websites still appear for that user.

## Notes

- Data is stored in SQLite database file: `backend/website_preview.db`.
- Screenshot images are stored in: `backend/screenshots/`.
- Passwords are hashed before storing.
- Each user only sees their own saved websites.
