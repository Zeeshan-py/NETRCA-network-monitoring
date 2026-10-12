# NetRCA — System Architecture Document

## 1. Architecture Overview

**NetRCA** (AI-Powered Network Root Cause Analysis and Incident Response System) is designed as a modular, event-driven platform.

Its architecture separates:

1. Network simulation
2. Data collection
3. Data processing
4. Anomaly detection
5. Event correlation
6. Network topology analysis
7. Root-cause analysis
8. Impact analysis
9. Gemini-powered explanation
10. Recommendation generation
11. Incident management
12. Persistent storage
13. Backend APIs
14. Web dashboard

### Core Architecture Principle

```text
OBSERVE
   ↓
COLLECT
   ↓
PROCESS
   ↓
DETECT
   ↓
CORRELATE
   ↓
DIAGNOSE
   ↓
ANALYZE IMPACT
   ↓
EXPLAIN
   ↓
RECOMMEND
   ↓
DISPLAY / STORE
```

---

# 2. High-Level System Architecture

```text
┌──────────────────────────────────────────────────────────────────┐
│                         NETRCA PLATFORM                          │
└──────────────────────────────────────────────────────────────────┘

                         ┌───────────────┐
                         │    MININET    │
                         │ Virtual Net   │
                         └───────┬───────┘
                                 │
                    Metrics / Logs / Events
                                 │
                                 ▼
                    ┌─────────────────────┐
                    │  DATA COLLECTION    │
                    │       Python        │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ DATA PROCESSING     │
                    │ Cleaning / Features │
                    └──────────┬──────────┘
                               │
                ┌──────────────┼──────────────┐
                ▼              ▼              ▼
       ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
       │  Anomaly    │ │    Logs     │ │  Topology   │
       │  Detection  │ │   Analysis  │ │   NetworkX  │
       │ Scikit-learn│ │             │ │             │
       └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
              │               │               │
              └───────────────┼───────────────┘
                              ▼
                    ┌─────────────────────┐
                    │ EVENT CORRELATION   │
                    │ Time + Topology +   │
                    │ Dependencies        │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ ROOT CAUSE ENGINE   │
                    │ Evidence + Ranking  │
                    └──────────┬──────────┘
                               │
                 ┌─────────────┴─────────────┐
                 ▼                           ▼
       ┌─────────────────┐         ┌──────────────────┐
       │ IMPACT ANALYSIS │         │    GEMINI API    │
       │ Affected Nodes  │         │ Explanation +    │
       │ Services / Links│         │ Recommendations  │
       └────────┬────────┘         └────────┬─────────┘
                │                           │
                └─────────────┬─────────────┘
                              ▼
                    ┌─────────────────────┐
                    │      FASTAPI        │
                    │    API BACKEND      │
                    └───────┬─────┬───────┘
                            │     │
              ┌─────────────┘     └──────────────┐
              ▼                                  ▼
       ┌─────────────┐                   ┌─────────────────┐
       │  SUPABASE   │                   │ React / Next.js │
       │ PostgreSQL  │                   │    Dashboard    │
       └─────────────┘                   └─────────────────┘
```

---

# 3. Architectural Layers

## Layer 1 — Network Simulation Layer

### Technology
- Mininet

### Responsibility

Provides the controlled network environment observed by NetRCA.

### Components

- Virtual hosts
- Virtual switches
- Virtual routers
- Network links
- DNS service
- Application/server nodes

### Capabilities

- Create network topology
- Configure links
- Configure bandwidth
- Configure latency
- Configure packet loss
- Start/stop network
- Generate network traffic
- Inject controlled faults
- Recover from faults

---

# 4. Network Topology Layer

Network topology is represented as a graph.

### Technology
- NetworkX

### Graph Model

```text
Node = Network Component
Edge = Network Connection
```

### Node Types

```text
Router
Switch
Server
Host
DNS
Service
```

### Edge Information

```text
Source
Destination
Bandwidth
Latency
Packet Loss
Status
```

### Responsibilities

- Maintain network relationships
- Determine upstream/downstream components
- Calculate paths
- Find affected nodes
- Support event correlation
- Support failure propagation analysis
- Support root-cause analysis

---

# 5. Data Collection Layer

### Technology
- Python

This layer collects information from Mininet and converts it into structured records.

### Data Sources

```text
Mininet
   │
   ├── Network Metrics
   ├── Logs
   ├── Events
   ├── Device Status
   └── Link Status
```

### Collected Metrics

- Latency
- Packet loss
- Bandwidth
- Throughput
- CPU utilization where available
- Memory utilization where available
- Error rate
- Connection failures
- Interface status
- Availability

### Collector Responsibilities

- Poll network components
- Timestamp measurements
- Normalize measurements
- Detect collection errors
- Forward data to processing pipeline

---

# 6. Data Processing Layer

Before AI analysis, raw network data is converted into structured information.

### Responsibilities

- Data cleaning
- Missing-value handling
- Normalization
- Timestamp normalization
- Feature extraction
- Metric aggregation
- Window-based analysis
- Event generation

### Example

Raw observations:

```text
10:31:01 latency=25
10:31:02 latency=27
10:31:03 latency=310
```

Processed result:

```text
Metric: latency
Device: R1
Normal Range: 20–40 ms
Observed: 310 ms
Status: ANOMALY
```

---

# 7. Anomaly Detection Layer

### Technology
- Python
- Scikit-learn

### Purpose

Identify network behavior that significantly differs from expected behavior.

### Initial Model

- Isolation Forest

### Inputs

```text
Latency
Packet Loss
Throughput
Bandwidth
Error Rate
CPU
Memory
Availability
```

### Outputs

```text
Anomaly Status
Anomaly Score
Timestamp
Device
Metric
Severity
```

### Example

```text
Device: R1
Metric: Packet Loss
Observed: 24%
Expected: <1%

Result: ANOMALY
```

---

# 8. Log Analysis Layer

This layer processes system and network logs.

### Responsibilities

- Parse logs
- Identify severity
- Extract device
- Extract event type
- Extract timestamps
- Detect error patterns
- Associate logs with incidents

### Log Structure

```text
log_id
timestamp
device_id
severity
event_type
message
source
```

### Severity

```text
INFO
WARNING
ERROR
CRITICAL
```

---

# 9. Event Processing Layer

Important changes in network state are converted into structured events.

### Event Examples

```text
Router Interface Failure
Packet Loss Detected
High Latency
DNS Failure
Server Timeout
Link Failure
Network Congestion
Server Overload
Device Unavailable
Service Failure
```

### Event Structure

```text
event_id
timestamp
device_id
event_type
severity
metric
observed_value
expected_value
status
```

---

# 10. Event Correlation Engine

This is one of the most important components of NetRCA.

The engine determines whether multiple events are related.

### Correlation Signals

1. Temporal relationship
2. Network topology
3. Device dependency
4. Metric relationship
5. Event sequence
6. Shared affected components

### Example

```text
10:31:05 R1 interface failure
        ↓
10:31:06 packet loss
        ↓
10:31:07 high latency
        ↓
10:31:08 server timeout
```

The system groups these events into one probable incident.

---

# 11. Root Cause Analysis Engine

The RCA engine identifies the most probable underlying cause.

### Inputs

```text
Anomalies
Logs
Events
Topology
Timestamps
Dependencies
Failure sequence
```

### Processing

```text
Collect Evidence
      ↓
Build Incident Timeline
      ↓
Map Events to Topology
      ↓
Identify Candidate Causes
      ↓
Compare Evidence
      ↓
Calculate/Assign Confidence
      ↓
Select Probable Root Cause
```

### Output

```text
Root Cause
Confidence
Evidence
Affected Components
Failure Chain
```

### Example

```text
Root Cause:
R1 interface failure

Confidence:
92%

Evidence:
- R1 error happened first
- Packet loss followed
- Latency increased afterward
- Downstream servers became unavailable
- R1 is an upstream dependency
```

---

# 12. Failure Propagation Engine

This component explains how the initial failure produced downstream symptoms.

### Example

```text
R1 Interface Failure
        ↓
Link Disruption
        ↓
Packet Loss
        ↓
Latency Increase
        ↓
Server Timeout
        ↓
Service Disruption
```

### Features

- Timeline generation
- Dependency tracing
- Upstream/downstream analysis
- Affected node identification
- Failure-chain visualization

---

# 13. Impact Analysis Layer

After finding the probable root cause, NetRCA determines what was affected.

### Inputs

- Root cause
- Network topology
- Event relationships
- Device status
- Service dependencies

### Outputs

```text
Affected Devices
Affected Links
Affected Services
Affected Metrics
Duration
Severity
```

### Example

```text
Root Cause:
R1 interface failure

Affected:
S1
Server1
Server2

Impact:
24% packet loss
312 ms latency
Server requests failing
```

---

# 14. Incident Management Layer

All important network failures are represented as incidents.

### Incident Lifecycle

```text
Detected
   ↓
Investigating
   ↓
Root Cause Identified
   ↓
Resolved
   ↓
Closed
```

### Incident Object

```text
incident_id
title
severity
status
start_time
end_time
root_cause
confidence
impact
evidence
recommendation
```

### Features

- Incident creation
- Incident updates
- Incident history
- Incident timeline
- Incident filtering
- Incident search
- Incident resolution tracking

---

# 15. Gemini AI Layer

### Technology
- Gemini API

Gemini is used as the AI explanation and recommendation layer.

### Responsibilities

- Explain RCA findings
- Summarize incidents
- Explain failure propagation
- Generate readable incident reports
- Generate troubleshooting recommendations
- Explain technical evidence
- Answer questions about incidents

### Important Architecture Rule

Gemini should not be the sole root-cause detector.

The pipeline should first produce structured evidence:

```text
Metrics
Logs
Events
Topology
ML Anomalies
RCA Result
Impact
```

Then Gemini receives the structured findings and produces:

```text
Explanation
Summary
Recommendation
```

This makes the system more deterministic and easier to evaluate.

---

# 16. AI Agent Architecture

NetRCA can expose its intelligence through specialized software agents.

```text
                 NetRCA Agents
                      │
      ┌───────────────┼────────────────┐
      ↓               ↓                ↓
 Monitoring       Anomaly          Log Analysis
   Agent            Agent              Agent
      │               │                │
      └───────────────┼────────────────┘
                      ↓
                  RCA Agent
                      ↓
               Impact Agent
                      ↓
          Recommendation Agent
```

## Monitoring Agent

Collects network observations.

## Anomaly Detection Agent

Identifies abnormal behavior.

## Log Analysis Agent

Finds relevant log evidence.

## RCA Agent

Determines probable root cause.

## Impact Agent

Determines affected components.

## Recommendation Agent

Produces response guidance.

These agents are logical software modules. They do not require a separate LLM for every agent.

---

# 17. Backend Architecture

### Technology
- FastAPI
- Python

The backend is the central application layer between the analysis engine, database, and frontend.

```text
Frontend
    ↓
FastAPI
    ↓
Service Layer
    ├── Network Service
    ├── Monitoring Service
    ├── Incident Service
    ├── RCA Service
    ├── AI Service
    └── Report Service
    ↓
Database / AI / Mininet
```

---

# 18. Backend Modules

## Network Service

Responsibilities:
- Start network
- Stop network
- Get topology
- Get devices
- Get links
- Trigger faults

## Monitoring Service

Responsibilities:
- Retrieve metrics
- Retrieve logs
- Retrieve events
- Calculate health status

## Anomaly Service

Responsibilities:
- Run anomaly detection
- Return anomaly scores
- Store anomaly results

## Correlation Service

Responsibilities:
- Group related events
- Build incident timelines

## RCA Service

Responsibilities:
- Run root-cause analysis
- Generate evidence
- Calculate confidence
- Identify probable cause

## Impact Service

Responsibilities:
- Determine affected components
- Determine affected services
- Calculate impact

## AI Service

Responsibilities:
- Communicate with Gemini API
- Generate explanations
- Generate recommendations
- Generate reports

## Incident Service

Responsibilities:
- Create incidents
- Update incident status
- Retrieve incident history

---

# 19. API Architecture

Example API structure:

```text
/api/network
/api/topology
/api/metrics
/api/logs
/api/events
/api/anomalies
/api/incidents
/api/incidents/{id}
/api/root-cause/{incident_id}
/api/impact/{incident_id}
/api/recommendations/{incident_id}
/api/faults
/api/faults/inject
/api/faults/reset
/api/ai/explain
/api/ai/report
```

---

# 20. Database Architecture

### Technology
- Supabase
- PostgreSQL

### Main Tables

```text
devices
links
metrics
logs
events
anomalies
incidents
root_causes
recommendations
fault_injections
```

---

# 21. Database Relationships

```text
DEVICES
   │
   ├──────── METRICS
   │
   ├──────── LOGS
   │
   └──────── EVENTS
                  │
                  ↓
              ANOMALIES
                  │
                  ↓
              INCIDENTS
                  │
          ┌───────┼────────┐
          ↓       ↓        ↓
      ROOT_CAUSE IMPACT  RECOMMENDATION
```

---

# 22. Device Model

Example:

```text
device_id
name
type
ip_address
status
created_at
```

### Device Types

```text
ROUTER
SWITCH
SERVER
HOST
DNS
SERVICE
```

---

# 23. Link Model

Example:

```text
link_id
source_device
destination_device
bandwidth
latency
packet_loss
status
```

---

# 24. Metric Model

Example:

```text
metric_id
device_id
metric_type
value
unit
timestamp
```

### Metric Types

```text
LATENCY
PACKET_LOSS
BANDWIDTH
THROUGHPUT
CPU
MEMORY
ERROR_RATE
AVAILABILITY
```

---

# 25. Incident Evidence Model

Each RCA result should retain evidence.

```text
evidence_id
incident_id
source_type
source_id
description
timestamp
importance
```

### Source Types

```text
METRIC
LOG
EVENT
TOPOLOGY
ANOMALY
```

This allows the dashboard to explain why a root cause was selected.

---

# 26. Fault Injection Architecture

```text
Dashboard
    ↓
FastAPI
    ↓
Fault Injection Service
    ↓
Mininet
    ↓
Network Failure
    ↓
Metrics / Logs / Events
    ↓
NetRCA Analysis Pipeline
```

### Supported Faults

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

---

# 27. Dashboard Architecture

### Technology

- React / Next.js
- Tailwind CSS
- Recharts
- React Flow or equivalent graph visualization

```text
                   Dashboard
                       │
       ┌───────────────┼────────────────┐
       ↓               ↓                ↓
 Network Overview   Incidents        Analytics
       │               │                │
       ↓               ↓                ↓
  Topology          RCA View       Historical Data
       │               │
       └───────────────┼───────────────┘
                       ↓
                AI Explanation
                       ↓
                Recommendation
```

---

# 28. Dashboard Features

## Network Overview

- Overall health
- Device count
- Healthy devices
- Warning devices
- Failed devices
- Active incidents

## Live Metrics

- Latency
- Packet loss
- Throughput
- Bandwidth
- Error rate
- CPU
- Memory

## Topology

- Interactive graph
- Device status
- Link status
- Failed component highlighting
- Affected component highlighting

## Incident Center

- Active incidents
- Severity
- Status
- Root cause
- Confidence
- Affected components

## RCA Investigation

- Incident summary
- Timeline
- Event correlation
- Root cause
- Evidence
- Failure chain
- Impact
- Gemini explanation
- Recommendation

## Logs

- Live logs
- Search
- Device filter
- Severity filter
- Time filter

## Historical Analytics

- Incident frequency
- Anomaly history
- Metric history
- Fault statistics
- Repeated root causes

---

# 29. Network Health Architecture

The system calculates an overall network health state from multiple signals.

### Inputs

```text
Latency
Packet Loss
Availability
Error Rate
Active Incidents
Device Status
```

### Output

```text
HEALTHY
WARNING
CRITICAL
```

Optional numerical score:

```text
Network Health = 78/100
```

---

# 30. Real-Time Data Flow

Normal operation:

```text
Mininet
   ↓
Metrics
   ↓
Collector
   ↓
Processor
   ↓
Anomaly Detection
   ↓
Event Store
   ↓
Supabase
   ↓
FastAPI
   ↓
Dashboard
```

---

# 31. Incident Data Flow

When a fault occurs:

```text
Fault Injection
      ↓
Mininet Failure
      ↓
Metrics Change
      ↓
Logs / Events
      ↓
Anomaly Detection
      ↓
Event Correlation
      ↓
RCA Engine
      ↓
Impact Analysis
      ↓
Gemini Explanation
      ↓
Recommendation
      ↓
Incident Record
      ↓
Dashboard
```

---

# 32. Example End-to-End Scenario

## Scenario: Router R1 Interface Failure

### Step 1 — Fault Injection

User selects:

```text
Inject Router Interface Failure
Device: R1
```

### Step 2 — Mininet

The interface is disabled.

### Step 3 — Monitoring

System observes:

```text
Packet loss = 24%
Latency = 312 ms
```

### Step 4 — Anomaly Detection

ML identifies abnormal values.

### Step 5 — Event Generation

```text
R1 interface failure
Packet loss
High latency
Server timeout
```

### Step 6 — Correlation

Events are connected by time and topology.

### Step 7 — RCA

The system identifies:

```text
Probable Root Cause:
R1 interface failure
```

### Step 8 — Impact

```text
Server1 affected
Server2 affected
S1 affected
```

### Step 9 — Gemini

Gemini generates a readable explanation.

### Step 10 — Dashboard

The dashboard displays:

```text
CRITICAL INCIDENT

Root Cause:
R1 Interface Failure

Confidence:
92%

Impact:
2 servers affected

Evidence:
4 correlated events

Recommendation:
Inspect R1 interface and routing configuration.
```

---

# 33. Explainability Architecture

NetRCA must preserve the chain of evidence.

```text
Observed Data
      ↓
Anomaly
      ↓
Event
      ↓
Correlation
      ↓
Candidate Cause
      ↓
Evidence
      ↓
Root Cause
      ↓
Impact
      ↓
Recommendation
```

The UI should allow the user to move through this chain.

---

# 34. Security Architecture

## API Keys

Gemini API keys must remain on the backend.

```text
Frontend
   X
   │
   │ no Gemini API key
   │
   ↓
FastAPI
   ↓
Gemini API
```

## Supabase

Use secure authentication/authorization where required.

## Environment Variables

Sensitive values should be stored in environment variables:

```text
GEMINI_API_KEY
SUPABASE_URL
SUPABASE_KEY
```

Never hard-code secrets in source code.

---

# 35. Safety Architecture

NetRCA should operate in a controlled simulated environment.

### Restrictions

- Fault injection only inside Mininet
- No unauthorized real-network scanning
- No destructive actions against real infrastructure
- No automatic production remediation
- Recommendations require human review
- AI should not directly execute dangerous network changes

---

# 36. Project Directory Architecture

Recommended repository structure:

```text
netrca/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── agents/
│   │   ├── rca/
│   │   ├── anomaly/
│   │   ├── topology/
│   │   ├── monitoring/
│   │   ├── incident/
│   │   └── main.py
│   │
│   ├── tests/
│   └── requirements.txt
│
├── network/
│   ├── topologies/
│   ├── faults/
│   ├── collectors/
│   ├── traffic/
│   └── mininet_runner.py
│
├── ml/
│   ├── preprocessing/
│   ├── models/
│   ├── training/
│   └── evaluation/
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── features/
│   ├── services/
│   └── lib/
│
├── database/
│   ├── migrations/
│   └── seeds/
│
├── docs/
│   ├── PRD.md
│   └── ARCHITECTURE.md
│
├── .env.example
├── README.md
└── docker-compose.yml
```

Docker is optional for deployment/supporting services; **Mininet remains the primary network simulation environment**.

---

# 37. Module Responsibilities

| Module | Responsibility |
|---|---|
| Mininet | Simulated network |
| Collector | Collect network data |
| Processor | Clean and transform data |
| Scikit-learn | Detect anomalies |
| NetworkX | Analyze topology |
| Correlation Engine | Relate events |
| RCA Engine | Identify probable root cause |
| Impact Engine | Determine affected components |
| Gemini Service | Explain and recommend |
| Incident Service | Manage incidents |
| FastAPI | Backend/API |
| Supabase | Persistent storage |
| React/Next.js | User interface |
| Recharts | Metric visualization |
| React Flow | Topology visualization |

---

# 38. Deployment Architecture

For development:

```text
Developer Machine
│
├── Mininet
├── Python Backend
├── ML Engine
└── Frontend
        │
        └── Supabase Cloud
```

Gemini API is accessed by the backend.

For a future deployment, services can be containerized where compatible, while the Mininet network simulation can run in an appropriate Linux environment.

---

# 39. Failure Handling

The system should handle:

- Collector failure
- Missing metrics
- Invalid logs
- Mininet process failure
- Gemini API failure
- Database connection failure
- Backend failure
- ML model failure

### Example

If Gemini is unavailable:

```text
RCA Engine
   ↓
Root Cause + Evidence
   ↓
Dashboard
```

The core RCA result should remain available even without Gemini.

---

# 40. Observability of NetRCA

NetRCA itself should maintain application logs for:

- API requests
- ML execution
- RCA execution
- Gemini requests
- Database errors
- Network simulation errors
- Fault injection operations

This makes debugging easier.

---

# 41. Performance Requirements

The system should aim for:

- Near-real-time metric updates
- Fast anomaly detection
- Fast event correlation
- Low-latency RCA for normal incident sizes
- Responsive dashboard
- Graceful handling of temporary API/database failures

Exact performance targets can be defined after the first prototype and measured experimentally.

---

# 42. Testing Architecture

Testing should occur at multiple levels.

## Unit Testing

Test:

- Metric processing
- Anomaly detection
- Event correlation
- Topology functions
- RCA logic
- API functions

## Integration Testing

Test:

```text
Mininet
→ Collector
→ ML
→ RCA
→ Database
→ API
→ Dashboard
```

## Scenario Testing

Test known faults:

1. Router failure
2. Interface failure
3. Link failure
4. Packet loss
5. High latency
6. Congestion
7. DNS failure
8. Server overload

---

# 43. Evaluation Metrics

The academic evaluation should measure:

### Anomaly Detection

- Precision
- Recall
- Accuracy where appropriate
- False positive rate

### Root Cause Analysis

- Root-cause identification accuracy
- Top-k candidate accuracy if multiple candidates are retained
- Confidence calibration where feasible

### System Performance

- Detection time
- RCA processing time
- Dashboard response time

### Incident Quality

- Correct affected-component identification
- Correct failure-chain reconstruction
- Recommendation usefulness

---

# 44. MVP Architecture

The minimum complete architecture is:

```text
Mininet
   ↓
Python Collector
   ↓
Scikit-learn
   ↓
NetworkX
   ↓
RCA Engine
   ↓
Gemini
   ↓
FastAPI
   ↓
Supabase
   ↓
React Dashboard
```

---

# 45. Complete Feature Inventory

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

## Monitoring Features

- Real-time metrics
- Historical metrics
- Device monitoring
- Link monitoring
- Availability monitoring
- Error monitoring
- Interface monitoring

## Log Features

- Log collection
- Log parsing
- Severity classification
- Log search
- Log filtering
- Incident association

## Event Features

- Event generation
- Event classification
- Event severity
- Event timeline
- Event correlation

## AI/ML Features

- Anomaly detection
- Anomaly scoring
- Root-cause analysis
- Failure propagation analysis
- Impact analysis
- Explainable diagnosis
- AI incident explanation
- AI recommendations
- AI incident reports

## RCA Features

- Candidate cause detection
- Evidence collection
- Confidence estimation
- Timeline analysis
- Topology-based reasoning
- Dependency analysis
- Symptom/root-cause separation

## Fault Injection Features

- Router failure
- Interface failure
- Switch failure
- Link failure
- Packet loss
- High latency
- Congestion
- DNS failure
- Server overload
- Server unavailability
- Error-rate increase
- Bandwidth reduction
- Fault reset/recovery

## Incident Features

- Incident creation
- Incident status
- Severity
- Root cause
- Confidence
- Evidence
- Impact
- Recommendations
- Incident history
- Incident search
- Incident filtering
- Incident resolution

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

## Data Features

- Device storage
- Link storage
- Metric storage
- Log storage
- Event storage
- Anomaly storage
- Incident storage
- RCA storage
- Recommendation storage
- Fault-injection history

## Security Features

- Backend-only Gemini API access
- Environment variables
- Secure database credentials
- Controlled fault injection
- Human-approved remediation
- No unauthorized real-network actions

---

# 46. Final Architecture

```text
                           ┌──────────────────────┐
                           │       USER           │
                           └──────────┬───────────┘
                                      │
                                      ▼
                           ┌──────────────────────┐
                           │ React / Next.js UI   │
                           │ Tailwind + Charts    │
                           └──────────┬───────────┘
                                      │
                                      ▼
                           ┌──────────────────────┐
                           │      FastAPI         │
                           │      Backend         │
                           └──────────┬───────────┘
                                      │
                 ┌────────────────────┼────────────────────┐
                 │                    │                    │
                 ▼                    ▼                    ▼
          ┌────────────┐       ┌────────────┐       ┌────────────┐
          │  Supabase  │       │   Gemini   │       │   NetRCA   │
          │ PostgreSQL │       │    API     │       │   Engine   │
          └────────────┘       └────────────┘       └─────┬──────┘
                                                          │
                                      ┌───────────────────┼───────────────────┐
                                      │                   │                   │
                                      ▼                   ▼                   ▼
                               ┌────────────┐      ┌────────────┐      ┌────────────┐
                               │ Scikit-    │      │ NetworkX   │      │ Incident   │
                               │ learn ML   │      │ Topology   │      │ / Impact   │
                               └────────────┘      └────────────┘      └────────────┘
                                      │                   │                   │
                                      └───────────────────┼───────────────────┘
                                                          │
                                                          ▼
                                                ┌─────────────────┐
                                                │ Data Collection │
                                                │     Python      │
                                                └────────┬────────┘
                                                         │
                                                         ▼
                                                ┌─────────────────┐
                                                │     Mininet     │
                                                │ Virtual Network │
                                                └─────────────────┘
```

---

# 47. Architecture Summary

The final NetRCA architecture consists of:

```text
MININET
   ↓
DATA COLLECTION
   ↓
DATA PROCESSING
   ↓
ANOMALY DETECTION
   ↓
LOG + EVENT ANALYSIS
   ↓
NETWORKX TOPOLOGY ANALYSIS
   ↓
EVENT CORRELATION
   ↓
ROOT CAUSE ANALYSIS
   ↓
IMPACT ANALYSIS
   ↓
GEMINI EXPLANATION
   ↓
RECOMMENDATION
   ↓
FASTAPI
   ↓
SUPABASE
   ↓
REACT / NEXT.JS DASHBOARD
```

The architecture intentionally keeps **network simulation, deterministic/ML analysis, RCA, AI explanation, backend, storage, and presentation separated**. This makes the project easier to develop, test, demonstrate, and extend.
