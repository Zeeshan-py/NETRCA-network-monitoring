# NetRCA — API Design Specification

## 1. Overview

This document defines the REST API architecture for **NetRCA — AI-Powered Network Root Cause Analysis and Incident Response System**.

The API is the central communication layer between:

```text
Next.js / React Dashboard
          ↓
       FastAPI
          ↓
 ┌────────┼───────────┐
 ↓        ↓           ↓
Mininet  RCA/ML    Supabase
          ↓
      Gemini API
```

The API is designed around the NetRCA pipeline:

```text
OBSERVE
  ↓
COLLECT
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
```

---

# 2. API Goals

The API must provide endpoints for:

- Network lifecycle management
- Network topology
- Device management
- Link management
- Service management
- Real-time metrics
- Historical metrics
- Logs
- Events
- Anomalies
- Event correlation
- Incidents
- Root-cause analysis
- Evidence
- Impact analysis
- Recommendations
- Gemini AI analysis
- Fault injection
- Fault recovery
- Network health
- Historical analytics
- Incident reports
- Dashboard data

---

# 3. API Technology

## Backend

- FastAPI
- Python
- Pydantic
- Uvicorn

## Database

- Supabase
- PostgreSQL

## AI

- Gemini API

## Network

- Mininet

## ML

- Scikit-learn

## Graph

- NetworkX

---

# 4. API Base URL

Development:

```text
http://localhost:8000/api/v1
```

Production example:

```text
https://api.example.com/api/v1
```

All application endpoints should be versioned under:

```text
/api/v1
```

This makes future API changes easier to manage.

---

# 5. Response Format

All successful API responses should follow a consistent structure.

## Success

```json
{
  "success": true,
  "data": {},
  "message": "Operation completed successfully"
}
```

## Error

```json
{
  "success": false,
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Device was not found"
  }
}
```

---

# 6. HTTP Status Codes

Use standard HTTP status codes.

| Code | Meaning |
|---|---|
| `200` | Successful request |
| `201` | Resource created |
| `202` | Accepted for processing |
| `204` | Successful request with no body |
| `400` | Invalid request |
| `401` | Unauthorized |
| `403` | Forbidden |
| `404` | Resource not found |
| `409` | Conflict |
| `422` | Validation error |
| `429` | Rate limit exceeded |
| `500` | Internal server error |
| `502` | External service failure |
| `503` | Service unavailable |

---

# 7. API Resource Structure

```text
/api/v1
│
├── /network
├── /topology
├── /devices
├── /links
├── /services
├── /metrics
├── /logs
├── /events
├── /anomalies
├── /incidents
├── /root-causes
├── /evidence
├── /impact
├── /recommendations
├── /ai
├── /faults
├── /health
├── /analytics
└── /reports
```

---

# 8. Network API

## 8.1 Get Network Status

```http
GET /api/v1/network/status
```

### Response

```json
{
  "success": true,
  "data": {
    "status": "RUNNING",
    "health": "WARNING",
    "device_count": 6,
    "active_incidents": 1
  }
}
```

---

## 8.2 Start Network

```http
POST /api/v1/network/start
```

### Response

```json
{
  "success": true,
  "data": {
    "status": "RUNNING"
  },
  "message": "Network started"
}
```

---

## 8.3 Stop Network

```http
POST /api/v1/network/stop
```

---

## 8.4 Restart Network

```http
POST /api/v1/network/restart
```

---

## 8.5 Reset Network

```http
POST /api/v1/network/reset
```

This returns the Mininet environment to the initial state.

---

# 9. Topology API

## 9.1 Get Current Topology

```http
GET /api/v1/topology
```

### Response

```json
{
  "success": true,
  "data": {
    "nodes": [
      {
        "id": "r1",
        "name": "R1",
        "type": "ROUTER",
        "status": "HEALTHY"
      }
    ],
    "links": [
      {
        "id": "l1",
        "source": "r1",
        "target": "s1",
        "status": "UP"
      }
    ]
  }
}
```

---

## 9.2 Get Topology Snapshot

```http
GET /api/v1/topology/snapshots
```

### Query Parameters

```text
from
to
limit
```

---

## 9.3 Create Topology Snapshot

```http
POST /api/v1/topology/snapshots
```

### Request

```json
{
  "reason": "Pre-fault topology"
}
```

---

# 10. Device API

## 10.1 List Devices

```http
GET /api/v1/devices
```

### Query Parameters

```text
type
status
search
page
limit
```

---

## 10.2 Get Device

```http
GET /api/v1/devices/{device_id}
```

---

## 10.3 Create Device

```http
POST /api/v1/devices
```

### Request

```json
{
  "name": "R1",
  "device_type": "ROUTER",
  "ip_address": "10.0.0.1",
  "hostname": "router-1"
}
```

---

## 10.4 Update Device

```http
PATCH /api/v1/devices/{device_id}
```

---

## 10.5 Delete Device

```http
DELETE /api/v1/devices/{device_id}
```

Deletion should normally be restricted while the simulated network is running.

---

# 11. Link API

## 11.1 List Links

```http
GET /api/v1/links
```

### Filters

```text
status
source_device
destination_device
```

---

## 11.2 Get Link

```http
GET /api/v1/links/{link_id}
```

---

## 11.3 Create Link

```http
POST /api/v1/links
```

### Request

```json
{
  "source_device_id": "uuid",
  "destination_device_id": "uuid",
  "bandwidth_mbps": 100,
  "latency_ms": 10,
  "packet_loss_percent": 0
}
```

---

## 11.4 Update Link

```http
PATCH /api/v1/links/{link_id}
```

---

# 12. Service API

## 12.1 List Services

```http
GET /api/v1/services
```

---

## 12.2 Get Service

```http
GET /api/v1/services/{service_id}
```

---

## 12.3 Create Service

```http
POST /api/v1/services
```

### Request

```json
{
  "name": "DNS Server",
  "service_type": "DNS",
  "port": 53,
  "protocol": "UDP"
}
```

---

# 13. Metrics API

## 13.1 Get Latest Metrics

```http
GET /api/v1/metrics/latest
```

### Query Parameters

```text
device_id
metric_type
```

---

## 13.2 Get Historical Metrics

```http
GET /api/v1/metrics
```

### Query Parameters

```text
device_id
link_id
metric_type
from
to
interval
limit
```

### Example

```http
GET /api/v1/metrics?device_id=r1&metric_type=LATENCY&from=2026-10-01T10:00:00Z&to=2026-10-01T11:00:00Z
```

---

## 13.3 Get Device Metrics

```http
GET /api/v1/devices/{device_id}/metrics
```

---

## 13.4 Get Metric Summary

```http
GET /api/v1/metrics/summary
```

### Response

```json
{
  "success": true,
  "data": {
    "latency": {
      "avg": 42,
      "min": 20,
      "max": 312
    },
    "packet_loss": {
      "avg": 2.1,
      "max": 24
    }
  }
}
```

---

# 14. Logs API

## 14.1 List Logs

```http
GET /api/v1/logs
```

### Filters

```text
device_id
severity
event_type
from
to
search
page
limit
```

---

## 14.2 Get Log

```http
GET /api/v1/logs/{log_id}
```

---

## 14.3 Get Device Logs

```http
GET /api/v1/devices/{device_id}/logs
```

---

# 15. Events API

## 15.1 List Events

```http
GET /api/v1/events
```

### Filters

```text
device_id
link_id
service_id
event_type
severity
from
to
```

---

## 15.2 Get Event

```http
GET /api/v1/events/{event_id}
```

---

## 15.3 Get Event Timeline

```http
GET /api/v1/events/timeline
```

### Query Parameters

```text
from
to
incident_id
device_id
```

---

## 15.4 Correlate Events

```http
POST /api/v1/events/correlate
```

### Request

```json
{
  "event_ids": [
    "event-1",
    "event-2",
    "event-3"
  ]
}
```

### Response

```json
{
  "success": true,
  "data": {
    "correlated": true,
    "relationship": "LIKELY_SAME_INCIDENT",
    "confidence": 0.91
  }
}
```

---

# 16. Anomaly API

## 16.1 List Anomalies

```http
GET /api/v1/anomalies
```

### Filters

```text
device_id
severity
is_anomaly
from
to
```

---

## 16.2 Get Anomaly

```http
GET /api/v1/anomalies/{anomaly_id}
```

---

## 16.3 Run Anomaly Detection

```http
POST /api/v1/anomalies/detect
```

### Request

```json
{
  "device_id": "uuid",
  "metric_types": [
    "LATENCY",
    "PACKET_LOSS"
  ]
}
```

### Response

```json
{
  "success": true,
  "data": {
    "anomalies_detected": 2
  }
}
```

---

## 16.4 Get Anomaly Statistics

```http
GET /api/v1/anomalies/statistics
```

---

# 17. Incident API

## 17.1 List Incidents

```http
GET /api/v1/incidents
```

### Query Parameters

```text
status
severity
from
to
search
page
limit
```

---

## 17.2 Get Incident

```http
GET /api/v1/incidents/{incident_id}
```

The response should include:

```text
Incident
Root Cause
Evidence
Timeline
Impact
Recommendations
AI Analysis
```

---

## 17.3 Create Incident

```http
POST /api/v1/incidents
```

### Request

```json
{
  "title": "Network connectivity issue",
  "severity": "HIGH",
  "description": "Multiple downstream services are timing out."
}
```

Normally, automatic incidents should be created by the correlation/RCA pipeline rather than manually.

---

## 17.4 Update Incident

```http
PATCH /api/v1/incidents/{incident_id}
```

### Request

```json
{
  "status": "RESOLVED"
}
```

---

## 17.5 Close Incident

```http
POST /api/v1/incidents/{incident_id}/close
```

---

## 17.6 Resolve Incident

```http
POST /api/v1/incidents/{incident_id}/resolve
```

---

## 17.7 Get Incident Timeline

```http
GET /api/v1/incidents/{incident_id}/timeline
```

---

# 18. Incident Event API

## 18.1 Get Incident Events

```http
GET /api/v1/incidents/{incident_id}/events
```

---

## 18.2 Add Event to Incident

```http
POST /api/v1/incidents/{incident_id}/events
```

### Request

```json
{
  "event_id": "uuid",
  "sequence_number": 4,
  "relationship_type": "DOWNSTREAM_SYMPTOM"
}
```

---

# 19. Root Cause API

## 19.1 Get Root Causes

```http
GET /api/v1/incidents/{incident_id}/root-causes
```

---

## 19.2 Get Root Cause

```http
GET /api/v1/root-causes/{root_cause_id}
```

---

## 19.3 Run RCA

```http
POST /api/v1/incidents/{incident_id}/root-cause/analyze
```

### Request

```json
{
  "include_topology": true,
  "include_logs": true,
  "include_metrics": true,
  "include_anomalies": true
}
```

### Response

```json
{
  "success": true,
  "data": {
    "root_cause": {
      "type": "INTERFACE_FAILURE",
      "device": "R1",
      "description": "R1 interface failure",
      "confidence": 0.92
    }
  }
}
```

---

# 20. Root Cause Evidence API

## 20.1 Get Evidence

```http
GET /api/v1/root-causes/{root_cause_id}/evidence
```

---

## 20.2 Add Evidence

```http
POST /api/v1/root-causes/{root_cause_id}/evidence
```

### Request

```json
{
  "source_type": "EVENT",
  "source_id": "uuid",
  "description": "R1 interface failure occurred before packet loss.",
  "importance": "HIGH"
}
```

---

# 21. Impact API

## 21.1 Get Incident Impact

```http
GET /api/v1/incidents/{incident_id}/impact
```

### Response

```json
{
  "success": true,
  "data": {
    "affected_devices": 3,
    "affected_links": 1,
    "affected_services": 2,
    "severity": "HIGH"
  }
}
```

---

## 21.2 Run Impact Analysis

```http
POST /api/v1/incidents/{incident_id}/impact/analyze
```

---

# 22. Failure Propagation API

## 22.1 Get Failure Chain

```http
GET /api/v1/incidents/{incident_id}/failure-chain
```

### Response

```json
{
  "success": true,
  "data": {
    "chain": [
      {
        "sequence": 1,
        "event": "R1 interface failure"
      },
      {
        "sequence": 2,
        "event": "Packet loss"
      },
      {
        "sequence": 3,
        "event": "High latency"
      },
      {
        "sequence": 4,
        "event": "Server timeout"
      }
    ]
  }
}
```

---

# 23. Recommendation API

## 23.1 Get Recommendations

```http
GET /api/v1/incidents/{incident_id}/recommendations
```

---

## 23.2 Generate Recommendation

```http
POST /api/v1/incidents/{incident_id}/recommendations/generate
```

---

## 23.3 Update Recommendation

```http
PATCH /api/v1/recommendations/{recommendation_id}
```

### Example

```json
{
  "status": "REVIEWED"
}
```

---

# 24. Gemini AI API

Gemini should be accessed through the FastAPI backend.

The frontend should never directly expose the Gemini API key.

---

## 24.1 Explain Incident

```http
POST /api/v1/ai/incidents/{incident_id}/explain
```

### Request

```json
{
  "detail_level": "technical"
}
```

### Response

```json
{
  "success": true,
  "data": {
    "analysis_type": "INCIDENT_EXPLANATION",
    "summary": "R1 interface failure appears to be the primary cause...",
    "explanation": "...",
    "recommendations": [
      "Inspect R1 interface",
      "Check routing configuration"
    ]
  }
}
```

---

## 24.2 Explain Root Cause

```http
POST /api/v1/ai/root-causes/{root_cause_id}/explain
```

---

## 24.3 Explain Failure Chain

```http
POST /api/v1/ai/incidents/{incident_id}/failure-chain/explain
```

---

## 24.4 Generate Incident Report

```http
POST /api/v1/ai/incidents/{incident_id}/report
```

---

## 24.5 Ask About Incident

```http
POST /api/v1/ai/incidents/{incident_id}/ask
```

### Request

```json
{
  "question": "Why do you think R1 is the root cause?"
}
```

### Response

```json
{
  "success": true,
  "data": {
    "answer": "R1 is considered the probable root cause because..."
  }
}
```

---

# 25. Fault Injection API

Fault injection is one of the most important demo features.

## 25.1 List Fault Types

```http
GET /api/v1/faults/types
```

### Response

```json
{
  "success": true,
  "data": [
    "ROUTER_FAILURE",
    "INTERFACE_FAILURE",
    "SWITCH_FAILURE",
    "LINK_FAILURE",
    "PACKET_LOSS",
    "HIGH_LATENCY",
    "CONGESTION",
    "DNS_FAILURE",
    "SERVER_OVERLOAD",
    "SERVER_UNAVAILABLE",
    "HIGH_ERROR_RATE",
    "BANDWIDTH_REDUCTION"
  ]
}
```

---

## 25.2 Inject Fault

```http
POST /api/v1/faults/inject
```

### Request

```json
{
  "fault_type": "INTERFACE_FAILURE",
  "device_id": "uuid",
  "duration_seconds": 60,
  "severity": "HIGH"
}
```

### Response

```json
{
  "success": true,
  "data": {
    "fault_id": "uuid",
    "status": "ACTIVE"
  }
}
```

---

## 25.3 Get Fault

```http
GET /api/v1/faults/{fault_id}
```

---

## 25.4 List Fault History

```http
GET /api/v1/faults
```

### Filters

```text
fault_type
status
device_id
from
to
```

---

## 25.5 Recover Fault

```http
POST /api/v1/faults/{fault_id}/recover
```

---

## 25.6 Reset All Faults

```http
POST /api/v1/faults/reset
```

---

# 26. Network Health API

## 26.1 Get Current Health

```http
GET /api/v1/health/network
```

### Response

```json
{
  "success": true,
  "data": {
    "score": 78,
    "status": "WARNING",
    "latency": 42,
    "packet_loss": 2.1,
    "active_incidents": 1,
    "failed_devices": 1
  }
}
```

---

## 26.2 Get Device Health

```http
GET /api/v1/health/devices/{device_id}
```

---

## 26.3 Get Health History

```http
GET /api/v1/health/history
```

---

# 27. Analytics API

## 27.1 Dashboard Summary

```http
GET /api/v1/analytics/dashboard
```

### Response

```json
{
  "success": true,
  "data": {
    "network_health": 78,
    "active_incidents": 1,
    "critical_incidents": 1,
    "anomalies_today": 14,
    "devices_down": 1
  }
}
```

---

## 27.2 Incident Statistics

```http
GET /api/v1/analytics/incidents
```

---

## 27.3 Anomaly Statistics

```http
GET /api/v1/analytics/anomalies
```

---

## 27.4 Fault Statistics

```http
GET /api/v1/analytics/faults
```

---

## 27.5 Root Cause Statistics

```http
GET /api/v1/analytics/root-causes
```

---

# 28. Reports API

## 28.1 Generate Report

```http
POST /api/v1/reports/incidents/{incident_id}
```

---

## 28.2 Get Report

```http
GET /api/v1/reports/incidents/{incident_id}
```

---

## 28.3 Export Report

```http
GET /api/v1/reports/incidents/{incident_id}/export
```

Possible formats:

```text
JSON
Markdown
PDF (future)
```

---

# 29. Health Check API

## 29.1 API Health

```http
GET /api/v1/health
```

### Response

```json
{
  "success": true,
  "data": {
    "api": "UP",
    "database": "UP",
    "mininet": "UP",
    "gemini": "UP"
  }
}
```

---

# 30. Authentication Architecture

Authentication is optional for the first academic MVP.

If authentication is added, use Supabase Auth.

### Flow

```text
User
 ↓
Supabase Auth
 ↓
Access Token
 ↓
FastAPI
 ↓
Token Validation
 ↓
Protected API
```

Potential roles:

```text
ADMIN
NETWORK_OPERATOR
VIEWER
```

---

# 31. Authorization

Possible permissions:

| Action | Admin | Operator | Viewer |
|---|---:|---:|---:|
| View dashboard | Yes | Yes | Yes |
| View metrics | Yes | Yes | Yes |
| View logs | Yes | Yes | Yes |
| View incidents | Yes | Yes | Yes |
| Run RCA | Yes | Yes | Yes |
| Inject fault | Yes | Yes | No |
| Reset network | Yes | Yes | No |
| Generate AI analysis | Yes | Yes | Yes |
| Modify devices | Yes | Yes | No |
| Modify configuration | Yes | Yes | No |

---

# 32. Pagination

Large resources should support pagination.

### Query

```text
?page=1&limit=50
```

### Response

```json
{
  "success": true,
  "data": [],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 245,
    "pages": 5
  }
}
```

---

# 33. Filtering

Supported filters should include:

```text
device_id
link_id
service_id
severity
status
event_type
metric_type
fault_type
from
to
search
```

---

# 34. Sorting

Resources should support:

```text
?sort=timestamp
?order=desc
```

Example:

```http
GET /api/v1/incidents?sort=start_time&order=desc
```

---

# 35. Error Codes

Recommended application-level codes:

```text
NETWORK_NOT_RUNNING
NETWORK_ALREADY_RUNNING
DEVICE_NOT_FOUND
LINK_NOT_FOUND
SERVICE_NOT_FOUND
METRIC_NOT_FOUND
EVENT_NOT_FOUND
INCIDENT_NOT_FOUND
ROOT_CAUSE_NOT_FOUND
INVALID_FAULT_TYPE
FAULT_NOT_FOUND
FAULT_ALREADY_RECOVERED
RCA_FAILED
ANOMALY_DETECTION_FAILED
GEMINI_UNAVAILABLE
GEMINI_REQUEST_FAILED
DATABASE_ERROR
MININET_ERROR
VALIDATION_ERROR
UNAUTHORIZED
FORBIDDEN
```

---

# 36. API Validation Rules

FastAPI/Pydantic should validate:

- UUIDs
- IP addresses
- Device types
- Metric types
- Event types
- Severity
- Incident status
- Fault type
- Numeric ranges
- Timestamp formats
- Required fields

### Example

Packet loss:

```text
0 <= packet_loss <= 100
```

Confidence:

```text
0 <= confidence <= 1
```

Severity:

```text
LOW
MEDIUM
HIGH
CRITICAL
```

---

# 37. RCA API Flow

The complete RCA request should follow:

```text
POST /incidents/{id}/root-cause/analyze
                 │
                 ▼
        Load Incident Data
                 │
       ┌─────────┼─────────┐
       ▼         ▼         ▼
    Metrics     Logs     Events
       │         │         │
       └─────────┼─────────┘
                 ▼
            Anomalies
                 │
                 ▼
             NetworkX
                 │
                 ▼
        Event Correlation
                 │
                 ▼
          Candidate Causes
                 │
                 ▼
          Evidence Scoring
                 │
                 ▼
          Root Cause Result
                 │
                 ▼
              Supabase
```

---

# 38. Gemini API Flow

```text
POST /ai/incidents/{id}/explain
                │
                ▼
        FastAPI AI Service
                │
                ▼
      Collect Structured RCA
                │
                ├── Root Cause
                ├── Evidence
                ├── Timeline
                ├── Impact
                └── Metrics
                │
                ▼
            Gemini API
                │
                ▼
      Structured AI Response
                │
                ▼
            Supabase
                │
                ▼
            Dashboard
```

---

# 39. Fault Injection Flow

```text
POST /faults/inject
        │
        ▼
FastAPI
        │
        ▼
Fault Injection Service
        │
        ▼
Mininet
        │
        ▼
Network Behavior Changes
        │
        ▼
Metrics / Logs / Events
        │
        ▼
Anomaly Detection
        │
        ▼
Incident Pipeline
```

---

# 40. Dashboard API Consumption

The dashboard should primarily use these endpoints.

## Main Dashboard

```text
GET /health/network
GET /analytics/dashboard
GET /metrics/latest
GET /incidents?status=ACTIVE
GET /topology
```

## Incident Page

```text
GET /incidents/{id}
GET /incidents/{id}/timeline
GET /incidents/{id}/events
GET /incidents/{id}/root-causes
GET /incidents/{id}/impact
GET /incidents/{id}/recommendations
GET /incidents/{id}/failure-chain
```

## AI Panel

```text
POST /ai/incidents/{id}/explain
POST /ai/incidents/{id}/ask
POST /ai/incidents/{id}/report
```

---

# 41. API Security

## Gemini

Never expose:

```text
GEMINI_API_KEY
```

to the frontend.

Correct:

```text
Frontend → FastAPI → Gemini
```

Incorrect:

```text
Frontend → Gemini
```

## Supabase

Sensitive server-side keys must never be exposed to the browser.

## Fault Injection

Fault endpoints must be protected if authentication is enabled.

---

# 42. Rate Limiting

Rate limits should be considered for:

- Gemini endpoints
- AI question endpoints
- Fault injection
- Report generation

Example:

```text
AI endpoints:
10 requests/minute/user
```

Exact limits can be adjusted after testing.

---

# 43. Idempotency

Operations that can accidentally be repeated should support idempotency where appropriate.

Examples:

```text
POST /network/start
POST /faults/inject
POST /reports
```

For fault injection, the backend should avoid creating duplicate active faults unless explicitly requested.

---

# 44. API Documentation

FastAPI automatically provides:

```text
/docs
```

Swagger UI.

And:

```text
/redoc
```

ReDoc.

The API should use meaningful:

- endpoint descriptions
- request models
- response models
- examples
- error responses

---

# 45. Suggested FastAPI Project Structure

```text
backend/
│
├── app/
│   ├── main.py
│   │
│   ├── api/
│   │   └── v1/
│   │       ├── network.py
│   │       ├── topology.py
│   │       ├── devices.py
│   │       ├── links.py
│   │       ├── services.py
│   │       ├── metrics.py
│   │       ├── logs.py
│   │       ├── events.py
│   │       ├── anomalies.py
│   │       ├── incidents.py
│   │       ├── root_causes.py
│   │       ├── impact.py
│   │       ├── recommendations.py
│   │       ├── ai.py
│   │       ├── faults.py
│   │       ├── health.py
│   │       ├── analytics.py
│   │       └── reports.py
│   │
│   ├── schemas/
│   ├── models/
│   ├── services/
│   ├── rca/
│   ├── anomaly/
│   ├── topology/
│   ├── monitoring/
│   ├── agents/
│   └── core/
│
└── tests/
```

---

# 46. API Feature Inventory

## Network API

- Network status
- Start network
- Stop network
- Restart network
- Reset network

## Topology API

- Get topology
- Get snapshots
- Create snapshot

## Device API

- List devices
- Get device
- Create device
- Update device
- Delete device
- Device metrics
- Device logs
- Device health

## Link API

- List links
- Get link
- Create link
- Update link

## Service API

- List services
- Get service
- Create service

## Metrics API

- Latest metrics
- Historical metrics
- Device metrics
- Metric summary

## Logs API

- List logs
- Get log
- Device logs
- Search
- Filtering

## Events API

- List events
- Get event
- Event timeline
- Event correlation

## Anomaly API

- List anomalies
- Get anomaly
- Run detection
- Anomaly statistics

## Incident API

- List incidents
- Get incident
- Create incident
- Update incident
- Resolve incident
- Close incident
- Incident timeline
- Incident events

## RCA API

- Run RCA
- Get root causes
- Get root cause
- Get evidence
- Add evidence
- Failure chain

## Impact API

- Run impact analysis
- Get impact

## Recommendation API

- Get recommendations
- Generate recommendations
- Update recommendation

## Gemini API

- Explain incident
- Explain root cause
- Explain failure chain
- Generate incident report
- Ask questions

## Fault API

- List fault types
- Inject fault
- Get fault
- Fault history
- Recover fault
- Reset faults

## Health API

- API health
- Network health
- Device health
- Health history

## Analytics API

- Dashboard summary
- Incident statistics
- Anomaly statistics
- Fault statistics
- Root-cause statistics

## Reports API

- Generate report
- Get report
- Export report

---

# 47. Recommended MVP API

Do not implement every endpoint before the core system works.

The minimum first version should implement:

```text
GET  /api/v1/network/status
POST /api/v1/network/start
POST /api/v1/network/stop
GET  /api/v1/topology

GET  /api/v1/devices
GET  /api/v1/metrics
GET  /api/v1/logs
GET  /api/v1/events
GET  /api/v1/anomalies

GET  /api/v1/incidents
GET  /api/v1/incidents/{id}
GET  /api/v1/incidents/{id}/timeline

POST /api/v1/incidents/{id}/root-cause/analyze
GET  /api/v1/incidents/{id}/root-causes
GET  /api/v1/incidents/{id}/impact
GET  /api/v1/incidents/{id}/failure-chain

POST /api/v1/ai/incidents/{id}/explain
POST /api/v1/ai/incidents/{id}/report

GET  /api/v1/faults/types
POST /api/v1/faults/inject
POST /api/v1/faults/{id}/recover

GET  /api/v1/health/network
GET  /api/v1/analytics/dashboard
```

This is enough to demonstrate the complete NetRCA workflow.

---

# 48. Complete End-to-End API Scenario

## User Injects Router Failure

```text
POST /api/v1/faults/inject
```

↓

Mininet disables R1 interface.

↓

Metrics change.

```text
GET /api/v1/metrics
```

↓

Anomaly detection identifies abnormal behavior.

```text
POST /api/v1/anomalies/detect
```

↓

Events are correlated.

```text
POST /api/v1/events/correlate
```

↓

Incident is created.

```text
GET /api/v1/incidents
```

↓

RCA is executed.

```text
POST /api/v1/incidents/{id}/root-cause/analyze
```

↓

Impact is analyzed.

```text
POST /api/v1/incidents/{id}/impact/analyze
```

↓

Failure chain is generated.

```text
GET /api/v1/incidents/{id}/failure-chain
```

↓

Gemini explains the result.

```text
POST /api/v1/ai/incidents/{id}/explain
```

↓

Recommendation is generated.

```text
POST /api/v1/incidents/{id}/recommendations/generate
```

↓

Dashboard displays the complete investigation.

---

# 49. Final API Architecture

```text
                        USER
                         │
                         ▼
                 NEXT.JS DASHBOARD
                         │
                         │ REST / JSON
                         ▼
                ┌─────────────────┐
                │     FASTAPI     │
                │    /api/v1      │
                └────────┬────────┘
                         │
       ┌─────────────────┼──────────────────────┐
       │                 │                      │
       ▼                 ▼                      ▼
   NETWORK            ANALYSIS                 DATA
   SERVICES           SERVICES                SERVICES
       │                 │                      │
       │          ┌──────┼──────┐               │
       │          ▼      ▼      ▼               │
       │         ML    RCA   NetworkX           │
       │          │      │      │               │
       └──────────┴──────┼──────┘               │
                         │                      │
                         ▼                      ▼
                     GEMINI                 SUPABASE
                       API                  PostgreSQL
                         │
                         ▼
                    AI Analysis
                         │
                         └──────────────► Dashboard
```

---

# 50. Final API Design Principles

1. **Version every application endpoint under `/api/v1`.**
2. **Use REST resources with predictable naming.**
3. **Use Pydantic models for request and response validation.**
4. **Return consistent success and error structures.**
5. **Use standard HTTP status codes.**
6. **Keep Gemini behind FastAPI.**
7. **Keep the Gemini API key server-side.**
8. **Keep Mininet control behind the backend.**
9. **Separate raw data APIs from derived RCA APIs.**
10. **Preserve evidence for every RCA finding.**
11. **Make incident investigation accessible through one incident resource.**
12. **Use filtering, pagination, and sorting for high-volume resources.**
13. **Protect fault-injection and network-control endpoints.**
14. **Keep the MVP API small enough to implement reliably.**
15. **Expand the API only when the corresponding feature exists.**
16. **Make API responses predictable for the frontend.**
17. **Store Gemini analyses separately from deterministic RCA results.**
18. **Never allow the AI layer to directly execute destructive production actions.**

---

# 51. Final API Workflow

The complete NetRCA API workflow is:

```text
                MININET
                   │
                   ▼
             DATA COLLECTION
                   │
                   ▼
              FASTAPI
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
     Metrics     Logs       Events
        │          │          │
        └──────────┼──────────┘
                   ▼
            ANOMALY API
                   │
                   ▼
           CORRELATION API
                   │
                   ▼
            INCIDENT API
                   │
                   ▼
             RCA API
                   │
             ┌─────┴─────┐
             ▼           ▼
        IMPACT API    EVIDENCE API
             │           │
             └─────┬─────┘
                   ▼
               GEMINI API
                   │
                   ▼
          RECOMMENDATION API
                   │
                   ▼
              SUPABASE
                   │
                   ▼
             DASHBOARD
```

This API design provides a complete, modular contract between the NetRCA frontend, backend, ML/RCA engine, Mininet simulation, Gemini AI layer, and Supabase database while keeping the core MVP implementable and extensible.
