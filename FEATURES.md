# Cloud Cost Optimizer — Complete Feature List & Usage Guide

---

## Data Sources & Data Flow Architecture

The application operates on **two distinct data sources** — one for demo/testing and one for persistent storage:

### Data Source 1: Synthetic Data Generator (`app/data_generator.py`)
This is the **primary data source for the dashboard charts and ML analysis**. It generates realistic cloud cost data programmatically — no real cloud provider connection needed.

#### What data it generates:

| Generator Function | Data It Produces | Columns / Structure |
|---|---|---|
| `generate_daily_costs(days=180)` | 180 days of daily cost records across AWS, Azure, GCP | `date, provider, service, region, environment, department, cost, usage_quantity, usage_unit` |
| `generate_resource_inventory()` | 200+ cloud resources with utilization metrics | `resource_id, provider, service, family, region, environment, department, monthly_cost, cpu_utilization_pct, memory_utilization_pct, days_active, status` |
| `generate_optimization_recommendations()` | 10 optimization suggestions with savings estimates | `title, category, risk_level, description, potential_monthly_savings, impact_score, affected_resources_count, provider, status, ai_confidence` |
| `generate_tag_compliance_data()` | Per-resource tag compliance percentages | `resource_id, provider, service, total_tags_required, tags_compliant, compliance_pct, missing_tags, environment, department` |

#### How the synthetic data is generated:
- **Random seed**: `np.random.seed(42)` ensures reproducible data
- **Seasonal patterns**: Sinusoidal yearly cycle (`1 + 0.3 * sin(2π * day/365)`)
- **Weekend patterns**: Costs are 40% lower on Saturdays and Sundays
- **Trend patterns**: 15% cost increase over 180 days
- **Randomization**: Random services (3-7 per provider per day), random regions, random environments, random departments, random usage quantities
- **Resource utilization**: CPU from 5-95%, memory from 10-90%, monthly costs from $10-$5,000
- **Recommendations**: Predefined titles with randomized savings ranges, confidence scores 75-99%

#### When it's generated:
- On first dashboard load when user clicks **"Generate Demo Data"**
- Automatically cached via `@st.cache_data(ttl=3600)` — regenerates only once per hour
- Regenerated on demand when user clicks **"Refresh Data"** (clears cache first)

---

### Data Source 2: SQLite Database (`cloud_optimizer.db`)
This is the **data source for authentication, RBAC, multi-tenancy, and user management**. It persists across sessions.

#### Database Tables (Models):

| Table (ORM Model) | Purpose | Key Columns |
|---|---|---|
| `organizations` | Multi-tenant organizations | `id, name, slug, description, is_active, created_at` |
| `teams` | Teams within organizations | `id, org_id, name, description` |
| `users` | User accounts with roles | `id, org_id, team_id, email, password_hash, name, role, avatar, is_active, joined, last_login` |
| `user_activities` | Activity audit log | `id, user_id, action, details, timestamp` |
| `role_permissions` | RBAC permission rules | `id, role, resource_type, action` |
| `providers` | Cloud provider list | `id, name` |
| `services` | Cloud service types per provider | `id, provider_id, name, family` |
| `resources` | Cloud resources (org-scoped) | `id, org_id, resource_id, provider_id, monthly_cost, cpu_utilization_pct`, etc. |
| `daily_costs` | Daily cost records (org-scoped) | `id, org_id, date, provider, service, cost, usage_quantity` |
| `cost_anomalies` | Detected anomalies (org-scoped) | `id, org_id, date, cost, expected_cost, anomaly_score, method` |
| `forecasts` | Cost forecasts (org-scoped) | `id, org_id, forecast_date, predicted_cost, lower_bound, upper_bound, model` |
| `recommendations` | Optimization recommendations (org-scoped) | `id, org_id, title, category, savings, impact_score, status, ai_confidence` |
| `tag_compliance` | Tag compliance snapshots | `id, org_id, resource_id, compliance_pct, missing_tags` |

#### How the database gets populated:

| Action | What Happens |
|---|---|
| **First app launch** | `auth.py` calls `_ensure_db_initialized()` → creates tables via `init_db()` → calls `seed_database()` |
| **Database seeding** | `seed.py` creates: 2 organizations, 4 teams per org, 4 users per org (admin/devops/optimizer/viewer), 1 super admin, activity logs for each user, and all RBAC permissions via `seed_role_permissions()` |
| **User registration** | New organizations + admin users are inserted via `register_organization()` in `auth.py` |
| **Admin actions** | Creating/editing/deleting users and teams via `CostRepository` methods |
| **Activity tracking** | Every login, logout, data export, user creation, etc. inserts a row into `user_activities` |

---

### Data Flow: How Data Moves Through the Application

```
[1] DATA GENERATION
    app/data_generator.py
    │
    ├── generate_daily_costs(days=180)  ──┐
    ├── generate_resource_inventory()     ├──→ cached in Streamlit session_state
    ├── generate_optimization_recommendations() ─┘   (ttl=3600s)
    └── generate_tag_compliance_data()
         │
         ▼
[2] ANALYSIS ENGINE
    app/cost_analyzer.py (CostAnalyzer class)
    │
    ├── detect_cost_anomalies_isolation_forest()  →  ml/anomaly.py  →  Isolation Forest
    ├── forecast_monthly_costs()                   →  ml/forecaster.py  →  LinearRegression
    ├── get_rightsizing_recommendations()           →  CPU/utilization thresholds → recommendations
    ├── get_wastage_analysis()                      →  Idle & over-provisioned resource detection
    ├── get_tag_compliance_summary()                →  Aggregation by provider
    ├── cluster_services_for_optimization()         →  ml/clustering.py (KMeans / XGBoost)
    └── estimate_savings_potential()                →  Sums rightsizing + idle + storage savings
         │
         ▼
[3] ML MODULES (ml/)
    │
    ├── ml/forecaster.py         ←── forecast_monthly_costs()
    │   ├── forecast_prophet()       →  Facebook Prophet forecast
    │   ├── forecast_xgboost()       →  XGBoost forecast (7 date features)
    │   ├── forecast_linear()        →  Linear Regression baseline
    │   └── fast_forecast()          →  Default: Linear Regression
    │
    ├── ml/anomaly.py            ←── detect_cost_anomalies_isolation_forest()
    │   ├── detect_iforest()         →  Isolation Forest (unsupervised)
    │   ├── detect_xgb_anomaly()     →  XGBoost (regression error threshold)
    │   ├── detect_autoencoder()     →  TensorFlow autoencoder (reconstruction error)
    │   └── ensemble_anomaly()       →  Majority vote of all 3 methods
    │
    └── ml/clustering.py         ←── cluster_services_for_optimization()
        ├── cluster_kmeans()         →  KMeans (4 clusters)
        ├── cluster_dbscan()         →  DBSCAN (density-based)
        └── cluster_xgb_importance() →  XGBoost feature importance
         │
         ▼
[4] VISUALIZATION LAYER
    app/visualizations.py (14 Plotly chart types)
    │
    ├── create_cost_trend()              →  Multi-line cost over time
    ├── create_cost_breakdown_pie()      →  Donut chart by provider
    ├── create_forecast_chart()          →  Historical line + predicted bars
    ├── create_anomaly_chart()           →  Cost spikes with anomaly highlights
    ├── create_savings_waterfall()       →  Rightsizing + idle + storage savings
    ├── create_multi_cloud_comparison()  →  Monthly grouped bars by provider
    ├── create_environment_cost_chart()  →  Stacked bars by environment
    ├── create_animated_cost_trend()     →  Animated cumulative cost day-by-day
    ├── create_animated_bar_race()       →  Month-by-month bar race animation
    └── create_service_cluster_chart()   →  KMeans/DBSCAN cluster scatter plot
         │
         ▼
[5] STREAMLIT DASHBOARD (app/dashboard.py)
    │
    ├── Tab 1: Cost Overview        →  Charts + KPI cards
    ├── Tab 2: AI Insights          →  Rightsizing, savings, waste analysis
    ├── Tab 3: Anomaly Detection    →  Anomaly metrics + chart
    ├── Tab 4: Forecasting          →  Forecast KPIs + combo chart
    ├── Tab 5: Optimization         →  Recommendation cards + filters
    ├── Tab 6: Tag Compliance       →  Compliance metrics + bar chart
    ├── Tab 7: AI Chatbot           →  NLP queries over cost data (RAG)
    └── Tab 8: My Profile           →  User info + activity log
         │
         ▼
[6] AI CHATBOT (AI/)
    │
    ├── AI/embeddings.py          →  Text embeddings for semantic search
    ├── AI/vector_store.py        →  ChromaDB vector database for cost documents
    ├── AI/nlp_processor.py       →  Query parsing & intent extraction
    ├── AI/rag_chain.py           →  Retrieve → Augment → Generate pipeline
    ├── AI/agent.py               →  Multi-step reasoning for complex queries
    └── AI/chatbot.py             →  Main chatbot interface (uses Llama 3.2 via Ollama)
         │
         ▼
[7] AUTH & BACKEND (Database-backed)
    │
    ├── app/auth.py               →  Login, logout, permission checks, activity recording
    │   ├── SQLite users table    →  verify_login(), perform_login()
    │   ├── role_permissions      →  check_permission()
    │   └── user_activities       →  record_activity()
    │
    └── backend/main.py           →  FastAPI REST API with RBAC middleware
        ├── /auth/login           →  Basic auth login
        ├── /organizations        →  List orgs (super admin)
        ├── /organizations/{id}/users  →  Org users
        └── /organizations/{id}/teams  →  Org teams
```

### Data Isolation (Multi-Tenancy)
```
Organization A (CloudOpt Inc.)     Organization B (Acme Corp)
   ├── Teams                          ├── Teams
   ├── Users                          ├── Users
   ├── Cost Data                      ├── Cost Data
   ├── Resources                      ├── Resources
   ├── Recommendations                ├── Recommendations
   └── Activity Logs                  └── Activity Logs
         ↑                                    ↑
    org_id = 1                           org_id = 2
         ↑                                    ↑
    user A sees only                   user B sees only
    org_id = 1 data                    org_id = 2 data
```

Key Multi-Tenancy Rules:
1. All cost data tables (`daily_costs`, `resources`, `recommendations`, `cost_anomalies`, `forecasts`, `tag_compliance`) have an `org_id` column
2. `CostRepository` methods accept `org_id` parameters to scope queries
3. `check_permission()` validates role-based access before returning data
4. Super admin (`super_admin` role) bypasses org scoping and sees all data
5. Regular users never see data from other organizations

---

## 1. Multi-Tenant Organization & RBAC (Role-Based Access Control)

### Features:
- **Organizations** — Each company/team gets an isolated organization with its own data, users, teams, costs, and resources.
- **Teams** — Departments (Engineering, DevOps, Finance, etc.) within each organization for finer access grouping.
- **5 User Roles:**
  | Role | Permissions |
  |------|-------------|
  | **super_admin** | Full access across ALL organizations. Can view/manage everything. |
  | **org_admin** | Full control within their own organization — manage users, teams, settings, approve recommendations. |
  | **team_lead** | Read costs, users, teams, settings. Can approve recommendations. |
  | **optimizer** | Read costs, read users/teams/settings. Can create/write recommendations. |
  | **viewer** | Read-only access to all data within the organization. |
- **Data Isolation** — Cost data, resources, recommendations, and all records are scoped to an organization.

### Usage:
- Registration: New organizations can be created from the login page via the "Register Organization" tab.
- Login: Enter email + password → user is redirected to their organization's dashboard.
- Organization switching: Super admins can see all organizations; regular users are locked to their org.
- Permission checks happen via `check_permission(resource_type, action)` — called throughout the UI to show/hide tabs, buttons, and data.

---

## 2. Authentication System

### Features:
- **Database-backed authentication** using SQLite + SQLAlchemy.
- **Password hashing** with SHA-256.
- **Login/Logout** with session management via Streamlit `session_state`.
- **Activity tracking** — All user actions (login, logout, data exports, profile changes) are recorded with timestamps.
- **Demo credentials** pre-seeded for all 5 roles:
  | Email | Password | Role |
  |-------|----------|------|
  | superadmin@cloudopt.com | superadmin123 | Super Admin |
  | admin@cloudopt-inc.com | admin123 | Org Admin |
  | devops@cloudopt-inc.com | devops123 | Team Lead |
  | optimizer@cloudopt-inc.com | opt123 | Optimizer |
  | viewer@cloudopt-inc.com | view123 | Viewer |

### Usage:
- On first load, the database is initialized and seeded automatically.
- Login page shows a styled form with demo credentials for quick testing.
- After login, the sidebar shows the user's name, role, organization, and team.
- Logout button in the sidebar footer clears session state.

---

## 3. Admin Dashboard (User & Team Management)

### Features:
- **User Management:** Add new users, edit existing users (name, email, role, team, department), deactivate users.
- **Team Management:** Create teams, rename teams, delete teams.
- **Organization Settings:** Update organization name and description.
- **Super Admin View:** List all organizations in the system with user/team counts.

### Usage:
- Accessible from the "🏢 Administration" tab (visible only to users with admin permissions).
- **Add User:** Fill name, email, role, team, password → click "Create User".
- **Edit User:** Click "Edit" next to a user → modify fields → "Save".
- **Deactivate User:** Click "Deactivate" to disable an account.
- **Create Team:** Enter team name + description → "Create".
- **Rename/Delete Team:** Use inline text field + buttons.
- **Super Admin:** Sees an "All Organizations" table with aggregate stats.

---

## 4. Cost Overview Dashboard (Tab 1)

### Features:
- **Daily Cost Trend** — Multi-line chart showing cost over time grouped by cloud provider (AWS/Azure/GCP).
- **Animated Cost Trend** — Play animation showing cumulative cost growth day-by-day.
- **Cost Breakdown Pie** — Donut chart showing cost distribution across providers.
- **Multi-Cloud Monthly Comparison** — Bar chart comparing monthly spend across providers.
- **Environment Cost Chart** — Cost breakdown by environment (Production, Staging, Development, QA).
- **Top 10 Expensive Services** — Horizontal bar chart of highest-cost services.
- **Service Clustering** — KMeans/DBSCAN clustering of services by cost patterns.
- **Animated Bar Race** — Month-by-month animated bar chart showing provider cost evolution.
- **KPI Metric Cards:**
  - Total Spend (with daily average)
  - Monthly Run Rate (projected)
  - Potential Savings (monthly & annual)
  - Cloud Services Count
  - Tag Compliance Percentage

### Usage:
- Click "🚀 Generate Demo Data" in the sidebar to load synthetic data.
- Use "🔄 Refresh Data" to regenerate all data.
- Apply filters via sidebar: multi-select providers and date range.
- Navigate through interactive Plotly charts (hover, zoom, pan).

---

## 5. AI Insights (Tab 2)

### Features:
- **Rightsizing Recommendations** — Resources classified by utilization:
  - CPU < 5% → "Stop/Terminate (idle)" — **Critical** priority
  - CPU < 20% + Memory < 30% → "Downsize instance type" — **High/Medium** priority
- **Savings Breakdown Waterfall** — Visualizes savings from rightsizing, idle resources, and storage optimization.
- **Resource Utilization Scatter** — CPU vs Memory utilization scatter plot.
- **Waste Analysis:**
  - Monthly waste total ($)
  - Idle resource count (CPU < 5%)
  - Over-provisioned resource count (CPU 5-20%)
  - Detail table with per-resource waste breakdown.

### Usage:
- View color-coded recommendation cards with priority badges.
- Each card shows: resource ID, provider, service, action, monthly savings.
- Waste analysis shows summary metrics and expandable detail table.

---

## 6. Cost Anomaly Detection (Tab 3)

### Features:
- **Isolation Forest** — Flags cost anomalies using unsupervised learning (contamination = 5%).
- **XGBoost** — Regression error-based anomaly detection (prediction error threshold).
- **TensorFlow Autoencoder** — Reconstruction error-based anomaly detection.
- **Ensemble Detection** — Majority voting among all three methods.
- **Anomaly Metrics:**
  - Anomalies detected (count)
  - Anomaly rate (%)
  - Average deviation (%)
  - Largest anomaly ($ amount)
- **Anomaly Visualization** — Interactive chart showing cost spikes with anomaly highlights.

### Usage:
- Data loads automatically from cached generation.
- Summary metrics update dynamically.
- Hover over anomaly points in the chart to see date, cost, and deviation details.

---

## 7. Cost Forecasting (Tab 4)

### Features:
- **Prophet Forecasting** — Facebook Prophet with yearly + weekly seasonality.
- **XGBoost Forecasting** — Gradient boosting with engineered date features.
- **Linear Regression Forecasting** — Simple baseline with days_since/month/quarter features.
- **Ensemble Forecast** — Average of all available methods.
- **Forecast KPIs:**
  - Next month projection ($ and % change vs current)
  - 6-month total projection
  - Average monthly projection
- **Forecast Visualization** — Historical line + predicted bars with confidence intervals.

### Usage:
- Default uses fast linear regression (`fast_forecast`).
- View projected costs for the next 6 months in both chart and table formats.
- Compare forecast vs historical trends.

---

## 8. Optimization Recommendations (Tab 5)

### Features:
- **Recommendation Cards** — Full list with categories, providers, impact scores, AI confidence.
- **Status Tracking** — Each recommendation has status: pending, in-progress, completed, dismissed.
- **Filters** — Filter by category and provider.
- **Sorting** — Sorted by impact score (highest first).
- **Metrics:**
  - Annual savings potential ($)
  - High impact recommendations count
  - Average AI confidence (%)
  - Pending actions count

### Usage:
- Each card shows: title, description, provider, category, affected resources, confidence score, potential monthly savings (with green badge).
- Use category and provider filters to narrow down.
- Recommendations are generated by the data generator with realistic synthetic data.

---

## 9. Tag Compliance (Tab 6)

### Features:
- **Compliance by Provider** — Bar chart showing average compliance % per cloud provider.
- **Compliance Metrics:**
  - Total resources tracked
  - Overall compliance %
  - Fully compliant resources count
  - Non-compliant resources count
- **Detail Tables** — Expandable raw tag compliance data.
- **Compliance Rate** — Percentage of fully compliant resources per provider.

### Usage:
- Compliance is calculated per resource based on tag coverage.
- Green metric when compliance > 80%, orange when below.
- View detailed compliance data in the expandable section.

---

## 10. AI Chatbot (Tab 7)

### Features:
- **Natural Language Queries** — Ask questions about cloud costs in plain English.
- **RAG Pipeline** — Retrieval-Augmented Generation using ChromaDB vector store + embeddings.
- **NLP Processor** — Query parsing and intent recognition.
- **Agent Workflows** — Multi-step reasoning for complex queries.
- **Fallback LLM** — Simple fallback when the main chatbot fails.
- **Suggested Queries** — Pre-built quick buttons:
  - "What are my total cloud costs?"
  - "Show cost trends for AWS"
  - "Any anomalies detected?"
  - "What can I optimize?"
  - "List idle resources"
  - "Cost forecast for next quarter"
  - "Show tag compliance"
  - "What's my wastage?"
- **Conversation History** — Chat messages persist during the session.
- **Clear Chat** — Reset conversation with one button.
- **Initialize AI** — Button to (re)start the AI backend.

### Usage:
1. Click "Initialize AI" to start the chatbot backend.
2. Type a question in the chat input, or click a suggested query.
3. The AI responds with cost insights using RAG over the loaded data.
4. Use "Clear Chat" to reset the conversation.
5. If the main chatbot fails, it falls back to a simpler NLP + LLM combo.

---

## 11. User Profile (Tab 8)

### Features:
- **Profile Header** — Avatar, name, role, organization, team, department, join date, last login.
- **Stat Cards:**
  - Total activities
  - Today's actions
  - Account status (Active)
  - Verification status (Verified)
- **Personal Information Card** — Full details: name, email, role, org, team, company, department, dates.
- **Account Settings:**
  - Change Password (placeholder)
  - Notification Preferences (placeholder)
  - Export My Data (records activity log entry)
- **Recent Activity Log** — Last 15 actions with timestamps, emoji icons, and details.

### Usage:
- Auto-populated from user data stored in the database.
- Activity log shows login/logout, data exports, and other actions.
- Account settings buttons are placeholders for future features.

---

## 12. ML Modules (Standalone)

### a) Anomaly Detection (`ml/anomaly.py`)
| Method | Algorithm | Description |
|--------|-----------|-------------|
| `detect_iforest` | Isolation Forest | Unsupervised outlier detection — flags days with unusual cost patterns |
| `detect_xgb_anomaly` | XGBoost | Regression error thresholding — trains model, high-error days = anomalies |
| `detect_autoencoder` | TensorFlow Autoencoder | Reconstruction error — days the autoencoder can't reconstruct well are anomalies |
| `ensemble_anomaly` | Majority Vote | Combines all 3 methods; anomaly flagged if ≥2 agree |

### b) Forecasting (`ml/forecaster.py`)
| Method | Algorithm | Description |
|--------|-----------|-------------|
| `forecast_prophet` | Facebook Prophet | Yearly + weekly seasonality with changepoint detection |
| `forecast_xgboost` | XGBoost | Gradient boosting with 7 engineered date features |
| `forecast_linear` | Linear Regression | Simple baseline using days_since, month, quarter |
| `ensemble_forecast` | Average | Mean of all available forecasts |
| `fast_forecast` | Linear Regression | Default fast method used by CostAnalyzer |

### c) Clustering (`ml/clustering.py`)
| Method | Algorithm | Description |
|--------|-----------|-------------|
| `cluster_kmeans` | KMeans | Groups services into 4 clusters by cost patterns |
| `cluster_dbscan` | DBSCAN | Density-based clustering (finds arbitrary-shaped groups) |
| `cluster_xgb_importance` | XGBoost | Feature importance analysis for cost pattern understanding |

---

## 13. AI / RAG Chatbot System (`AI/`)

### Features:
- **Embeddings** (`AI/embeddings.py`) — Text embeddings for semantic search.
- **Vector Store** (`AI/vector_store.py`) — ChromaDB-based vector database for storing/retrieving cost-related documents.
- **NLP Processor** (`AI/nlp_processor.py`) — Query parsing and intent extraction.
- **Document Loader** (`AI/document_loader.py`) — Loads and chunks documentation/cost data.
- **RAG Chain** (`AI/rag_chain.py`) — Full RAG pipeline: retrieve → augment → generate.
- **Agent** (`AI/agent.py`) — Multi-step reasoning agent for complex queries.
- **Chatbot** (`AI/chatbot.py`) — Main chatbot interface that ties everything together.
- **Integration** (`AI/integration.py`) — One-click initialization of all AI components.
- **Config** (`AI/config.py`) — Configuration for models, embeddings, and vector store settings.

### Usage:
- Accessed via Tab 7 in the dashboard.
- Backend initializes on "Initialize AI" click or on first chat message.
- Uses Llama 3.2 (via Ollama or similar) as the LLM behind the RAG pipeline.
- Falls back gracefully if AI components are not fully installed.

---

## 14. Backend API (`backend/main.py`)

### Features:
- **FastAPI REST API** with automatic OpenAPI documentation.
- **RBAC Middleware** — Permission checks on all endpoints.
- **Endpoints:**
  - `/auth/login` — Authenticate users
  - `/organizations` — List organizations (super admin)
  - `/organizations/{id}/users` — List users in an organization
  - `/organizations/{id}/teams` — List teams in an organization
  - `/costs` — Cost data (scoped to user's org)
  - `/recommendations` — Optimization recommendations
- **Basic Auth** for API authentication.
- **Scoped Data Access** — Users only see their own organization's data.

### Usage:
- Launch via `launch.py` which starts both the API and dashboard.
- API docs available at `/docs` when the backend is running.
- Use the FastAPI backend for programmatic access or integration with external tools.

---

## 15. Synthetic Data Generation (`app/data_generator.py`)

### Features:
- `generate_daily_costs(days=180)` — 180 days of cost data across AWS, Azure, GCP with:
  - Seasonal factors (yearly sine wave)
  - Weekend factors (30% lower on Sat/Sun)
  - Trend factors (15% increase over 180 days)
  - Random services, regions, environments, departments
  - Usage quantities and units
- `generate_resource_inventory()` — 200+ resources with:
  - CPU utilization, memory utilization, monthly costs
  - Provider, service, region, environment, department
- `generate_optimization_recommendations()` — Recommendations with categories, impact scores, AI confidence
- `generate_tag_compliance_data()` — Per-resource tag compliance percentages

### Usage:
- Data is auto-generated on first dashboard load with 1-hour cache TTL.
- Click "Refresh Data" in the sidebar to regenerate.
- Synthetic data provides realistic patterns for demo and testing.

---

## 16. Visualization Library (`app/visualizations.py`)

### Features (14 chart types):
| Function | Chart Type | Description |
|----------|------------|-------------|
| `create_cost_trend` | Multi-line | Daily cost trend grouped by provider |
| `create_cost_breakdown_pie` | Pie/Donut | Cost distribution by provider |
| `create_bar_chart` | Bar | Custom bar charts (horizontal/vertical) |
| `create_forecast_chart` | Combo | Historical line + forecast bars |
| `create_anomaly_chart` | Scatter+Line | Cost anomalies highlighted on timeline |
| `create_multi_cloud_comparison` | Grouped Bar | Monthly comparison across providers |
| `create_environment_cost_chart` | Stacked Bar | Cost by environment (Prod/Staging/Dev/QA) |
| `create_utilization_scatter` | Scatter | CPU vs Memory utilization |
| `create_savings_waterfall` | Waterfall | Savings breakdown visualization |
| `create_service_cluster_chart` | Scatter+Cluster | Service clustering visualization |
| `create_animated_cost_trend` | Animated Bar | Cumulative cost growth day-by-day |
| `create_animated_bar_race` | Animated Bar Race | Month-by-month provider cost race |

### Usage:
- All charts use Plotly with dark theme and consistent styling.
- Interactive: hover, zoom, pan, download as PNG.
- Animations have play/pause controls.

---

## 17. Database Layer (`database/`)

### Features:
- **SQLite** via SQLAlchemy ORM.
- **Models** (`database/models.py`):
  - `Organization` — name, slug, description, created_at, is_active
  - `Team` — name, description, org_id (FK)
  - `User` — name, email, password_hash, role, avatar, joined, last_login, is_active, org_id (FK), team_id (FK)
  - `CostData` — date, provider, service, cost, usage, org_id (FK)
  - `ActivityLog` — user_id, action, details, timestamp
  - `Permission` — role, resource_type, action (RBAC rules)
- **Repository** (`database/repository.py`) — Scoped queries for multi-tenancy:
  - `get_org_users(org_id)` — Users within an org
  - `get_teams(org_id)` — Teams within an org
  - `get_user_activities(user_id)` — Activity log for a user
  - `check_permission(role, resource_type, action)` — RBAC check
  - `create_organization()` — Register new org with admin user
- **Seed** (`database/seed.py`) — Pre-seeds 2 organizations, 5 roles, demo users, and permissions.
- **Connection** (`database/connection.py`) — Engine and session factory setup.

### Usage:
- Database auto-creates on first import of `auth.py`.
- Auto-seeds if no organizations exist.
- All queries are scoped by organization ID for data isolation.

---

## 18. Launcher Scripts

### a) `run.py` (Dashboard Only)
- Starts only the Streamlit dashboard on port 8501.
- Opens browser automatically.
- Usage: `python run.py`

### b) `launch.py` (Full Stack)
- Starts the Streamlit dashboard + logs output to `launch_log.txt`.
- Also capable of starting the FastAPI backend (if configured).
- Usage: `python launch.py`

---

## Tech Stack Summary

| Category | Technologies |
|----------|-------------|
| Frontend | Streamlit, Plotly, Custom CSS/Animations |
| Backend | FastAPI (REST) |
| Database | SQLite, SQLAlchemy ORM |
| ML | scikit-learn (Isolation Forest, KMeans, DBSCAN), XGBoost, TensorFlow/Keras (Autoencoder), Facebook Prophet |
| AI | LangChain, ChromaDB, Llama 3.2 (Ollama), RAG Pipeline |
| Auth | SHA-256 password hashing, Session-based, Role-Based Access Control |
| Data | Pandas, NumPy, Synthetic data generators |

---

## Quick Start Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Launch Streamlit dashboard only
python run.py

# Launch full stack (dashboard + API + AI)
python launch.py

# Test RBAC permissions
python test_rbac.py