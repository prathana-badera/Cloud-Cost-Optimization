# Cloud Cost Optimizer

Multi-cloud (AWS, Azure, GCP) cost monitoring, analysis, and optimization dashboard with **Multi-Tenant Organization & Role-Based Access Control (RBAC)**.

## Quick Start

```bash
pip install -r requirements.txt
python run.py          # Opens Streamlit dashboard
python launch.py       # Full stack (backend + AI + dashboard)
```

## Demo Credentials

| Role | Email | Password | Permissions |
|------|-------|----------|-------------|
| 👑 **Super Admin** | `superadmin@cloudopt.com` | `superadmin123` | All organizations, all permissions |
| 👨‍💼 **Org Admin** | `admin@cloudopt-inc.com` | `admin123` | Manage users, teams, settings within org |
| 👩‍🔧 **Team Lead** | `devops@cloudopt-inc.com` | `devops123` | Approve recommendations, read costs |
| 🧑‍💻 **Optimizer** | `optimizer@cloudopt-inc.com` | `opt123` | Create recommendations, read costs |
| 👤 **Viewer** | `viewer@cloudopt-inc.com` | `view123` | Read-only access to all data |

Two demo organizations are pre-seeded: **CloudOpt Inc.** and **Acme Corp**. You can also register new organizations from the login page.

## Project Structure

| Module | Purpose |
|--------|---------|
| `app/` | Streamlit dashboard (auth, cost analysis, visualizations, profile, admin) |
| `AI/` | NLP chatbot, RAG pipeline, embeddings for querying cost data |
| `backend/` | FastAPI REST API with RBAC middleware |
| `database/` | SQLite models, connection, seeding, repository (org-scoped queries) |
| `ml/` | Forecasting, anomaly detection, clustering |

## New Features: Multi-Tenant Organization & RBAC

### Multi-Tenancy
- **Organizations** — Each company/team gets an isolated organization with its own data
- **Teams** — Create departments (Engineering, DevOps, Finance, etc.) within organizations
- **Data Isolation** — All cost data, resources, and recommendations are scoped to an organization

### Role-Based Access Control (5 Roles)

| Role | Costs | Users | Teams | Settings | Recommendations |
|------|-------|-------|-------|----------|----------------|
| **super_admin** | ✅ All | ✅ All | ✅ All | ✅ All | ✅ All |
| **org_admin** | ✅ Read/Write | ✅ Full | ✅ Full | ✅ Full | ✅ Approve |
| **team_lead** | ✅ Read/Write | ✅ Read | ✅ Read | ✅ Read | ✅ Approve |
| **optimizer** | ✅ Read/Write | ✅ Read | ✅ Read | ✅ Read | ✅ Write |
| **viewer** | ✅ Read | ✅ Read | ✅ Read | ✅ Read | ✅ Read |

### Admin Dashboard
- **User Management** — Create, edit roles, deactivate users
- **Team Management** — Create/rename/delete teams
- **Org Settings** — Update organization name and description
- **Super Admin View** — See all organizations in the system

### Database-Backed Authentication
- Replaced in-memory `DEMO_USERS` dict with SQLite-backed users
- Password hashing with SHA-256
- Activity tracking for all user actions
- Organization registration from login page
- Secure session management

### API Authentication
- Basic Auth for all API endpoints
- Scoped data access per organization
- New endpoints: `/auth/login`, `/organizations`, `/organizations/{id}/users`, `/organizations/{id}/teams`

## Capabilities

- **Multi-Tenant Organization & RBAC** — Isolated data, role-based permissions
- **Cost Analysis** — Spend breakdown by service/region/account/tag
- **Rightsizing** — Instance type recommendations from utilization data
- **Anomaly Detection** — Unusual spending patterns flagged via ML (Isolation Forest, XGBoost, Autoencoder)
- **Forecasting** — ML-based cost prediction (Prophet, XGBoost, Linear Regression)
- **Chatbot** — Natural language queries over cost data (RAG)
- **Cleanup** — Automated detection of idle/unused resources
- **Governance** — Tag compliance, budget policies, approval workflows

## Tech Stack

Python, Streamlit, FastAPI, scikit-learn, Plotly, Pandas, LangChain, ChromaDB, Prophet, SQLite, SQLAlchemy

## License

MIT