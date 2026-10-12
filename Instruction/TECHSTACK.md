# NetRCA — Technical Stack Specification

## 1. Overview

**NetRCA** is an AI-powered Network Root Cause Analysis and Incident Response System.

This document defines the complete technology stack, responsibilities, architecture boundaries, libraries, infrastructure, development tools, security requirements, testing stack, and feature-to-technology mapping for the project.

The stack is intentionally focused on technologies that directly support the NetRCA architecture:

```text
Mininet
   ↓
Python
   ↓
Pandas / NumPy
   ↓
Scikit-learn
   ↓
NetworkX
   ↓
RCA Engine
   ↓
Gemini API
   ↓
FastAPI
   ↓
Supabase / PostgreSQL
   ↓
Next.js / React
   ↓
Tailwind CSS + Recharts + React Flow
```

---

# 2. Final Technology Stack

| Layer | Technology | Primary Purpose |
|---|---|---|
| Network Simulation | **Mininet** | Simulated network environment |
| Main Language | **Python** | Network collection, ML, RCA, backend |
| Data Processing | **Pandas** | Data cleaning and transformation |
| Numerical Computing | **NumPy** | Numerical operations and feature processing |
| Machine Learning | **Scikit-learn** | Anomaly detection |
| Graph Analysis | **NetworkX** | Network topology and dependency analysis |
| AI | **Gemini API** | Explanation, summarization, recommendations |
| Backend | **FastAPI** | REST API and application backend |
| Validation | **Pydantic** | API schemas and data validation |
| Database | **Supabase / PostgreSQL** | Persistent storage |
| Frontend | **Next.js / React** | Web dashboard |
| Styling | **Tailwind CSS** | Dashboard UI |
| Charts | **Recharts** | Metrics and analytics visualization |
| Topology UI | **React Flow** | Interactive network topology |
| HTTP Client | **httpx / fetch** | Backend/API communication |
| Testing | **pytest** | Python/backend testing |
| Frontend Testing | **Vitest / React Testing Library** | UI/component testing |
| Version Control | **Git + GitHub** | Source control |
| Configuration | **python-dotenv / environment variables** | Secret/config management |
| Documentation | **Markdown** | Project documentation |

---

# 3. Architecture Stack

```text
┌────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                       │
│              Next.js + React + Tailwind CSS                │
│             Recharts + React Flow + TypeScript             │
└───────────────────────────┬────────────────────────────────┘
                            │
                            │ REST / JSON
                            ▼
┌────────────────────────────────────────────────────────────┐
│                         API LAYER                           │
│                         FastAPI                             │
│                    Pydantic Validation                      │
└───────────────────────────┬────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────┐
│                      APPLICATION LAYER                     │
│                                                            │
│ Monitoring │ Anomaly │ Correlation │ RCA │ Impact │ AI     │
└───────────────┬─────────────────────┬──────────────────────┘
                │                     │
                ▼                     ▼
        ┌───────────────┐     ┌────────────────┐
        │ Python + ML   │     │   Gemini API   │
        │ NetworkX      │     │ Explanation    │
        └───────┬───────┘     └────────────────┘
                │
                ▼
┌────────────────────────────────────────────────────────────┐
│                    DATA / NETWORK LAYER                    │
│                                                            │
│      Mininet                         Supabase/PostgreSQL   │
│      Network                         Persistent Storage    │
└────────────────────────────────────────────────────────────┘
```

---

# 4. Network Simulation Stack

## Technology: Mininet

Mininet is the primary network simulation environment.

### Purpose

It provides the controlled environment in which NetRCA observes network behavior.

### Used For

- Virtual hosts
- Virtual switches
- Virtual routers where configured
- Network links
- Network topology
- Bandwidth constraints
- Latency
- Packet loss
- Network congestion
- Traffic generation
- Fault injection
- Failure recovery

### Example

```text
                R1
               /  \
             S1    S2
            /  \    \
       Server1 Server2 DNS
```

### Why Mininet

NetRCA is a network-analysis project, so the simulation layer needs to model actual network relationships rather than only generating arbitrary numerical data.

---

# 5. Python

## Technology: Python 3.x

Python is the main engineering language.

### Responsibilities

- Mininet integration
- Network monitoring
- Data collection
- Data processing
- Feature engineering
- Machine learning
- Event generation
- Event correlation
- RCA engine
- Impact analysis
- Gemini integration
- FastAPI backend

### Suggested Project Style

Use:

```text
PEP 8
Type hints
Modular services
Environment-based configuration
Unit tests
```

---

# 6. NumPy

## Technology: NumPy

### Purpose

Numerical computing and feature manipulation.

### Used For

- Numeric arrays
- Statistical calculations
- Feature transformations
- ML preprocessing
- Metric calculations

Example metrics:

```text
Latency
Packet Loss
Throughput
Error Rate
CPU
Memory
```

---

# 7. Pandas

## Technology: Pandas

### Purpose

Network-data processing.

### Used For

- Cleaning metrics
- Processing logs
- Creating feature datasets
- Aggregating time windows
- Preparing ML input
- Historical analysis
- Experiment evaluation

Example:

```text
timestamp | device | latency | packet_loss | errors
------------------------------------------------------
10:31:01  | R1     | 24      | 0.2         | 1
10:31:02  | R1     | 26      | 0.1         | 0
10:31:03  | R1     | 310     | 24.0        | 35
```

---

# 8. Scikit-learn

## Technology: Scikit-learn

### Primary Purpose

Machine-learning based anomaly detection.

### Initial Algorithm

**Isolation Forest**

### Inputs

```text
latency
packet_loss
throughput
bandwidth
error_rate
cpu
memory
availability
```

### Outputs

```text
anomaly_score
is_anomaly
severity
```

### ML Architecture

```text
Raw Metrics
     ↓
Pandas
     ↓
Feature Engineering
     ↓
Scikit-learn
     ↓
Anomaly Score
     ↓
Anomaly Event
```

### Future Algorithms

Optional future experiments may include:

- Random Forest
- Logistic Regression
- One-Class SVM
- Local Outlier Factor
- Neural Network

The MVP should not require all of these.

---

# 9. NetworkX

## Technology: NetworkX

### Purpose

Represent and analyze network topology as a graph.

### Graph Model

```text
Node = Device
Edge = Network Link
```

### Nodes

```text
Router
Switch
Server
Host
DNS
```

### Edges

```text
R1 ─ S1
S1 ─ Server1
```

### Used For

- Topology representation
- Path analysis
- Dependency analysis
- Upstream/downstream analysis
- Affected-device identification
- Failure propagation
- Root-cause reasoning

---

# 10. Root Cause Analysis Engine

The RCA engine is a custom Python application layer rather than a third-party technology.

### Inputs

```text
Metrics
Logs
Events
Anomalies
Topology
Timestamps
Dependencies
Fault information
```

### Processing

```text
Collect Evidence
       ↓
Create Timeline
       ↓
Correlate Events
       ↓
Map Events to Topology
       ↓
Generate Candidate Causes
       ↓
Evaluate Evidence
       ↓
Calculate Confidence
       ↓
Return Root Cause
```

### Output

```text
Root Cause
Confidence
Evidence
Affected Components
Failure Chain
```

---

# 11. Event Correlation Technology

Event correlation will initially be implemented with Python logic.

### Correlation Signals

- Timestamp proximity
- Event sequence
- Shared device
- Shared link
- Network topology
- Dependency
- Metric relationships

### Example

```text
R1 failure
    ↓ 1 sec
Packet loss
    ↓ 1 sec
Latency increase
    ↓ 1 sec
Server timeout
```

The correlation engine groups these events into one incident.

---

# 12. Gemini API

## Technology: Gemini API

Gemini is the generative AI layer.

### Responsibilities

- Incident explanation
- RCA explanation
- Failure-chain explanation
- Impact summary
- Troubleshooting recommendations
- Human-readable incident reports
- Technical question answering about an incident

### Gemini Input

Gemini should receive structured evidence instead of raw unrestricted system access.

Example:

```json
{
  "root_cause": "R1 interface failure",
  "confidence": 0.92,
  "affected_devices": ["S1", "Server1", "Server2"],
  "events": [
    "R1 interface failure",
    "packet loss",
    "high latency",
    "server timeout"
  ],
  "evidence": [
    "R1 error occurred first",
    "Packet loss increased afterward",
    "R1 is an upstream dependency"
  ]
}
```

### Gemini Output

```text
Explanation
Recommendation
Incident Summary
```

### Important Rule

Gemini is **not the sole RCA engine**.

The architecture should be:

```text
ML + topology + event correlation
              ↓
       Structured RCA
              ↓
          Gemini
              ↓
     Explanation / Advice
```

This preserves deterministic evidence and makes the system easier to evaluate.

---

# 13. FastAPI

## Technology: FastAPI

FastAPI is the backend API framework.

### Responsibilities

- REST API
- Request validation
- Response serialization
- Authentication integration if added
- Network control endpoints
- Metrics endpoints
- Incident endpoints
- RCA endpoints
- AI endpoints
- Fault injection endpoints

### API Groups

```text
/api/network
/api/topology
/api/metrics
/api/logs
/api/events
/api/anomalies
/api/incidents
/api/root-causes
/api/impact
/api/recommendations
/api/faults
/api/ai
```

---

# 14. Pydantic

## Technology: Pydantic

Used by FastAPI for structured request/response validation.

### Example Models

```text
DeviceCreate
MetricResponse
EventResponse
IncidentResponse
RootCauseResponse
RecommendationResponse
FaultInjectionRequest
AIAnalysisResponse
```

### Benefits

- Type safety
- Validation
- Consistent API contracts
- Clear error responses

---

# 15. Supabase

## Technology: Supabase

Supabase provides the PostgreSQL database and supporting backend capabilities.

### Primary Use

Persistent storage for:

```text
devices
links
services
device_services
metrics
logs
events
anomalies
incidents
incident_events
root_causes
root_cause_evidence
impact_records
recommendations
ai_analyses
fault_injections
topology_snapshots
```

### Why Supabase

- PostgreSQL
- Managed database
- SQL support
- Authentication capability if required later
- API access
- Dashboard
- Convenient development workflow

---

# 16. PostgreSQL

Supabase uses PostgreSQL as the relational database.

### Database Responsibilities

- Persistent network data
- Time-series-like metric storage
- Incident records
- RCA evidence
- AI analysis records
- Recommendations
- Fault history
- Historical analysis

### Important Data Principles

```text
Raw Data ≠ Derived Data
RCA Result ≠ Gemini Explanation
Incident ≠ Event
Symptom ≠ Root Cause
```

These should remain separate in the database.

---

# 17. Next.js / React

## Technology

- Next.js
- React
- TypeScript

### Responsibilities

- Dashboard
- Network overview
- Incident center
- RCA investigation
- Topology visualization
- Metrics
- Logs
- Fault injection UI
- AI explanation
- Recommendations
- Historical analytics

---

# 18. TypeScript

TypeScript is recommended for the frontend.

### Used For

- API types
- Component props
- Dashboard state
- Network topology data
- Incident objects
- Metric objects
- RCA results

Example:

```typescript
type Incident = {
  id: string;
  title: string;
  severity: string;
  status: string;
  confidence?: number;
  rootCause?: string;
};
```

---

# 19. Tailwind CSS

## Technology: Tailwind CSS

Used for dashboard styling.

### UI Requirements

- Responsive layout
- Cards
- Tables
- Status badges
- Incident panels
- Metric cards
- Modal dialogs
- Filters
- Navigation
- Dark/light UI support if desired

---

# 20. Recharts

## Technology: Recharts

Used for network metric visualization.

### Charts

- Latency over time
- Packet loss over time
- Throughput
- Bandwidth
- Error rate
- CPU utilization
- Memory
- Incident frequency
- Anomaly frequency

---

# 21. React Flow

## Technology: React Flow

Recommended for interactive network topology.

### Features

- Network nodes
- Network edges
- Device status
- Failed node highlighting
- Affected node highlighting
- Interactive topology
- Zoom
- Pan
- Node details

Example:

```text
       🔴 R1
        │
        S1
       /  \
   Server1 Server2
```

---

# 22. HTTP Communication

### Backend

FastAPI exposes REST/JSON endpoints.

### Frontend

Use:

```text
fetch
```

or:

```text
httpx
```

depending on whether communication is frontend-side or Python-side.

### Communication Flow

```text
React
  ↓ HTTP/JSON
FastAPI
  ↓
Services
  ↓
Database / ML / Gemini / Mininet
```

---

# 23. Real-Time Updates

The initial MVP can use polling for simplicity.

Example:

```text
Frontend
   ↓
GET /api/metrics
   ↓
Every few seconds
```

For a more advanced version, use:

- WebSockets
- Server-Sent Events

### Recommended Development Order

```text
MVP → Polling
Future → WebSockets/SSE
```

Do not add real-time infrastructure before the core system works.

---

# 24. Fault Injection Technology

Fault injection will be implemented with Python + Mininet.

### Faults

```text
Router Failure
Interface Failure
Switch Failure
Link Failure
Packet Loss
High Latency
Congestion
DNS Failure
Server Overload
Server Unavailable
High Error Rate
Bandwidth Reduction
```

### Flow

```text
Dashboard
    ↓
FastAPI
    ↓
Fault Service
    ↓
Mininet
    ↓
Network Failure
```

---

# 25. Logging

### Application Logging

Use Python's standard logging system initially.

Log:

```text
API calls
Network events
Collector errors
ML execution
RCA execution
Gemini calls
Database errors
Fault injection
```

### Log Levels

```text
DEBUG
INFO
WARNING
ERROR
CRITICAL
```

---

# 26. Environment Configuration

Sensitive configuration must use environment variables.

### Example

```text
GEMINI_API_KEY=
SUPABASE_URL=
SUPABASE_KEY=
DATABASE_URL=
```

### `.env.example`

The repository should include:

```text
.env.example
```

but never commit real secrets.

---

# 27. Git and GitHub

## Git

Used for:

- Version control
- Branching
- Local history
- Reverting changes

## GitHub

Used for:

- Remote repository
- Collaboration
- Issue tracking
- Pull requests
- Project documentation
- Source-code backup

### Suggested branches

```text
main
develop
feature/network
feature/ml
feature/rca
feature/frontend
```

For a small student project, a simpler:

```text
main
feature/*
```

workflow is sufficient.

---

# 28. Testing Stack

## Backend

**pytest**

Test:

- Data processing
- Anomaly detection
- Event correlation
- RCA
- Impact analysis
- API endpoints
- Fault injection

## Frontend

**Vitest + React Testing Library**

Test:

- Dashboard components
- Incident cards
- Metric components
- Filters
- RCA display

## Integration Testing

Validate:

```text
Mininet
 ↓
Collector
 ↓
ML
 ↓
RCA
 ↓
Supabase
 ↓
FastAPI
 ↓
Frontend
```

---

# 29. Development Environment

## Recommended

```text
Operating System:
Ubuntu Linux / WSL2
```

Mininet is primarily designed around Linux networking functionality.

### Development Tools

- VS Code
- Git
- GitHub
- Python
- Node.js
- npm/pnpm
- PostgreSQL/Supabase
- Mininet

### Windows Users

If developing on Windows, **WSL2 with Ubuntu** is recommended for the Mininet environment.

---

# 30. Docker

Docker is **not the primary network simulator**.

### Primary Network Environment

```text
Mininet
```

### Docker's Optional Role

Docker can later be used for:

- Backend packaging
- Frontend deployment
- Supporting services
- Reproducible development environments
- CI/CD

### Important

Do not replace Mininet with Docker for the core network simulation.

---

# 31. Security Stack

### API Keys

Gemini keys stay on the backend.

```text
Frontend
   X
   │
   │ Gemini API key
   │
   X
```

Instead:

```text
Frontend
   ↓
FastAPI
   ↓
Gemini
```

### Database Security

- Keep Supabase credentials protected
- Use server-side privileged keys only where necessary
- Never expose sensitive keys in frontend code
- Use environment variables
- Apply database access policies if authentication is introduced

---

# 32. AI Safety Architecture

NetRCA should only operate automatically inside the controlled simulation.

### AI Can

- Explain incidents
- Analyze structured evidence
- Recommend troubleshooting steps
- Generate reports

### AI Should Not

- Directly modify real production networks
- Execute destructive commands
- Scan unauthorized networks
- Automatically apply dangerous network changes

---

# 33. Feature-to-Technology Mapping

| Feature | Technology |
|---|---|
| Network simulation | Mininet |
| Virtual devices | Mininet |
| Network topology | Mininet + NetworkX |
| Traffic generation | Mininet/Linux networking tools |
| Fault injection | Python + Mininet |
| Metric collection | Python |
| Log collection | Python |
| Data processing | Pandas + NumPy |
| Feature engineering | Pandas + NumPy |
| Anomaly detection | Scikit-learn |
| Anomaly scoring | Scikit-learn |
| Event generation | Python |
| Event correlation | Python |
| Topology reasoning | NetworkX |
| Root-cause analysis | Custom Python RCA engine |
| Failure propagation | NetworkX + RCA engine |
| Impact analysis | Python + NetworkX |
| AI explanation | Gemini API |
| AI recommendation | Gemini API |
| Incident reports | Gemini API + FastAPI |
| API | FastAPI |
| API validation | Pydantic |
| Database | Supabase/PostgreSQL |
| Metric visualization | Recharts |
| Network visualization | React Flow |
| Dashboard | Next.js + React |
| Styling | Tailwind CSS |
| Frontend language | TypeScript |
| Version control | Git |
| Remote repository | GitHub |
| Backend testing | pytest |
| Frontend testing | Vitest + RTL |
| Secrets | Environment variables |

---

# 34. Feature Inventory

## Network Features

- Virtual network creation
- Router simulation
- Switch simulation
- Server simulation
- Host simulation
- DNS simulation
- Topology configuration
- Link configuration
- Bandwidth configuration
- Latency configuration
- Packet-loss configuration
- Traffic generation
- Device status
- Link status

## Monitoring Features

- Real-time metrics
- Historical metrics
- Device monitoring
- Link monitoring
- Availability monitoring
- Error monitoring
- Interface monitoring
- Throughput monitoring
- Bandwidth monitoring
- Latency monitoring
- Packet-loss monitoring

## Logging Features

- Log collection
- Log parsing
- Log severity
- Live logs
- Log search
- Log filtering
- Incident association

## Event Features

- Event generation
- Event classification
- Event severity
- Event timeline
- Event correlation
- Incident grouping

## Machine Learning Features

- Anomaly detection
- Anomaly scoring
- Feature extraction
- Model versioning
- Historical anomaly storage
- False-positive evaluation
- Detection performance evaluation

## RCA Features

- Candidate cause detection
- Root-cause identification
- Confidence estimation
- Evidence collection
- Timeline analysis
- Topology-based reasoning
- Dependency analysis
- Symptom/root-cause separation
- Failure-chain reconstruction

## Impact Features

- Affected-device identification
- Affected-link identification
- Affected-service identification
- Impact severity
- Impact duration
- Service disruption tracking

## Gemini Features

- Incident explanation
- RCA explanation
- Failure-chain explanation
- Impact summary
- Troubleshooting recommendation
- Incident report generation
- Technical incident Q&A

## Fault Injection Features

- Router failure
- Interface failure
- Switch failure
- Link failure
- Packet loss
- High latency
- Network congestion
- DNS failure
- Server overload
- Server unavailable
- High error rate
- Bandwidth reduction
- Fault recovery

## Incident Features

- Incident creation
- Incident status
- Incident severity
- Incident timeline
- Root cause
- Confidence
- Evidence
- Impact
- Recommendations
- Incident history
- Incident search
- Incident filtering
- Resolution tracking

## Dashboard Features

- Network health
- Live metrics
- Interactive topology
- Active incidents
- Incident details
- RCA investigation
- Failure chain
- Logs
- Historical analytics
- Charts
- Search
- Filters
- AI explanation
- Recommendations

## Database Features

- Device storage
- Link storage
- Service storage
- Metric storage
- Log storage
- Event storage
- Anomaly storage
- Incident storage
- RCA storage
- Evidence storage
- Impact storage
- Recommendation storage
- AI-analysis storage
- Fault-injection history
- Topology snapshots

## Security Features

- Backend-only Gemini access
- Environment variables
- Protected database credentials
- Controlled fault injection
- Human-reviewed recommendations
- No unauthorized network operations

---

# 35. Recommended Python Dependencies

A starting backend environment can include:

```text
fastapi
uvicorn
pydantic
python-dotenv
pandas
numpy
scikit-learn
networkx
httpx
pytest
```

Additional packages should only be added when a concrete feature requires them.

---

# 36. Recommended Frontend Dependencies

A starting frontend can include:

```text
next
react
typescript
tailwindcss
recharts
reactflow
```

Additional UI libraries are optional and should not be added unnecessarily.

---

# 37. Suggested Service Boundaries

The backend should be modular:

```text
backend/
│
├── api/
│
├── services/
│   ├── network_service.py
│   ├── monitoring_service.py
│   ├── anomaly_service.py
│   ├── correlation_service.py
│   ├── rca_service.py
│   ├── impact_service.py
│   ├── incident_service.py
│   ├── recommendation_service.py
│   └── ai_service.py
│
├── agents/
│
├── rca/
│
├── anomaly/
│
├── topology/
│
├── monitoring/
│
└── models/
```

This prevents the project from becoming one large Python file.

---

# 38. Data Flow by Technology

```text
                 MININET
                    │
                    │ network data
                    ▼
                 PYTHON
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
       PANDAS              NUMPY
          │                   │
          └─────────┬─────────┘
                    ▼
              SCIKIT-LEARN
                    │
                    │ anomaly
                    ▼
                NETWORKX
                    │
                    │ topology
                    ▼
              RCA ENGINE
                    │
                    ├──────────────► SUPABASE
                    │
                    ▼
                GEMINI API
                    │
                    ▼
                 FASTAPI
                    │
                    ▼
            NEXT.JS / REACT
                    │
              ┌─────┴─────┐
              ▼           ▼
          RECHARTS    REACT FLOW
```

---

# 39. MVP Technology Scope

The first working release should use only:

```text
Mininet
Python
NumPy
Pandas
Scikit-learn
NetworkX
Gemini API
FastAPI
Pydantic
Supabase/PostgreSQL
Next.js
React
TypeScript
Tailwind CSS
Recharts
React Flow
Git/GitHub
pytest
```

Avoid adding:

```text
Kafka
Redis
Kubernetes
microservices
multiple databases
multiple LLM providers
complex cloud infrastructure
```

until the core project is working.

---

# 40. Future Technology Extensions

Optional future technologies may include:

### Real-Time Streaming
- WebSockets
- Server-Sent Events

### Caching
- Redis

### Message Streaming
- Apache Kafka

### Advanced ML
- PyTorch
- TensorFlow

### Advanced Graph AI
- PyTorch Geometric
- Graph Neural Networks

### Observability
- Prometheus
- Grafana

### Deployment
- Docker
- CI/CD
- Cloud hosting

These are future enhancements, not MVP requirements.

---

# 41. Recommended Implementation Order

## Phase 1 — Environment

Install:

```text
Ubuntu / WSL2
Python
Mininet
Node.js
Git
```

## Phase 2 — Network

Build:

```text
R1
S1
S2
Server1
Server2
DNS
```

## Phase 3 — Monitoring

Implement:

```text
Latency
Packet Loss
Bandwidth
Throughput
Errors
Logs
```

## Phase 4 — Fault Injection

Implement:

```text
Router Failure
Link Failure
Packet Loss
High Latency
DNS Failure
Server Overload
```

## Phase 5 — ML

Implement:

```text
Feature Engineering
Isolation Forest
Anomaly Scoring
```

## Phase 6 — RCA

Implement:

```text
Event Correlation
NetworkX Topology
Failure Propagation
Root Cause
Confidence
Evidence
```

## Phase 7 — Gemini

Implement:

```text
Incident Explanation
Recommendation
Report Generation
```

## Phase 8 — Backend

Implement FastAPI endpoints.

## Phase 9 — Database

Implement Supabase schema and persistence.

## Phase 10 — Dashboard

Implement:

```text
Network Overview
Metrics
Topology
Incidents
RCA
Logs
AI Explanation
Recommendations
```

## Phase 11 — Testing

Run controlled fault scenarios and evaluate the results.

---

# 42. Final Recommended Stack

```text
┌─────────────────────────────────────────────┐
│                  FRONTEND                   │
│                                             │
│ Next.js + React + TypeScript                │
│ Tailwind CSS                                │
│ Recharts                                    │
│ React Flow                                  │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│                   BACKEND                   │
│                                             │
│ FastAPI + Pydantic                          │
└──────────────────────┬──────────────────────┘
                       │
        ┌──────────────┼───────────────┐
        ▼              ▼               ▼
   RCA Engine      Gemini API      Supabase
        │                              │
   ┌────┴─────┐                        │
   ▼          ▼                        │
Scikit-     NetworkX                   │
learn                                  │
   │                                    │
   └──────────────┬─────────────────────┘
                  │
                  ▼
            Python + Pandas
                  │
                  ▼
               Mininet
```

---

# 43. Final Technology Decisions

### Required

- **Mininet** — network simulation
- **Python** — core language
- **NumPy** — numerical processing
- **Pandas** — data processing
- **Scikit-learn** — anomaly detection
- **NetworkX** — topology/RCA support
- **Gemini API** — AI explanation/recommendation
- **FastAPI** — backend
- **Pydantic** — API validation
- **Supabase/PostgreSQL** — database
- **Next.js/React** — frontend
- **TypeScript** — frontend type safety
- **Tailwind CSS** — UI
- **Recharts** — metrics visualization
- **React Flow** — topology visualization
- **Git/GitHub** — source control
- **pytest** — backend testing

### Optional

- Docker
- WebSockets/SSE
- Redis
- Prometheus
- Grafana
- PyTorch
- Graph Neural Networks

These should only be introduced when the core system requires them.

---

# 44. Final Architecture Principle

The most important technical decision in NetRCA is to avoid making it simply an LLM application.

The intelligence pipeline should be:

```text
             NETWORK
                ↓
             MININET
                ↓
        DATA COLLECTION
                ↓
        DATA PROCESSING
                ↓
       MACHINE LEARNING
                ↓
       ANOMALY DETECTION
                ↓
       EVENT CORRELATION
                ↓
       NETWORK TOPOLOGY
                ↓
        ROOT CAUSE ENGINE
                ↓
         IMPACT ANALYSIS
                ↓
            GEMINI
                ↓
        EXPLANATION + AI
        RECOMMENDATION
                ↓
             FASTAPI
                ↓
            SUPABASE
                ↓
        NEXT.JS DASHBOARD
```

This architecture gives NetRCA a clear separation between **network simulation, measurable data, machine learning, graph reasoning, root-cause analysis, generative AI, persistence, and user interface**.
