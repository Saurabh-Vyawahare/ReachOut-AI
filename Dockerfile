# Stage 1: Build React frontend
FROM node:20-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Stage 2: Python backend + serve built frontend
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ src/
COPY server.py .
COPY credentials/ credentials/
COPY data/ data/
COPY --from=frontend /app/frontend/dist frontend/dist/
EXPOSE 8000
CMD ["python", "server.py"]
