# AML Event Injector — Microsoft Fabric IQ Ontology

A full-stack web application to inject AML transaction data into **Azure Event Hubs → Fabric Eventstream → Eventhouse**. Built for the **Hack2Future Business Challenge 1**.

> **Stack**: Python 3.11 · FastAPI · Uvicorn · Pydantic v2 · Vanilla HTML/JS

---

## Folder Structure

```
aml-event-injector/
├── app.py                        ← FastAPI app entry point
├── startup.sh                    ← Azure App Service startup command
├── requirements.txt              ← Python dependencies
├── .env.example                  ← Environment variables template
├── routes/
│   ├── events.py                 ← All event injection endpoints
│   └── health.py                 ← Health check
├── services/
│   └── event_hub_service.py      ← Azure Event Hubs async client
├── validators/
│   └── schemas.py                ← Pydantic v2 input validation
└── static/
    ├── index.html                ← Single-page frontend (no build step)
    ├── css/style.css
    └── js/
        ├── app.js
        ├── forms.js
        ├── patterns.js
        └── eventlog.js
```

---

## Local Development

### 1. Clone and install

```bash
git clone <your-repo>
cd aml-event-injector
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env — set EVENT_HUB_CONNECTION_STRING and EVENT_HUB_NAME
```

### 3. Run

```bash
# Development (auto-reload on save)
ENVIRONMENT=development python app.py

# Or directly with uvicorn
uvicorn app:app --reload --port 8000
```

Open `http://localhost:8000`

### 4. Demo mode (no Azure required)

If `EVENT_HUB_CONNECTION_STRING` is not set or contains `YOUR_NAMESPACE`, the app runs in **DEMO mode** — it logs events to the console instead of sending to Azure. The UI shows "DEMO MODE" in the header.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | /api/health | Server + Event Hub status |
| POST | /api/events/transaction | Send a single transaction |
| POST | /api/events/customer | Register a customer entity |
| POST | /api/events/account | Register a bank account |
| POST | /api/events/merchant | Register a merchant entity |
| POST | /api/events/batch | Send up to 500 events at once |
| POST | /api/events/seed/{pattern} | Seed AML demo pattern |

Interactive API docs: `http://localhost:8000/docs`

### Seed patterns

| Pattern | Description | Events |
|---------|-------------|--------|
| `structuring` | 4 sub-threshold transactions (AML-001) | 4 |
| `circular` | 3-hop A→B→C→A fund rotation (AML-002) | 3 |
| `fanout` | 1→10 layer distribution (AML-002/003) | 10 |
| `velocity` | 20 rapid UPI transactions (AML-004) | 20 |
| `chitfund` | 5 accounts → 1 chit fund (AML-005) | 5 |

---

## Azure Setup & Deployment

> **Why not Azure Static Web Apps?**
> Static Web Apps only hosts static files + Azure Functions. This app requires a persistent Python ASGI server (Uvicorn). **Azure App Service** (Python runtime) is the correct and simplest deployment target.

---

### STEP 1 — Create Azure Event Hubs

1. **portal.azure.com** → Search **Event Hubs** → Create
2. Settings:
   - **Namespace name**: `aml-hack-eventhub`
   - **Pricing tier**: Standard
   - **Region**: Central India
3. After creation → **Event Hubs** → **+ Event Hub**
   - Name: `transactions-stream`
   - Partitions: 4
4. **Shared Access Policies** → `RootManageSharedAccessKey` → copy **Connection String – primary key**

---

### STEP 2 — Create Azure App Service (Python)

1. **portal.azure.com** → Search **App Service** → Create
2. Settings:
   - **Name**: `aml-event-injector` (must be globally unique)
   - **Publish**: Code
   - **Runtime stack**: Python 3.11
   - **OS**: Linux
   - **Region**: Central India
   - **Plan**: F1 Free (hackathon) or B1 Basic (production)
3. **Review + Create** → **Create**

---

### STEP 3 — Configure Environment Variables

App Service → **Settings** → **Environment variables** → Add:

| Name | Value |
|------|-------|
| `EVENT_HUB_CONNECTION_STRING` | `Endpoint=sb://aml-hack-eventhub.servicebus.windows.net/;...` |
| `EVENT_HUB_NAME` | `transactions-stream` |
| `ENVIRONMENT` | `production` |

Click **Apply** → **Confirm**

---

### STEP 4 — Set Startup Command

App Service → **Settings** → **Configuration** → **General settings**

Set **Startup command**:
```
uvicorn app:app --host 0.0.0.0 --port $PORT --workers 2
```

Click **Save**

---

### STEP 5A — Deploy via Azure CLI (Recommended)

```bash
# Install Azure CLI: https://aka.ms/installazurecli
az login

# From project root — zip and deploy (excludes .venv, __pycache__, .git)
zip -r deploy.zip . \
  --exclude "*/.venv/*" \
  --exclude "*/__pycache__/*" \
  --exclude "*/.git/*"

az webapp deployment source config-zip \
  --resource-group rg-aml-hack \
  --name aml-event-injector \
  --src deploy.zip
```

---

### STEP 5B — Deploy via GitHub Actions (CI/CD)

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Azure App Service

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Deploy to Azure App Service
        uses: azure/webapps-deploy@v3
        with:
          app-name: aml-event-injector
          publish-profile: ${{ secrets.AZURE_WEBAPP_PUBLISH_PROFILE }}
```

To get `AZURE_WEBAPP_PUBLISH_PROFILE`:
1. App Service → **Get publish profile** → download file
2. GitHub → **Settings** → **Secrets** → New secret: `AZURE_WEBAPP_PUBLISH_PROFILE`

---

### STEP 5C — Deploy via VS Code

1. Install extension: **Azure App Service** (Microsoft)
2. Sign in to Azure in VS Code sidebar
3. Right-click your App Service → **Deploy to Web App...**
4. Select the project folder → confirm

---

### STEP 6 — Verify Deployment

Open: `https://aml-event-injector.azurewebsites.net/api/health`

Expected:
```json
{
  "status": "ok",
  "mode": "LIVE",
  "eventHub": "transactions-stream",
  "uptime": 12
}
```

If `"mode": "DEMO"` — check that `EVENT_HUB_CONNECTION_STRING` is set correctly in App Service environment variables.

---

### STEP 7 — Connect to Fabric Eventstream

1. **Microsoft Fabric** workspace → open your **Eventstream**
2. Add source → **Azure Event Hubs**
3. Select namespace `aml-hack-eventhub`, hub `transactions-stream`
4. Set destination: **Eventhouse** (your `aml_realtime` KQL DB)

Data pipeline:
```
Web App → Event Hubs → Eventstream → Eventhouse → Ontology → Agent
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| App shows DEMO mode on Azure | Check `EVENT_HUB_CONNECTION_STRING` in App Service env vars |
| CORS error in browser | Verify the App Service URL matches what you're accessing |
| 503 on Azure | Check startup command is set to `uvicorn app:app --host 0.0.0.0 --port $PORT --workers 2` |
| Event Hub connection refused | Verify connection string includes `SharedAccessKey` |
| `ModuleNotFoundError` on Azure | Ensure `requirements.txt` is in project root; App Service installs it automatically |
| Slow first request | F1 free tier has no always-on; upgrade to B1 or enable Always On |
