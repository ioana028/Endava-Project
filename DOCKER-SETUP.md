# Docker Development Setup

This guide explains how to run the project locally using Docker containers with Rancher Desktop.
--------------------------------------------------------------------------------------
|  If you are already familiar with containers, go directly to Step 9: Quick Setup.  |
--------------------------------------------------------------------------------------







## 1. Prerequisites

Before running the project, install:

* **Git**
* **Rancher Desktop**
* **WSL 2** on Windows

During Rancher Desktop setup, make sure WSL 2 integration is enabled and that the container engine is running.

You can verify that Docker is available by running:

```powershell
docker --version
docker compose version
```

Optionally, test the container engine with:

```powershell
docker run hello-world
```

If the `hello-world` container runs successfully, the container environment is ready.

## 2. Get the latest project version

Before starting development, make sure your local repository is up to date.

Switch to `main`:

```powershell
git checkout main
```

Download the latest changes:

```powershell
git pull origin main
```

If you are working on a feature, create or switch to your own branch after updating `main`.

For example:

```powershell
git checkout -b your-branch-name
```

If your branch already exists:

```powershell
git checkout your-branch-name
```

Keep your branch synchronized with `main` according to the team's Git workflow.

## 3. Environment variables

The project uses a local `.env` file for environment variables and secrets.

Use `.env.example` as the reference for the required variables.

Do **not** commit `.env` to Git.

The actual `.env` file is ignored by Git, while `.env.example` can be committed because it should contain only example values/placeholders and no secrets.

## 4. First run

From the root directory of the project, run:

```powershell
docker compose up --build
```

This command:

1. Builds the backend Docker image.
2. Builds the frontend Docker image.
3. Installs the required dependencies inside the images.
4. Creates the containers.
5. Starts the frontend and backend services.

The first build can take longer because Docker needs to download the base images and install the project dependencies.

After the containers start, the application is available at:

Frontend:

```text
http://localhost:5173
```

Backend:

```text
http://localhost:8000
```

Backend health check:

```text
http://localhost:8000/health
```

## 5. Normal development

After the images have already been built, you normally do not need to rebuild them every time.

Start the project with:

```powershell
docker compose up
```

The development setup supports hot reload.

Changes made to backend source files are detected by Uvicorn, and changes made to frontend source files are detected by Vite.

This means that normal source-code changes do not require rebuilding the Docker images.

To stop the running containers, press:

```text
Ctrl + C
```

To stop and remove the project's containers and Docker Compose network:

```powershell
docker compose down
```

## 6. When should I rebuild?

Run:

```powershell
docker compose up --build
```

when something affecting the Docker image has changed, especially:

* `backend/requirements.txt`
* `frontend/package.json`
* `frontend/package-lock.json`
* a `Dockerfile`
* other Docker build configuration

For normal changes to Python, React, TypeScript, CSS, etc., a rebuild should not be necessary because hot reload is enabled.

## 7. Useful commands

Check running project services:

```powershell
docker compose ps
```

View logs:

```powershell
docker compose logs
```

Follow logs continuously:

```powershell
docker compose logs -f
```

View only backend logs:

```powershell
docker compose logs -f backend
```

View only frontend logs:

```powershell
docker compose logs -f frontend
```

Stop the stack:

```powershell
docker compose down
```

Rebuild and start:

```powershell
docker compose up --build
```

## 8. How containers work

A Docker **image** is a packaged environment containing the application and the dependencies required to run it.

A Docker **container** is a running instance of that image.

In this project, the frontend and backend run in separate containers. Docker Compose defines how these services are built, started, configured, and connected.

The main benefit is consistency: instead of every developer manually configuring Python, Node.js, dependencies, versions, and startup commands, Docker provides a reproducible development environment.

In simple terms:

```text
Dockerfile
    ↓
Docker image
    ↓
Container
    ↓
Running application
```

Docker Compose manages the containers together:

```text
docker compose
    │
    ├── frontend container → Vite / React → port 5173
    │
    └── backend container  → FastAPI      → port 8000
```

This makes it easier for all team members to run the project in approximately the same environment and reduces "works on my machine" problems.

## 9. Quick start

Once Rancher Desktop, WSL 2, Git, and the project `.env` are configured:

```powershell
git checkout main
git pull origin main
docker compose up --build
```

After the first successful build, normal development usually only requires:

```powershell
docker compose up
```

Then open:

```text
http://localhost:5173
```
