# SourceBuild – Affordable Construction Planning Platform

SourceBuild is a Flask + MongoDB web app that connects customers with engineers for construction planning, cost estimation, and plan image exchange.

## Quickstart (Local)

1. Create and activate a virtual environment

	Windows:

	```
	python -m venv .venv
	.venv\Scripts\activate
	```

2. Install dependencies

	```
	pip install -r requirements.txt
	```

3. Configure environment

	- Copy `.env.example` to `.env` (or edit the existing `.env`)
	- Set at minimum:
	  - `SECRET_KEY` (required, use a long random string)
	  - `MONGO_URI` (e.g. `mongodb://localhost:27017` or your Atlas URI)
	  - `MONGO_DB_NAME` (default: `sourcebuild_db`)
	  - `MONGO_MOCK_FALLBACK` (`1` for local dev fallback, set `0` in production)

4. Start the app

	```
	python app.py
	```

5. Open in browser

	- `http://127.0.0.1:5000`

## Production / Deployment

### Push to GitHub

1. Install Git on your machine if it is not already installed.
2. Open a terminal in the project folder.
3. Initialize the repo if needed:

	```
	git init
	```

4. Add your GitHub remote:

	```
	git remote add origin https://github.com/<your-username>/<your-repo>.git
	```

5. Commit and push:

	```
	git add .
	git commit -m "Prepare app for deployment"
	git branch -M main
	git push -u origin main
	```

### Quick deploy options

#### Option 1: Docker Compose

- Make sure Docker Desktop is installed.
- Set the required environment values in `.env`.
- Run:

  ```
  docker compose up --build
  ```

#### Option 2: Production server

- Use `waitress-serve --listen=0.0.0.0:5000 wsgi:app`.
- Point your hosting platform to the repository.
- Configure environment variables in the platform settings.

#### Option 3: Cloud hosting

- Push to GitHub.
- Connect the repo to a host like Render, Railway, Fly.io, or a VPS.
- Use the `wsgi:app` entrypoint and set `SECRET_KEY`, `MONGO_URI`, and `MONGO_DB_NAME`.
- Set `MONGO_MOCK_FALLBACK=0` in production to force a real MongoDB.

## Health Check

- Endpoint: `/health`
- Returns:
  - `200` when DB is connected
  - `503` when DB is unavailable
- Includes `database_mode` (`mongodb` or `mock`) in the response JSON.

## Docker (Optional Full Stack Local Run)

Use Docker Compose to run the app and MongoDB together:

1. Build and start:

	```
	docker compose up --build
	```

2. Open:

	- `http://127.0.0.1:5000`

3. For containerized runs, set in `.env`:

	- `MONGO_URI=mongodb://mongo:27017`
	- `MONGO_MOCK_FALLBACK=0`

## Main Routes

- `/` home
- `/about`
- `/register_customer` (GET, POST)
- `/register_engineer` (GET, POST)
- `/login` (GET, POST)
- `/dashboard_customer`
- `/dashboard_engineer`
- `/estimate_cost` (POST)
- `/upload_area_image` (POST)
- `/upload_plan_image/<area_image_id>` (POST)

## Notes

- Tailwind is loaded via CDN for rapid UI iteration.
- Passwords are hashed using Werkzeug.
- Uploaded files are stored in `static/uploads`.

