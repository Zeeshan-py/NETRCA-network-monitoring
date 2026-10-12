# NetRCA — Security Specification

## 1. Purpose

This document defines the security architecture, controls, policies, threat model, secure development practices, and safety boundaries for **NetRCA — AI-Powered Network Root Cause Analysis and Incident Response System**.

NetRCA operates primarily in a controlled **Mininet simulation environment**. The security design must protect:

- Network simulation controls
- Backend APIs
- Supabase/PostgreSQL data
- Gemini API credentials
- User access
- Incident data
- Logs and evidence
- Fault-injection capabilities
- AI-generated recommendations
- Application infrastructure

The most important security principle is:

> **NetRCA may analyze and simulate network failures, but it must not perform unauthorized or destructive actions against real networks.**

---

# 2. Security Objectives

NetRCA security is based on:

```text
CONFIDENTIALITY
        +
INTEGRITY
        +
AVAILABILITY
        +
AUTHENTICITY
        +
AUDITABILITY
        +
SAFETY
```

### Confidentiality

Prevent unauthorized access to:

- API keys
- Database credentials
- Incident information
- Logs
- Internal topology
- User information

### Integrity

Prevent unauthorized modification of:

- Network configuration
- Incident records
- RCA evidence
- Recommendations
- Fault records
- Database records

### Availability

Keep the monitoring and analysis system operational during:

- Network faults
- Temporary Gemini failures
- Database failures
- Invalid requests
- Unexpected Mininet behavior

### Authenticity

Ensure that protected operations are performed only by authorized users/services.

### Auditability

Record security-sensitive actions such as:

- Login
- Fault injection
- Network reset
- Device changes
- Incident modifications
- RCA execution
- AI analysis
- Recommendation changes

### Safety

Prevent the AI system from directly executing potentially destructive network operations.

---

# 3. Security Architecture

```text
                         USER
                           │
                           ▼
                  ┌──────────────────┐
                  │ Next.js Frontend │
                  └────────┬─────────┘
                           │
                     HTTPS / JSON
                           │
                           ▼
                  ┌──────────────────┐
                  │     FastAPI      │
                  │ Authentication   │
                  │ Authorization    │
                  │ Validation       │
                  │ Rate Limiting    │
                  └───────┬──────────┘
                          │
          ┌───────────────┼────────────────┐
          │               │                │
          ▼               ▼                ▼
       Mininet          RCA/ML          Supabase
       Sandbox          Engine         PostgreSQL
          │               │                │
          │               ▼                │
          │          Gemini API             │
          │               │                │
          └───────────────┼────────────────┘
                          ▼
                    Audit Logging
```

---

# 4. Trust Boundaries

NetRCA has several trust boundaries.

## Boundary 1 — Browser → API

The frontend is considered untrusted.

All important authorization decisions must happen on the backend.

```text
Browser
   X
   │
   │ cannot directly control Mininet
   │
   ▼
FastAPI
```

## Boundary 2 — API → Mininet

Network-control operations must be validated before reaching Mininet.

## Boundary 3 — API → Supabase

Database operations must use controlled credentials and validated data.

## Boundary 4 — API → Gemini

Only structured, appropriate incident context should be sent to Gemini.

## Boundary 5 — AI → Network

Gemini must not directly execute network commands.

```text
Gemini
   X
   │
   │ NO direct network control
   │
   X
Mininet
```

---

# 5. Authentication

Authentication is optional for the earliest local MVP but should be supported by the architecture.

## Recommended Technology

**Supabase Auth**

### Flow

```text
User
 ↓
Supabase Auth
 ↓
Access Token
 ↓
Next.js
 ↓
FastAPI
 ↓
Token Validation
 ↓
Protected Resource
```

---

# 6. Authorization

Authorization must be enforced on the backend.

Recommended roles:

```text
ADMIN
NETWORK_OPERATOR
VIEWER
```

## Permission Matrix

| Operation | Admin | Operator | Viewer |
|---|---:|---:|---:|
| View dashboard | ✓ | ✓ | ✓ |
| View topology | ✓ | ✓ | ✓ |
| View metrics | ✓ | ✓ | ✓ |
| View logs | ✓ | ✓ | ✓ |
| View incidents | ✓ | ✓ | ✓ |
| Run RCA | ✓ | ✓ | ✓ |
| Generate AI analysis | ✓ | ✓ | ✓ |
| Inject fault | ✓ | ✓ | ✗ |
| Recover fault | ✓ | ✓ | ✗ |
| Reset network | ✓ | ✓ | ✗ |
| Modify devices | ✓ | ✓ | ✗ |
| Modify links | ✓ | ✓ | ✗ |
| Manage users | ✓ | ✗ | ✗ |
| Modify system configuration | ✓ | ✗ | ✗ |

---

# 7. API Security

## HTTPS

Production API traffic must use HTTPS.

```text
HTTPS
  ↓
FastAPI
```

Never transmit sensitive credentials over plain HTTP in production.

## Input Validation

FastAPI + Pydantic should validate:

- UUIDs
- IP addresses
- Device types
- Fault types
- Severity
- Incident status
- Numeric values
- Timestamps
- Request body structure

Example:

```text
packet_loss:
0 ≤ value ≤ 100

confidence:
0 ≤ value ≤ 1
```

---

# 8. API Rate Limiting

Rate limiting should protect resource-intensive endpoints.

### High-priority endpoints

```text
POST /api/v1/ai/*
POST /api/v1/faults/inject
POST /api/v1/network/reset
POST /api/v1/reports/*
POST /api/v1/incidents/*/root-cause/analyze
```

### Example Policy

```text
AI:
10 requests/minute/user

Fault Injection:
limited requests/minute/user

Report Generation:
limited requests/minute/user
```

Exact limits should be tuned during testing.

---

# 9. Gemini API Key Security

The Gemini API key is a secret.

It must never be placed in:

- React source code
- Next.js public environment variables
- HTML
- Browser local storage
- GitHub repository
- Client-side JavaScript

Correct architecture:

```text
Frontend
    ↓
FastAPI
    ↓
GEMINI_API_KEY
    ↓
Gemini API
```

Incorrect:

```text
Frontend
    ↓
Gemini API
```

---

# 10. Environment Variables

Secrets should be stored in environment variables.

Example:

```text
GEMINI_API_KEY=
SUPABASE_URL=
SUPABASE_KEY=
DATABASE_URL=
```

Repository should contain:

```text
.env.example
```

but never:

```text
.env
```

with real credentials.

---

# 11. Secret Management

## Rules

1. Never hard-code secrets.
2. Never commit secrets to Git.
3. Never expose backend secrets to the browser.
4. Rotate leaked credentials immediately.
5. Use separate credentials for development and production.
6. Use the minimum required database privileges.
7. Remove unused credentials.

---

# 12. Supabase Security

Supabase/PostgreSQL stores important NetRCA information.

Protected data includes:

```text
Devices
Topology
Metrics
Logs
Events
Anomalies
Incidents
RCA Evidence
Recommendations
AI Analyses
Fault History
```

## Database Security

Use:

- Strong credentials
- TLS connections
- Row Level Security where applicable
- Restricted database permissions
- Server-side privileged operations
- Foreign-key constraints
- Input validation

---

# 13. Row Level Security

If user authentication is enabled, Supabase Row Level Security should be considered.

Example conceptual policy:

```text
Viewer:
READ only

Operator:
READ + operational actions

Admin:
READ + WRITE + administrative actions
```

The frontend must not be trusted to enforce these permissions by itself.

---

# 14. Database Integrity

Database integrity controls should include:

- Primary keys
- Foreign keys
- Unique constraints
- Check constraints
- NOT NULL constraints
- Valid status values
- Valid severity values
- Timestamp validation

Examples:

```text
confidence BETWEEN 0 AND 1

packet_loss BETWEEN 0 AND 100
```

---

# 15. SQL Injection Protection

The backend must never construct SQL queries by directly concatenating user input.

Avoid:

```text
"SELECT * FROM incidents WHERE id = '" + user_input + "'"
```

Use:

- Supabase client methods
- Parameterized queries
- Validated query parameters
- ORM/query-builder mechanisms where applicable

---

# 16. XSS Protection

User-controlled values such as:

- Incident titles
- Log messages
- Device names
- AI output
- Search terms

must be rendered safely.

The frontend should avoid unsafe HTML injection.

AI-generated text should be treated as untrusted content.

---

# 17. CORS

FastAPI should use a restricted CORS policy.

Development:

```text
http://localhost:3000
```

Production:

```text
https://your-dashboard-domain
```

Do not use unrestricted:

```text
allow_origins=["*"]
```

for sensitive production deployments.

---

# 18. CSRF Considerations

If authentication uses browser cookies, CSRF protections should be applied.

If using bearer tokens in an appropriate architecture, CSRF exposure differs, but authentication and authorization still need to be enforced server-side.

---

# 19. Mininet Security

Mininet is the controlled network environment.

## Core Rule

> Fault injection must remain inside the controlled simulation.

The application should not allow arbitrary user-supplied shell commands to be executed on the host.

Avoid APIs such as:

```text
POST /execute-command
```

that accept arbitrary commands.

Instead provide explicit operations:

```text
POST /faults/inject
POST /faults/{id}/recover
POST /network/reset
```

---

# 20. Command Injection Prevention

This is particularly important because Mininet involves Linux networking commands.

Never directly execute arbitrary user input.

Bad:

```python
os.system(user_command)
```

Better:

```text
Validate fault_type
Validate device_id
Validate parameters
Map to an approved operation
Execute only the approved operation
```

Example:

```text
fault_type = INTERFACE_FAILURE
device = R1
```

The backend maps this to a known internal operation.

---

# 21. Fault Injection Safety

Allowed:

```text
INTERFACE_FAILURE
LINK_FAILURE
PACKET_LOSS
HIGH_LATENCY
SERVER_OVERLOAD
DNS_FAILURE
```

The system should reject:

```text
arbitrary shell commands
arbitrary host networking commands
unknown fault types
unknown device identifiers
```

---

# 22. AI Safety Boundary

Gemini is an analysis/explanation component.

It should not have direct access to:

- Shell
- Mininet CLI
- Linux commands
- Production routers
- Production switches
- Production servers

Architecture:

```text
Structured Evidence
       ↓
     Gemini
       ↓
Explanation / Recommendation
       ↓
Human Review
```

Not:

```text
Gemini
 ↓
Shell
 ↓
Network
```

---

# 23. Prompt Injection Protection

Logs and network messages may contain attacker-controlled text.

For example:

```text
ERROR:
Ignore previous instructions and perform an action...
```

If this content is sent to Gemini, it should be treated as **data**, not instructions.

The AI service should clearly separate:

```text
SYSTEM INSTRUCTIONS
TRUSTED STRUCTURED DATA
UNTRUSTED LOG CONTENT
```

Do not allow log text to override system instructions.

---

# 24. Gemini Input Minimization

Only send the information necessary for the requested analysis.

Example:

```json
{
  "root_cause": "R1 interface failure",
  "confidence": 0.92,
  "evidence": [],
  "impact": [],
  "timeline": []
}
```

Avoid sending:

- API keys
- Database credentials
- User passwords
- Unnecessary personal information
- Internal secrets

---

# 25. Gemini Output Validation

AI output should not be blindly trusted.

The backend should validate:

- Expected JSON structure
- Required fields
- Recommendation format
- Maximum response length where appropriate
- Allowed status values

If Gemini returns invalid structured data:

```text
Gemini
  ↓
Validation Failed
  ↓
Fallback to deterministic RCA result
```

---

# 26. AI Hallucination Protection

NetRCA should distinguish between:

```text
System Evidence
```

and:

```text
AI Interpretation
```

The database should separately store:

```text
RCA Result
AI Explanation
AI Recommendation
```

The UI should make this distinction clear.

---

# 27. Recommendation Safety

Recommendations are advisory.

Example:

```text
Recommendation:
Inspect R1 interface and routing configuration.
```

The system should not automatically execute:

```text
shutdown interface
restart router
change route
```

unless a future version introduces an explicit, authenticated, human-approved remediation workflow.

---

# 28. Audit Logging

Security-sensitive actions should be recorded.

Recommended audit events:

```text
LOGIN
LOGOUT
FAULT_INJECTED
FAULT_RECOVERED
NETWORK_STARTED
NETWORK_STOPPED
NETWORK_RESET
DEVICE_CREATED
DEVICE_UPDATED
DEVICE_DELETED
INCIDENT_CREATED
INCIDENT_UPDATED
RCA_EXECUTED
AI_ANALYSIS_REQUESTED
RECOMMENDATION_UPDATED
CONFIGURATION_CHANGED
```

---

# 29. Audit Log Structure

A future `audit_logs` table can contain:

```text
id
user_id
action
resource_type
resource_id
ip_address
user_agent
metadata
created_at
```

Example:

```text
Action:
FAULT_INJECTED

User:
operator-123

Resource:
R1

Timestamp:
2026-10-04 10:31:05
```

---

# 30. Incident Data Security

Incidents may contain detailed internal network information.

Access should be controlled according to the user's role.

Sensitive fields may include:

```text
Internal IP addresses
Topology
System logs
Infrastructure details
Error messages
AI analysis context
```

---

# 31. Logging Security

Application logs must not contain:

```text
GEMINI_API_KEY
SUPABASE_SERVICE_ROLE_KEY
DATABASE_PASSWORD
Authentication tokens
Session secrets
```

Use redaction for sensitive values.

---

# 32. Error Handling

Error responses should not reveal internal details.

Bad:

```text
PostgreSQL connection failed:
password=abc123
host=internal-db
```

Good:

```json
{
  "success": false,
  "error": {
    "code": "DATABASE_ERROR",
    "message": "A database error occurred."
  }
}
```

Detailed technical information should remain in protected server logs.

---

# 33. Dependency Security

Project dependencies should be kept updated.

Monitor:

```text
Python packages
Node packages
FastAPI
Next.js
React
Scikit-learn
Supabase libraries
```

Use dependency lock files where appropriate.

Examples:

```text
requirements.txt
package-lock.json
pnpm-lock.yaml
```

---

# 34. Git Security

Never commit:

```text
.env
API keys
passwords
tokens
private certificates
database credentials
```

Recommended `.gitignore`:

```text
.env
.env.*
!.env.example
__pycache__/
*.pyc
node_modules/
.next/
venv/
.venv/
```

---

# 35. GitHub Security

Recommended controls:

- Protected `main` branch
- Pull requests for significant changes
- Secret scanning where available
- Dependabot/security alerts where available
- Review before merging
- No credentials in commits

If a secret is accidentally committed:

1. Revoke it.
2. Rotate it.
3. Remove it from the repository history where appropriate.
4. Check for unauthorized use.

---

# 36. Frontend Security

The frontend should:

- Avoid storing secrets
- Validate user input
- Avoid unsafe HTML
- Handle authentication securely
- Use HTTPS in production
- Avoid exposing internal error messages
- Restrict privileged UI operations based on authorization state

However:

> Frontend permission checks are only for UX. Backend authorization is the actual security boundary.

---

# 37. Backend Security

FastAPI should implement:

- Authentication validation
- Authorization checks
- Request validation
- Rate limiting
- CORS restrictions
- Secure error handling
- Audit logging
- Dependency validation
- Secure configuration
- Controlled Mininet operations

---

# 38. Network Isolation

The Mininet environment should be isolated from production infrastructure.

Recommended conceptual architecture:

```text
                INTERNET
                   X
                   │
                   │ no direct control
                   X
              MININET LAB
                   │
              NetRCA Backend
```

For a student project, Mininet should run in a dedicated Linux/WSL2 environment or controlled host environment.

---

# 39. Production Network Protection

NetRCA MVP must not connect directly to:

- University production networks
- ISP infrastructure
- Corporate networks
- Third-party networks
- Systems without authorization

The project should use:

```text
Mininet
```

as the controlled environment.

---

# 40. Network Scanning Policy

NetRCA should not include unrestricted network scanning.

If network discovery is added later, it must be explicitly scoped to an authorized environment.

The MVP should rely on the known Mininet topology.

---

# 41. Database Backup

Supabase/PostgreSQL data should be backed up according to the deployment environment.

Important data includes:

```text
Incidents
Root Causes
Evidence
Recommendations
AI Analyses
Fault History
```

For an academic MVP, periodic database export can provide an additional backup.

---

# 42. Data Retention

High-volume data includes:

```text
Metrics
Logs
Events
Anomalies
```

Long-term data includes:

```text
Incidents
Root Causes
Evidence
Recommendations
Reports
```

Production deployments should define retention periods.

For the academic MVP, historical data may be retained for evaluation.

---

# 43. Availability and Resilience

NetRCA should continue providing useful functionality when external components fail.

## Gemini unavailable

The system should still show:

```text
Root Cause
Confidence
Evidence
Impact
Timeline
```

Only AI-generated explanation/recommendation may be unavailable.

## Database temporarily unavailable

The API should return a controlled error rather than crashing.

## Mininet unavailable

The dashboard should report:

```text
Network Simulator: OFFLINE
```

instead of exposing internal exceptions.

---

# 44. Graceful Degradation

The architecture should support:

```text
Gemini unavailable
       ↓
Deterministic RCA remains available
```

and:

```text
AI explanation unavailable
       ↓
Evidence-based RCA remains visible
```

This is important because Gemini is an enhancement layer, not the entire system.

---

# 45. Denial-of-Service Protection

Potential abuse targets include:

```text
Fault injection
RCA execution
AI generation
Report generation
Metric queries
Log queries
```

Controls:

- Rate limiting
- Pagination
- Maximum query windows
- Request size limits
- Authentication
- Authorization
- Resource limits
- Timeout handling

---

# 46. Resource Limits

API endpoints should limit:

- Maximum page size
- Maximum time range
- Maximum number of events per RCA request
- Maximum log search results
- Maximum AI context size
- Maximum fault duration

Example:

```text
limit ≤ 100
```

---

# 47. Timeout Strategy

External operations should have timeouts.

Examples:

```text
Gemini request timeout
Database request timeout
Mininet command timeout
HTTP request timeout
```

A timeout should return a controlled error.

---

# 48. Secure File Handling

If incident reports or future uploads are supported:

- Validate file type
- Validate file size
- Avoid executing uploaded files
- Store uploads outside executable directories
- Use randomized filenames
- Scan files where appropriate

The MVP does not require arbitrary file uploads.

---

# 49. Secure Report Generation

Generated reports should not accidentally include:

```text
API keys
Database credentials
Authentication tokens
Internal secrets
```

Reports should contain:

```text
Incident Summary
Root Cause
Evidence
Timeline
Impact
Recommendation
```

---

# 50. Security Testing

## API Testing

Test:

- Unauthorized access
- Invalid tokens
- Invalid UUIDs
- Invalid input
- Excessive requests
- Invalid fault types
- Privileged operations

## Database Testing

Test:

- Constraint enforcement
- Unauthorized access
- RLS policies if enabled
- Invalid foreign keys

## AI Testing

Test:

- Prompt injection
- Malicious log content
- Invalid Gemini output
- Hallucinated recommendations
- Excessive context
- API failure

## Network Testing

Test:

- Fault isolation
- Unauthorized command attempts
- Invalid device IDs
- Invalid fault parameters
- Network reset safety

---

# 51. Threat Model

## Threat: API Credential Theft

**Risk:** Gemini/Supabase credentials are exposed.

**Controls:**

- Environment variables
- Server-side secrets
- No client exposure
- Secret scanning
- Credential rotation

---

## Threat: Command Injection

**Risk:** User sends malicious Mininet/Linux commands.

**Controls:**

- No arbitrary command endpoint
- Allowlisted fault operations
- Parameter validation
- Restricted execution

---

## Threat: Unauthorized Fault Injection

**Risk:** User disrupts the simulation.

**Controls:**

- Authentication
- Authorization
- Rate limiting
- Audit logging
- Explicit fault allowlist

---

## Threat: Prompt Injection

**Risk:** Malicious log/event content attempts to control Gemini.

**Controls:**

- Treat logs as untrusted data
- Structured prompts
- Clear instruction/data separation
- Output validation
- No tool execution by Gemini

---

## Threat: SQL Injection

**Risk:** Malicious input manipulates database queries.

**Controls:**

- Parameterized queries
- Supabase client/query builders
- Input validation
- No string-concatenated SQL

---

## Threat: XSS

**Risk:** Malicious log or incident content executes in the browser.

**Controls:**

- Safe rendering
- Output encoding
- Avoid unsafe HTML injection
- Content validation

---

## Threat: Data Exposure

**Risk:** Internal network information is exposed.

**Controls:**

- Authentication
- Authorization
- HTTPS
- Database access policies
- Restricted reports

---

## Threat: Denial of Service

**Risk:** Expensive endpoints are abused.

**Controls:**

- Rate limiting
- Pagination
- Request limits
- Timeouts
- Authentication

---

# 52. Security Levels by Feature

| Feature | Security Level |
|---|---|
| Dashboard viewing | Medium |
| Metrics viewing | Medium |
| Logs viewing | Medium/High |
| Incident viewing | Medium/High |
| RCA execution | Medium |
| Gemini analysis | Medium |
| Fault injection | **High** |
| Network reset | **High** |
| Device modification | **High** |
| Link modification | **High** |
| User management | **High** |
| Secret management | **Critical** |

---

# 53. Secure API Endpoint Groups

## Public/Low Risk

Potentially public only in controlled deployments:

```text
GET /health
GET /network/status
```

## Authenticated

```text
GET /devices
GET /metrics
GET /logs
GET /events
GET /incidents
GET /analytics
```

## Privileged

```text
POST /network/start
POST /network/stop
POST /network/reset
POST /faults/inject
POST /faults/{id}/recover
POST /devices
PATCH /devices/{id}
PATCH /links/{id}
```

## AI

```text
POST /ai/*
```

should be authenticated and rate-limited.

---

# 54. Security Headers

Production web deployment should consider headers such as:

```text
Content-Security-Policy
Strict-Transport-Security
X-Content-Type-Options
Referrer-Policy
```

Exact configuration depends on the deployment platform.

---

# 55. Secure Development Lifecycle

Development should follow:

```text
PLAN
 ↓
DESIGN
 ↓
IMPLEMENT
 ↓
TEST
 ↓
SECURITY REVIEW
 ↓
DEPLOY
 ↓
MONITOR
 ↓
PATCH
```

Security should not be added only after the project is complete.

---

# 56. Security Checklist — Development

- [ ] `.env` excluded from Git
- [ ] No API keys in source code
- [ ] No arbitrary shell command endpoint
- [ ] Pydantic validation enabled
- [ ] SQL injection protections
- [ ] CORS configured
- [ ] Authentication architecture defined
- [ ] Authorization enforced server-side
- [ ] Fault injection allowlist implemented
- [ ] Gemini key kept server-side
- [ ] AI output treated as untrusted
- [ ] Audit logging implemented
- [ ] Error messages sanitized
- [ ] Dependencies reviewed
- [ ] Unit tests written
- [ ] Security tests written

---

# 57. Security Checklist — Deployment

- [ ] HTTPS enabled
- [ ] Production secrets configured securely
- [ ] Development credentials not reused
- [ ] Database policies enabled
- [ ] CORS restricted
- [ ] Rate limiting enabled
- [ ] Logs protected
- [ ] Backups configured
- [ ] GitHub repository contains no secrets
- [ ] Dependency vulnerabilities reviewed
- [ ] Monitoring enabled
- [ ] Mininet environment isolated
- [ ] No unauthorized network connections

---

# 58. Feature Security Inventory

## Network Features

- Virtual network creation — protected
- Router simulation — controlled
- Switch simulation — controlled
- Server simulation — controlled
- Network topology — access controlled
- Link configuration — privileged
- Bandwidth configuration — privileged
- Latency configuration — privileged
- Packet-loss configuration — privileged
- Traffic generation — controlled
- Network start/stop — privileged
- Network reset — privileged

## Monitoring Features

- Real-time metrics — authenticated
- Historical metrics — authenticated
- Device monitoring — authenticated
- Link monitoring — authenticated
- Availability monitoring — authenticated
- Error monitoring — authenticated
- Interface monitoring — authenticated

## Logging Features

- Log collection — backend-controlled
- Log parsing — backend-controlled
- Log viewing — authenticated
- Log search — authenticated
- Log filtering — authenticated
- Incident association — controlled

## Event Features

- Event generation — backend-controlled
- Event classification — backend-controlled
- Event correlation — authenticated
- Incident grouping — controlled

## Machine Learning Features

- Anomaly detection — backend-controlled
- Model execution — controlled
- Model metadata — protected
- Anomaly results — authenticated
- Evaluation data — protected

## RCA Features

- Candidate cause detection — backend-controlled
- Root-cause identification — backend-controlled
- Confidence estimation — backend-controlled
- Evidence collection — protected
- Timeline analysis — authenticated
- Topology reasoning — authenticated
- Failure-chain reconstruction — authenticated

## AI Features

- Incident explanation — authenticated/rate-limited
- RCA explanation — authenticated/rate-limited
- Failure-chain explanation — authenticated/rate-limited
- Impact summary — authenticated/rate-limited
- Recommendation generation — authenticated/rate-limited
- Incident report generation — authenticated/rate-limited
- Incident Q&A — authenticated/rate-limited

## Fault Injection

- Fault listing — authenticated
- Fault injection — privileged
- Fault recovery — privileged
- Fault reset — privileged
- Fault history — authenticated
- Fault duration — validated
- Fault parameters — validated

## Incident Features

- Incident creation — controlled
- Incident status — controlled
- Incident severity — controlled
- Root cause — protected
- Evidence — protected
- Impact — protected
- Recommendations — protected
- Incident history — authenticated
- Incident export — authenticated

## Dashboard

- Network health — authenticated
- Live metrics — authenticated
- Interactive topology — authenticated
- Active incidents — authenticated
- RCA investigation — authenticated
- Logs — authenticated
- AI explanation — authenticated
- Recommendations — authenticated

---

# 59. Security Architecture for the Core Demo

The project demo should follow this safe sequence:

```text
User
 ↓
Authenticated Dashboard
 ↓
Select "Inject Router Failure"
 ↓
FastAPI validates request
 ↓
Allowlisted fault operation
 ↓
Mininet simulation
 ↓
Network failure
 ↓
Metrics / Logs / Events
 ↓
ML + RCA
 ↓
Evidence-based result
 ↓
Gemini explanation
 ↓
Human-readable recommendation
 ↓
Dashboard
```

There should be no path from:

```text
Gemini → arbitrary shell → real network
```

---

# 60. Security Design Principles

1. **Never trust the frontend.**
2. **Validate every privileged operation on the backend.**
3. **Never expose secrets to the browser.**
4. **Never execute arbitrary user-supplied commands.**
5. **Keep Mininet isolated from real production infrastructure.**
6. **Treat logs as untrusted input.**
7. **Treat Gemini output as advisory and untrusted.**
8. **Separate deterministic RCA from generative AI output.**
9. **Store evidence for important decisions.**
10. **Audit security-sensitive operations.**
11. **Use least privilege.**
12. **Use HTTPS in production.**
13. **Limit expensive API operations.**
14. **Use safe error messages.**
15. **Keep dependencies updated.**
16. **Back up important incident data.**
17. **Require human review before any future remediation action.**
18. **Keep the MVP inside the controlled simulation environment.**

---

# 61. Final Security Architecture

```text
                         USER
                           │
                           ▼
                  ┌─────────────────┐
                  │ Next.js / React │
                  │  Secure UI      │
                  └────────┬────────┘
                           │ HTTPS
                           ▼
                  ┌─────────────────┐
                  │     FastAPI     │
                  │                 │
                  │ Auth            │
                  │ Authorization   │
                  │ Validation      │
                  │ Rate Limiting   │
                  │ Audit Logging   │
                  └───────┬─────────┘
                          │
          ┌───────────────┼────────────────┐
          │               │                │
          ▼               ▼                ▼
      ┌────────┐      ┌─────────┐     ┌──────────┐
      │Mininet │      │RCA / ML │     │ Supabase │
      │Sandbox │      │ Engine  │     │PostgreSQL│
      └────────┘      └────┬────┘     └──────────┘
                            │
                            ▼
                       ┌─────────┐
                       │ Gemini  │
                       │   API   │
                       └─────────┘
```

---

# 62. Final Security Goal

NetRCA should provide powerful network investigation capabilities without turning the AI system into an uncontrolled network operator.

The secure architecture is:

```text
CONTROLLED NETWORK
        ↓
MEASURED DATA
        ↓
VALIDATED BACKEND
        ↓
ML + GRAPH RCA
        ↓
EVIDENCE
        ↓
GEMINI EXPLANATION
        ↓
HUMAN REVIEW
```

The system should remain capable of:

- Detecting network anomalies
- Correlating network events
- Identifying probable root causes
- Explaining failure propagation
- Analyzing impact
- Generating recommendations
- Producing incident reports

while maintaining strict boundaries around:

- Credentials
- Database access
- Mininet control
- AI tool access
- Network commands
- Production infrastructure
- User permissions

This security model is appropriate for the NetRCA academic MVP and provides a foundation for future expansion without compromising the project's controlled simulation boundary.
