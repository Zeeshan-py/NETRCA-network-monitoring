# NetRCA — Software Requirements Specification (SRS)

## 1. Introduction

### 1.1 Purpose

This Software Requirements Specification (SRS) defines the complete functional and non-functional requirements for **NetRCA — AI-Powered Network Root Cause Analysis and Incident Response System**.

NetRCA is an AI-assisted network monitoring and troubleshooting platform designed to operate on a controlled **Mininet network simulation environment**.

The system observes network behavior, collects metrics/logs/events, detects anomalies, correlates related events, analyzes network topology and dependencies, identifies probable root causes, evaluates impact, and generates explainable recommendations using AI.

The primary objective is to move from:

```text
Raw Network Data
      ↓
Symptoms
```

to:

```text
Raw Network Data
      ↓
Anomaly Detection
      ↓
Event Correlation
      ↓
Root Cause Analysis
      ↓
Impact Analysis
      ↓
AI Explanation
      ↓
Recommended Action
```

---

## 1.2 Scope

NetRCA covers:

- Network simulation
- Network topology management
- Device and link monitoring
- Metrics collection
- Log collection
- Event processing
- Anomaly detection
- Event correlation
- Network dependency analysis
- Root cause analysis
- Failure-chain reconstruction
- Impact analysis
- Incident management
- AI-assisted explanations
- AI-generated recommendations
- Fault injection
- Network health monitoring
- Historical analytics
- Incident reports
- Security and audit controls
- Web-based visualization

The initial system is intended for a **controlled academic/simulation environment** and must not be used to control unauthorized real-world networks.

---

## 1.3 Product Vision

NetRCA should behave like an intelligent network operations assistant:

```text
Observe
   ↓
Understand
   ↓
Correlate
   ↓
Diagnose
   ↓
Explain
   ↓
Recommend
```

The system should not simply show that a network is failing. It should help explain **why the failure occurred, how it propagated, what it affected, and what should be investigated next**.

---

## 1.4 Intended Audience

The system is intended for:

- Network engineering students
- Computer engineering students
- Network administrators
- System administrators
- Researchers
- AI/ML learners
- Network troubleshooting learners
- Instructors demonstrating AI and networking concepts

---

# 2. Product Description

## 2.1 Product Perspective

NetRCA consists of:

```text
Mininet Network Simulation
        ↓
Data Collection
        ↓
Data Processing
        ↓
ML Anomaly Detection
        ↓
Event Correlation
        ↓
Topology / Graph Analysis
        ↓
RCA Engine
        ↓
Impact Analysis
        ↓
Gemini AI
        ↓
FastAPI Backend
        ↓
Next.js Dashboard
```

---

## 2.2 Major System Components

### Network Simulation Layer

Uses Mininet to create a controlled virtual network containing:

- Routers
- Switches
- Hosts/servers
- Links
- Services
- Network traffic

### Data Collection Layer

Collects:

- CPU-related metrics where available
- Memory-related metrics where available
- Bandwidth
- Latency
- Packet loss
- Availability
- Interface status
- Network errors
- Logs
- Events

### Intelligence Layer

Contains:

- Anomaly detection
- Event correlation
- Topology reasoning
- Root cause analysis
- Failure propagation analysis
- Impact analysis
- AI explanation
- AI recommendations

### Backend Layer

FastAPI provides:

- REST APIs
- Authentication
- Authorization
- Validation
- Business logic
- Network-control interface
- ML/RCA orchestration
- AI integration

### Database Layer

Supabase/PostgreSQL stores:

- Devices
- Links
- Services
- Metrics
- Logs
- Events
- Anomalies
- Incidents
- Root causes
- Evidence
- Impact
- Recommendations
- AI analyses
- Fault injections
- Topology snapshots

### Frontend Layer

Next.js/React provides:

- Dashboard
- Network topology
- Metrics
- Logs
- Events
- Incident investigation
- RCA visualization
- Failure-chain visualization
- AI explanations
- Recommendations
- Reports

---

# 3. System Users

## 3.1 Administrator

The administrator can:

- Manage users
- Manage system configuration
- Manage devices
- Manage links
- Run network controls
- Inject faults
- Recover faults
- Reset the simulation
- View all incidents
- Execute RCA
- Generate AI analysis
- View audit information

---

## 3.2 Network Operator

The network operator can:

- View network status
- View topology
- View metrics
- View logs
- View events
- Investigate incidents
- Run RCA
- Generate AI analysis
- Inject approved faults
- Recover approved faults
- Generate recommendations

---

## 3.3 Viewer

The viewer can:

- View dashboard
- View topology
- View metrics
- View logs
- View incidents
- View RCA results
- View AI explanations
- View recommendations

The viewer must not perform privileged network operations.

---

# 4. Functional Requirements

# FR-001 Network Simulation Management

The system shall provide controlled management of the Mininet network simulation.

### Features

- Start network
- Stop network
- Restart network
- Reset network
- View network status
- Detect simulator availability
- Display simulator health
- Maintain controlled topology
- Maintain simulated devices
- Maintain simulated links

### Requirements

**FR-001.1** The system shall allow an authorized user to start the simulated network.

**FR-001.2** The system shall allow an authorized user to stop the simulated network.

**FR-001.3** The system shall allow an authorized user to restart the simulated network.

**FR-001.4** The system shall allow an authorized user to reset the network to a known state.

**FR-001.5** The system shall expose network status through the backend.

**FR-001.6** The system shall prevent arbitrary shell commands from being submitted through the public API.

---

# FR-002 Topology Management

The system shall represent the simulated network as a graph.

### Features

- Device discovery
- Link discovery
- Topology visualization
- Device relationships
- Link relationships
- Topology snapshots
- Topology history
- Dependency representation

### Requirements

**FR-002.1** The system shall represent devices as graph nodes.

**FR-002.2** The system shall represent links as graph edges.

**FR-002.3** The system shall provide the current topology.

**FR-002.4** The system shall support topology snapshots.

**FR-002.5** The system shall use NetworkX for graph-based analysis.

**FR-002.6** The system shall allow topology information to support RCA.

---

# FR-003 Device Management

The system shall maintain information about network devices.

### Supported device concepts

- Router
- Switch
- Host
- Server
- Other simulated network nodes

### Device attributes

- Device ID
- Name
- Type
- IP address where applicable
- Status
- Metadata
- Created time
- Updated time

### Features

- Create device
- View device
- Update device
- Delete device
- List devices
- Filter devices
- View device health
- View device metrics
- View device logs
- View device events

---

# FR-004 Link Management

The system shall manage relationships between network devices.

### Link information

- Source device
- Destination device
- Bandwidth
- Latency
- Packet-loss characteristics
- Status
- Metadata

### Features

- Create link
- View link
- Update link
- Delete link
- List links
- View link health
- Monitor link performance
- Associate faults with links

---

# FR-005 Service Management

The system shall support services running on simulated hosts/devices.

### Service information

- Service ID
- Service name
- Service type
- Device association
- Status
- Port where applicable
- Metadata

### Features

- Create service
- View service
- Update service
- Associate service with device
- Monitor service status
- Associate service failures with incidents

---

# FR-006 Metrics Collection

The system shall collect network health and performance metrics.

### Metrics

- Latency
- Packet loss
- Bandwidth
- Throughput where available
- Availability
- Interface state
- Error counts
- Device health indicators

### Features

- Real-time metrics
- Historical metrics
- Latest metrics
- Metric summaries
- Time-range filtering
- Device filtering
- Link filtering
- Metric aggregation

### Requirements

**FR-006.1** Metrics shall be associated with a device or network resource.

**FR-006.2** Metrics shall include timestamps.

**FR-006.3** Metrics shall be stored for historical analysis.

**FR-006.4** Metrics shall be available to the anomaly detection system.

---

# FR-007 Log Collection and Analysis

The system shall collect and process network-related logs.

### Features

- Log collection
- Log storage
- Log filtering
- Log search
- Log severity
- Log timestamps
- Device association
- Event extraction
- Incident association

### Log severity

```text
DEBUG
INFO
WARNING
ERROR
CRITICAL
```

The exact implementation may be extended as required.

---

# FR-008 Event Management

The system shall represent important network occurrences as events.

### Event examples

- Interface failure
- Link failure
- Packet-loss increase
- Latency increase
- Device unavailable
- Service unavailable
- Error spike
- Recovery event

### Features

- Event generation
- Event classification
- Event storage
- Event timeline
- Event filtering
- Event correlation
- Incident association

---

# FR-009 Anomaly Detection

The system shall detect abnormal network behavior.

### Initial approach

The system shall support ML-based anomaly detection, with **Isolation Forest** as an initial implementation candidate.

### Input features

Potential features include:

- Latency
- Packet loss
- Bandwidth
- Availability
- Error rate
- Device health indicators
- Historical deviations

### Features

- Detect anomalies
- Store anomaly records
- Assign anomaly score
- Assign severity
- Associate anomaly with device/resource
- View anomaly history
- View anomaly statistics

### Requirements

**FR-009.1** The anomaly detector shall accept validated numerical features.

**FR-009.2** The system shall record the timestamp of each detected anomaly.

**FR-009.3** The system shall preserve the relationship between an anomaly and its source resource.

**FR-009.4** The anomaly detector shall provide results to the event/RCA pipeline.

---

# FR-010 Event Correlation

The system shall correlate events that may belong to the same underlying failure.

### Correlation dimensions

- Time
- Device
- Link
- Service
- Topology
- Event type
- Severity
- Dependency

### Example

```text
R1 interface failure
        ↓
Packet loss
        ↓
High latency
        ↓
Server timeout
        ↓
Service unavailable
```

The system should group related observations into a coherent incident rather than treating every symptom as an independent failure.

---

# FR-011 Incident Management

The system shall provide incident lifecycle management.

### Incident states

```text
OPEN
INVESTIGATING
RESOLVED
CLOSED
```

### Incident features

- Create incident
- View incident
- Update incident
- Incident timeline
- Associate events
- Associate anomalies
- Root cause
- Evidence
- Impact
- Recommendations
- AI analysis
- Resolve incident
- Close incident
- Incident history
- Incident filtering
- Incident severity

### Severity

```text
LOW
MEDIUM
HIGH
CRITICAL
```

---

# FR-012 Root Cause Analysis

Root Cause Analysis is the core intelligence feature.

The system shall identify probable causes instead of simply listing symptoms.

### RCA inputs

- Metrics
- Logs
- Events
- Anomalies
- Topology
- Dependencies
- Temporal relationships
- Historical context

### RCA process

```text
Incident
 ↓
Collect Evidence
 ↓
Identify Anomalies
 ↓
Correlate Events
 ↓
Analyze Topology
 ↓
Generate Candidate Causes
 ↓
Score Candidates
 ↓
Select Probable Root Cause
 ↓
Store Evidence
```

### Requirements

**FR-012.1** The RCA engine shall generate one or more candidate causes.

**FR-012.2** Each candidate shall have supporting evidence.

**FR-012.3** Each candidate shall have a confidence score where applicable.

**FR-012.4** The system shall preserve evidence supporting the RCA.

**FR-012.5** The system shall allow users to inspect why a cause was selected.

---

# FR-013 Root Cause Evidence

The system shall maintain evidence supporting root-cause decisions.

### Evidence types

- Metric anomaly
- Log entry
- Event
- Topology relationship
- Device failure
- Link failure
- Service dependency
- Historical observation

### Evidence attributes

- Evidence ID
- Root cause ID
- Evidence type
- Source ID
- Description
- Weight
- Timestamp
- Metadata

---

# FR-014 Failure Chain Analysis

The system shall reconstruct how a failure propagated through the network.

### Example

```text
R1 Interface Failure
        ↓
Packet Loss
        ↓
Latency Increase
        ↓
Server Timeout
        ↓
Application Unavailable
```

### Features

- Failure-chain generation
- Ordered events
- Dependency traversal
- Graph visualization
- Failure explanation
- AI explanation

---

# FR-015 Impact Analysis

The system shall determine what resources were affected by an incident.

### Impact categories

- Devices affected
- Links affected
- Services affected
- Users/services potentially affected
- Availability impact
- Performance impact
- Duration
- Severity

### Features

- Impact detection
- Impact summary
- Impact timeline
- Affected-resource list
- Topology-based impact analysis

---

# FR-016 AI Incident Explanation

The system shall use Gemini API to generate human-readable explanations.

### Input

Structured information such as:

- Incident
- Timeline
- Metrics
- Events
- Anomalies
- Root cause
- Evidence
- Impact

### Output

- Incident explanation
- Root cause explanation
- Failure-chain explanation
- Impact explanation
- Human-readable summary

### Requirement

Gemini shall be an explanation and recommendation layer rather than the sole deterministic RCA mechanism.

---

# FR-017 AI Root Cause Explanation

The system shall provide an AI-generated explanation of the probable root cause.

Example:

```text
Probable Root Cause:
R1 interface failure

Why:
The interface failure occurred before the packet-loss spike,
which was followed by latency increase and service timeout.
The topology shows that R1 is a dependency for the affected service.
```

The UI shall distinguish evidence-based system results from AI-generated interpretation.

---

# FR-018 AI Recommendations

The system shall generate recommended investigation/remediation steps.

Example:

```text
1. Inspect R1 interface state.
2. Verify the link between R1 and S1.
3. Check routing configuration.
4. Confirm service recovery after restoration.
```

Recommendations are advisory.

The MVP shall not automatically execute destructive remediation actions.

---

# FR-019 AI Incident Q&A

The system may provide an incident-specific question-answering interface.

Example questions:

```text
Why did this incident happen?
Which device was probably responsible?
What services were affected?
What evidence supports the RCA?
How did the failure propagate?
What should the operator investigate first?
```

The AI should answer using incident context supplied by the backend.

---

# FR-020 Fault Injection

The system shall provide controlled fault injection for testing RCA.

### Supported fault types

- Interface failure
- Link failure
- Packet loss
- High latency
- Server overload
- DNS failure

Additional fault types may be added later.

### Features

- List fault types
- Inject fault
- View fault status
- View fault history
- Recover fault
- Reset faults
- Set controlled parameters
- Associate fault with device/link/service

### Safety requirement

Fault injection must be restricted to the controlled Mininet simulation.

---

# FR-021 Network Health Monitoring

The system shall provide an overall network health view.

### Health information

- Network availability
- Device health
- Link health
- Service health
- Active anomalies
- Active incidents
- Recent failures

### Features

- Overall health
- Device health
- Health history
- Health trends
- Health status indicators

---

# FR-022 Dashboard

The frontend shall provide a centralized operational dashboard.

### Dashboard sections

```text
Network Status
Topology
Active Incidents
Anomalies
Metrics
Logs
Failure Chains
Root Causes
Impact
AI Analysis
Recommendations
Fault Injection
Analytics
```

---

# FR-023 Interactive Topology

The frontend shall provide an interactive network graph.

### Features

- Device nodes
- Link edges
- Device status
- Link status
- Failure highlighting
- Incident highlighting
- Root-cause highlighting
- Affected-resource highlighting
- Zoom
- Pan
- Selection
- Topology filtering

React Flow is the preferred implementation.

---

# FR-024 Incident Investigation Interface

The system shall provide a dedicated incident investigation view.

### It shall display:

- Incident summary
- Severity
- Status
- Start time
- End time
- Timeline
- Events
- Anomalies
- Root causes
- Evidence
- Failure chain
- Impact
- Recommendations
- AI explanation
- Incident report

---

# FR-025 Analytics

The system shall provide analytics for:

- Incidents
- Anomalies
- Faults
- Root causes
- Network health
- Device failures
- Service failures

### Features

- Counts
- Trends
- Time-series charts
- Severity distribution
- Device distribution
- Root-cause distribution
- Fault frequency

---

# FR-026 Incident Reports

The system shall generate incident reports.

### Report sections

```text
Incident Summary
Timeline
Observed Symptoms
Anomalies
Root Cause
Evidence
Failure Chain
Impact
Recommendations
AI Explanation
```

### Features

- Generate report
- View report
- Export report
- Historical reports

---

# FR-027 Search, Filtering and Pagination

The system shall support efficient data retrieval.

### Searchable data

- Devices
- Logs
- Events
- Incidents
- Root causes
- Faults

### Filters

- Date/time
- Severity
- Status
- Device
- Link
- Service
- Event type
- Fault type

### Pagination

Large datasets shall be paginated.

---

# FR-028 Authentication

The system should support authenticated users.

Preferred authentication technology:

```text
Supabase Auth
```

### Features

- Login
- Logout
- Session validation
- Token validation
- User identity
- Role association

---

# FR-029 Authorization

The system shall enforce permissions server-side.

### Roles

```text
ADMIN
NETWORK_OPERATOR
VIEWER
```

Privileged operations shall require appropriate authorization.

---

# FR-030 Audit Logging

The system shall record security-sensitive actions.

### Audit events

- Login
- Logout
- Fault injection
- Fault recovery
- Network start
- Network stop
- Network reset
- Device modification
- Link modification
- Incident modification
- RCA execution
- AI analysis
- Recommendation changes
- Configuration changes

---

# FR-031 Security Controls

The system shall implement:

- HTTPS in production
- Input validation
- CORS restrictions
- Rate limiting
- Authentication
- Authorization
- Secure error handling
- Secret management
- SQL injection prevention
- XSS protection
- Prompt injection protection
- Audit logging
- Dependency security
- Network isolation

---

# FR-032 API

The backend shall expose REST APIs under:

```text
/api/v1
```

### Network

```text
GET  /api/v1/network/status
POST /api/v1/network/start
POST /api/v1/network/stop
POST /api/v1/network/restart
POST /api/v1/network/reset
```

### Topology

```text
GET  /api/v1/topology
GET  /api/v1/topology/snapshots
POST /api/v1/topology/snapshots
```

### Devices

```text
GET    /api/v1/devices
POST   /api/v1/devices
GET    /api/v1/devices/{id}
PATCH  /api/v1/devices/{id}
DELETE /api/v1/devices/{id}
```

### Links

```text
GET   /api/v1/links
POST  /api/v1/links
GET   /api/v1/links/{id}
PATCH /api/v1/links/{id}
```

### Services

```text
GET  /api/v1/services
POST /api/v1/services
GET  /api/v1/services/{id}
PATCH /api/v1/services/{id}
```

### Metrics

```text
GET /api/v1/metrics/latest
GET /api/v1/metrics
GET /api/v1/metrics/summary
```

### Logs

```text
GET /api/v1/logs
GET /api/v1/logs/{id}
```

### Events

```text
GET  /api/v1/events
GET  /api/v1/events/{id}
GET  /api/v1/events/timeline
POST /api/v1/events/correlate
```

### Anomalies

```text
GET  /api/v1/anomalies
GET  /api/v1/anomalies/{id}
POST /api/v1/anomalies/detect
GET  /api/v1/anomalies/statistics
```

### Incidents

```text
GET   /api/v1/incidents
POST  /api/v1/incidents
GET   /api/v1/incidents/{id}
PATCH /api/v1/incidents/{id}
POST  /api/v1/incidents/{id}/resolve
POST  /api/v1/incidents/{id}/close
GET   /api/v1/incidents/{id}/timeline
GET   /api/v1/incidents/{id}/events
POST  /api/v1/incidents/{id}/events
```

### Root Cause

```text
GET  /api/v1/incidents/{id}/root-causes
POST /api/v1/incidents/{id}/root-cause/analyze
GET  /api/v1/root-causes/{id}
GET  /api/v1/root-causes/{id}/evidence
POST /api/v1/root-causes/{id}/evidence
```

### Impact

```text
GET  /api/v1/incidents/{id}/impact
POST /api/v1/incidents/{id}/impact/analyze
GET  /api/v1/incidents/{id}/failure-chain
```

### Recommendations

```text
GET   /api/v1/incidents/{id}/recommendations
POST  /api/v1/incidents/{id}/recommendations/generate
PATCH /api/v1/recommendations/{id}
```

### AI

```text
POST /api/v1/ai/incidents/{id}/explain
POST /api/v1/ai/root-causes/{id}/explain
POST /api/v1/ai/incidents/{id}/failure-chain/explain
POST /api/v1/ai/incidents/{id}/report
POST /api/v1/ai/incidents/{id}/ask
```

### Fault Injection

```text
GET  /api/v1/faults/types
POST /api/v1/faults/inject
GET  /api/v1/faults/{id}
GET  /api/v1/faults
POST /api/v1/faults/{id}/recover
POST /api/v1/faults/reset
```

### Health

```text
GET /api/v1/health/network
GET /api/v1/health/devices/{id}
GET /api/v1/health/history
GET /api/v1/health
```

### Analytics

```text
GET /api/v1/analytics/dashboard
GET /api/v1/analytics/incidents
GET /api/v1/analytics/anomalies
GET /api/v1/analytics/faults
GET /api/v1/analytics/root-causes
```

### Reports

```text
POST /api/v1/reports/incidents/{id}
GET  /api/v1/reports/incidents/{id}
GET  /api/v1/reports/incidents/{id}/export
```

---

# 5. Data Requirements

## 5.1 Device Data

The system shall store:

```text
id
name
type
ip_address
status
metadata
created_at
updated_at
```

---

## 5.2 Link Data

The system shall store:

```text
id
source_device_id
destination_device_id
bandwidth
latency
packet_loss
status
metadata
created_at
updated_at
```

---

## 5.3 Service Data

The system shall store:

```text
id
name
type
status
port
metadata
created_at
updated_at
```

---

## 5.4 Metric Data

The system shall store:

```text
id
device_id
link_id
metric_type
value
unit
timestamp
metadata
```

---

## 5.5 Log Data

The system shall store:

```text
id
device_id
service_id
severity
message
timestamp
metadata
```

---

## 5.6 Event Data

The system shall store:

```text
id
device_id
link_id
service_id
event_type
severity
description
timestamp
metadata
```

---

## 5.7 Anomaly Data

The system shall store:

```text
id
device_id
metric_id
anomaly_score
severity
description
detected_at
metadata
```

---

## 5.8 Incident Data

The system shall store:

```text
id
title
description
severity
status
started_at
resolved_at
closed_at
created_at
updated_at
```

---

## 5.9 Root Cause Data

The system shall store:

```text
id
incident_id
cause_type
description
confidence
created_at
```

---

## 5.10 Root Cause Evidence

The system shall store:

```text
id
root_cause_id
evidence_type
source_id
description
weight
timestamp
metadata
```

---

## 5.11 Impact Data

The system shall store:

```text
id
incident_id
resource_type
resource_id
impact_type
severity
description
created_at
```

---

## 5.12 Recommendation Data

The system shall store:

```text
id
incident_id
title
description
priority
status
source
created_at
updated_at
```

---

## 5.13 AI Analysis Data

The system shall store:

```text
id
incident_id
analysis_type
prompt_context
response
model
created_at
```

Sensitive credentials must never be stored in AI analysis records.

---

## 5.14 Fault Injection Data

The system shall store:

```text
id
fault_type
target_type
target_id
parameters
status
started_at
recovered_at
created_at
```

---

# 6. Non-Functional Requirements

# NFR-001 Performance

The dashboard should provide responsive interaction for normal academic workloads.

Target:

- Common API operations: preferably < 2 seconds
- Database queries: optimized for expected dataset size
- Dashboard loading: preferably < 3 seconds under normal conditions
- AI response: dependent on Gemini API latency

These are target values rather than strict guarantees.

---

# NFR-002 Scalability

The architecture should allow future scaling of:

- Number of devices
- Number of links
- Metrics
- Logs
- Events
- Incidents
- AI requests

The MVP may run as a single-server academic deployment.

---

# NFR-003 Availability

The system should gracefully handle failure of:

- Mininet
- Supabase
- Gemini
- Individual API operations

The system should not crash because one external component becomes temporarily unavailable.

---

# NFR-004 Reliability

The system shall:

- Validate inputs
- Handle exceptions
- Use database constraints
- Use controlled network operations
- Preserve important incident data
- Provide deterministic fallback behavior where possible

---

# NFR-005 Security

The system shall protect:

- Credentials
- User accounts
- Database
- Network simulation
- Incident information
- AI integration
- Privileged operations

Security requirements are defined in `SECURITY.md`.

---

# NFR-006 Usability

The interface should make complex network failures understandable.

The dashboard should emphasize:

```text
What happened?
Why did it happen?
What was affected?
What evidence supports it?
What should be investigated?
```

---

# NFR-007 Explainability

The system shall preserve the distinction between:

```text
Observed Evidence
        vs.
ML Detection
        vs.
RCA Result
        vs.
AI Interpretation
```

This is especially important because generative AI can produce incorrect explanations.

---

# NFR-008 Maintainability

The codebase should be modular.

Recommended backend modules:

```text
network/
monitoring/
metrics/
logs/
events/
anomaly/
correlation/
rca/
impact/
incidents/
ai/
faults/
analytics/
reports/
auth/
```

---

# NFR-009 Testability

The system should support:

- Unit testing
- API testing
- Integration testing
- ML testing
- RCA testing
- Security testing
- Frontend testing
- Fault-injection testing

Preferred tools:

```text
pytest
Vitest
React Testing Library
```

---

# NFR-010 Portability

The backend should run in a Linux environment compatible with Mininet.

Recommended development environment:

```text
Ubuntu / WSL2
```

The frontend should run in a standard modern browser.

---

# NFR-011 Observability

The system should expose:

- Backend health
- Network simulator health
- Database health
- AI service status
- Active incidents
- Recent anomalies

---

# NFR-012 Data Integrity

The system shall maintain referential integrity between:

```text
Devices
Links
Services
Metrics
Logs
Events
Anomalies
Incidents
Root Causes
Evidence
Impact
Recommendations
AI Analyses
Faults
```

---

# NFR-013 Privacy

The system should minimize collection of unnecessary personal information.

The project primarily processes simulated network information.

---

# NFR-014 AI Safety

AI-generated recommendations shall be advisory.

The MVP shall not allow Gemini to:

- Execute shell commands
- Directly control Mininet
- Directly access production networks
- Modify network configuration without explicit controlled backend logic

---

# 7. System Constraints

## Constraint 1

The primary network environment is Mininet.

## Constraint 2

The system requires a Linux-compatible environment for Mininet.

## Constraint 3

Gemini API access requires an API key.

## Constraint 4

Supabase requires appropriate project configuration.

## Constraint 5

AI quality depends on the quality of structured evidence supplied to Gemini.

## Constraint 6

ML anomaly detection quality depends on available training/baseline data.

## Constraint 7

The academic MVP is designed around simulated networks rather than production infrastructure.

---

# 8. Assumptions

The system assumes:

1. Mininet is installed correctly.
2. The backend can communicate with the simulation environment.
3. Supabase/PostgreSQL is reachable.
4. Gemini API credentials are configured securely.
5. The user has permission to operate the simulated environment.
6. Network devices and services are represented using known identifiers.
7. The generated metrics and logs are sufficiently representative for the demonstration.
8. AI output is treated as advisory rather than authoritative.

---

# 9. External Interfaces

## 9.1 User Interface

Technology:

```text
Next.js
React
TypeScript
Tailwind CSS
Recharts
React Flow
```

---

## 9.2 Backend Interface

Technology:

```text
FastAPI
Python
Pydantic
REST API
```

---

## 9.3 Database Interface

Technology:

```text
Supabase
PostgreSQL
```

---

## 9.4 AI Interface

Technology:

```text
Gemini API
```

---

## 9.5 Network Simulation Interface

Technology:

```text
Mininet
```

---

# 10. AI/ML Requirements

## 10.1 Machine Learning

The initial anomaly detection component shall use a suitable unsupervised approach, with Isolation Forest as the initial candidate.

Potential future algorithms:

- DBSCAN
- K-Means-based behavioral clustering
- One-Class SVM
- Autoencoders

---

## 10.2 Graph Reasoning

NetworkX shall represent:

```text
Devices
Links
Dependencies
Failure propagation
```

Graph analysis shall support:

- Neighbor analysis
- Dependency traversal
- Path analysis
- Affected-resource discovery
- Failure-chain reconstruction

---

## 10.3 Generative AI

Gemini shall provide:

- Explanations
- Summaries
- Recommendations
- Incident reports
- Incident Q&A

Gemini shall receive structured context generated by the backend.

---

# 11. End-to-End Functional Scenario

## Scenario: Router Interface Failure

### Step 1 — Network Running

```text
R1 ── S1 ── Server
```

All services are healthy.

### Step 2 — Fault Injection

User injects:

```text
R1 interface failure
```

### Step 3 — Network Symptoms

The simulator produces:

```text
Packet loss
Latency increase
Connection failures
Server timeout
```

### Step 4 — Monitoring

NetRCA collects:

```text
Metrics
Logs
Events
```

### Step 5 — Anomaly Detection

ML identifies unusual behavior.

### Step 6 — Event Correlation

The system connects:

```text
Interface failure
→ packet loss
→ latency
→ timeout
```

### Step 7 — RCA

The RCA engine identifies:

```text
Probable Root Cause:
R1 interface failure
```

### Step 8 — Evidence

The system shows:

```text
Failure occurred first
Packet loss increased afterward
Affected path depends on R1
Service timeout followed
```

### Step 9 — Impact

The system identifies:

```text
Affected server
Affected service
Unavailable path
Incident duration
```

### Step 10 — Gemini

Gemini explains the incident in human-readable language.

### Step 11 — Recommendation

The system recommends investigation/recovery actions.

### Step 12 — Recovery

The operator recovers the simulated fault.

### Step 13 — Resolution

Metrics return toward normal behavior and the incident can be resolved.

---

# 12. Alternative Fault Scenarios

The system should support demonstrations such as:

## Scenario A — Link Failure

```text
Link failure
 ↓
Connectivity loss
 ↓
Packet loss
 ↓
Service timeout
 ↓
Incident
```

## Scenario B — High Latency

```text
High latency
 ↓
Slow application response
 ↓
Timeouts
 ↓
Service degradation
```

## Scenario C — Packet Loss

```text
Packet loss
 ↓
Retransmissions
 ↓
Latency increase
 ↓
Application degradation
```

## Scenario D — Server Overload

```text
Server overload
 ↓
Service response degradation
 ↓
Timeout
 ↓
Application unavailable
```

## Scenario E — DNS Failure

```text
DNS failure
 ↓
Name resolution failure
 ↓
Application connection failure
 ↓
Service unavailable
```

---

# 13. Acceptance Criteria

The project shall be considered functionally complete when it can demonstrate:

### Network

- [ ] Mininet network starts
- [ ] Mininet network stops
- [ ] Network reset works
- [ ] Topology is visible

### Monitoring

- [ ] Metrics are collected
- [ ] Logs are collected
- [ ] Events are generated
- [ ] Network health is visible

### ML

- [ ] Anomalies are detected
- [ ] Anomalies are stored
- [ ] Anomaly history is visible

### Correlation

- [ ] Related events can be correlated
- [ ] Incident timeline is created
- [ ] Failure propagation is represented

### RCA

- [ ] Candidate causes are generated
- [ ] Root cause is selected/scored
- [ ] Evidence is shown
- [ ] Confidence is available
- [ ] Failure chain is reconstructed

### Impact

- [ ] Affected devices are identified
- [ ] Affected links are identified
- [ ] Affected services are identified
- [ ] Impact summary is displayed

### AI

- [ ] Gemini integration works
- [ ] Incident explanation works
- [ ] Root cause explanation works
- [ ] Failure-chain explanation works
- [ ] Recommendations are generated
- [ ] Incident report can be generated
- [ ] Incident Q&A works

### Fault Injection

- [ ] Fault types are listed
- [ ] Fault can be injected
- [ ] Fault status is tracked
- [ ] Fault can be recovered
- [ ] Fault history is stored

### Dashboard

- [ ] Network status is visible
- [ ] Topology is interactive
- [ ] Incidents are visible
- [ ] Metrics are visualized
- [ ] Logs are searchable
- [ ] RCA is visualized
- [ ] Failure chain is visualized
- [ ] AI explanation is visible
- [ ] Recommendations are visible

### Security

- [ ] Authentication works where enabled
- [ ] Authorization is enforced
- [ ] Secrets are protected
- [ ] Arbitrary commands are blocked
- [ ] Fault injection is restricted
- [ ] Audit logging works
- [ ] Rate limiting is applied to expensive operations

---

# 14. MVP Scope

The minimum viable version should contain:

```text
Mininet
   ↓
Topology
   ↓
Metrics
   ↓
Logs
   ↓
Events
   ↓
Anomaly Detection
   ↓
Event Correlation
   ↓
RCA
   ↓
Impact Analysis
   ↓
Gemini Explanation
   ↓
Recommendations
   ↓
Dashboard
```

### MVP features

1. Mininet topology
2. Device management
3. Link management
4. Metrics collection
5. Log collection
6. Event collection
7. Isolation Forest anomaly detection
8. Event correlation
9. NetworkX topology reasoning
10. Root cause analysis
11. Evidence management
12. Failure-chain reconstruction
13. Impact analysis
14. Incident management
15. Fault injection
16. Gemini explanation
17. Gemini recommendations
18. Interactive dashboard
19. Incident reports
20. Basic security controls

---

# 15. Future Enhancements

Potential future functionality:

- Advanced anomaly models
- Online learning
- Historical RCA learning
- Predictive failure detection
- Auto-remediation with explicit human approval
- Multi-network environments
- Real monitoring integrations
- SNMP support
- Prometheus integration
- Syslog integration
- Distributed monitoring
- Advanced user management
- Notification system
- Email/Slack alerts
- Advanced report generation
- RCA model evaluation
- Feedback-based learning
- Digital twin capabilities

Future real-network integrations must preserve authorization and security boundaries.

---

# 16. Feature Inventory

## Network

- Network simulation
- Network start
- Network stop
- Network restart
- Network reset
- Network status
- Network health
- Device management
- Link management
- Service management
- Topology management
- Topology snapshots
- Topology history

## Monitoring

- Real-time metrics
- Historical metrics
- Metric summaries
- Device health
- Link health
- Service health
- Log collection
- Log search
- Log filtering
- Event generation
- Event timeline
- Event filtering

## AI/ML

- ML anomaly detection
- Anomaly scoring
- Anomaly history
- Event correlation
- Graph-based reasoning
- Root cause candidates
- Root cause scoring
- Root cause evidence
- Failure-chain reconstruction
- Impact analysis
- Gemini incident explanation
- Gemini root-cause explanation
- Gemini failure-chain explanation
- Gemini recommendations
- Gemini incident reports
- Incident Q&A

## Incident Management

- Incident creation
- Incident investigation
- Incident timeline
- Incident severity
- Incident status
- Incident event association
- Incident resolution
- Incident closure
- Incident history
- Incident reports
- Incident export

## Fault Injection

- Interface failure
- Link failure
- Packet loss
- High latency
- Server overload
- DNS failure
- Fault history
- Fault recovery
- Fault reset

## Dashboard

- Network overview
- Health dashboard
- Interactive topology
- Metrics charts
- Logs
- Events
- Anomalies
- Incidents
- RCA view
- Evidence view
- Failure-chain view
- Impact view
- AI analysis
- Recommendations
- Analytics
- Reports

## Security

- Authentication
- Authorization
- Role-based access
- HTTPS
- CORS
- Rate limiting
- Input validation
- Secret management
- SQL injection protection
- XSS protection
- Prompt injection protection
- Audit logging
- Error sanitization
- Dependency security
- Network isolation
- Privileged operation controls

---

# 17. Traceability Summary

| Requirement Area | Main Components |
|---|---|
| Network simulation | Mininet |
| Topology | Mininet + NetworkX + React Flow |
| Monitoring | Python + FastAPI |
| Metrics | Python + Pandas |
| Anomaly detection | Scikit-learn |
| Event correlation | Python + NetworkX |
| RCA | Python + NetworkX |
| Impact analysis | NetworkX |
| AI explanation | Gemini API |
| API | FastAPI + Pydantic |
| Database | Supabase/PostgreSQL |
| Frontend | Next.js + React + TypeScript |
| Charts | Recharts |
| Testing | pytest + Vitest |
| Version control | Git + GitHub |

---

# 18. Final System Requirement

The complete NetRCA system shall provide an integrated pipeline:

```text
                 ┌──────────────────────┐
                 │   MININET NETWORK    │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │   DATA COLLECTION    │
                 │ Metrics / Logs /     │
                 │ Events               │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │   DATA PROCESSING    │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │ ANOMALY DETECTION    │
                 │    ML / Isolation    │
                 │       Forest         │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │  EVENT CORRELATION   │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │ TOPOLOGY / GRAPH     │
                 │      ANALYSIS        │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │ ROOT CAUSE ANALYSIS  │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │   IMPACT ANALYSIS    │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │      GEMINI AI       │
                 │ Explain / Recommend  │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │   HUMAN DASHBOARD    │
                 └──────────────────────┘
```

The final product should therefore function as an **AI-assisted network investigation and root-cause analysis platform**, combining simulated network telemetry, machine learning, graph reasoning, deterministic evidence, and generative AI into one integrated system.

The system's central requirement is:

> **NetRCA shall transform network symptoms into an evidence-supported probable root cause, explain the failure chain and impact, and provide human-readable recommendations within a controlled and secure simulation environment.**
