# Incident Response Runbook

**Last Updated**: December 27, 2025
**Version**: 1.0.0
**Maintainer**: DevOps Team

## Quick Links

- [Severity Levels & Response Times](#severity-levels)
- [Escalation Matrix](#escalation-matrix)
- [On-Call Rotation](#on-call-rotation)
- [Response Procedures](#response-procedures)
- [Communication Templates](#communication-templates)
- [Troubleshooting Guides](#troubleshooting-guides)
- [Diagnostic Collection](#diagnostic-collection)
- [Postmortem Process](#postmortem-process)

---

## Severity Levels

### P1 - Critical (0-15 minutes)

**Impact**: Production system completely down, all users affected

**Response Time**: Immediate (< 5 minutes)

**Examples**:
- Database completely unavailable
- API service down (0% uptime)
- Authentication broken (users cannot log in)
- Website not accessible
- All WebSocket connections failing
- Payment processing completely broken
- Data corruption detected
- Security breach confirmed

**Actions**:
1. Declare SEV-1 incident
2. Page on-call engineer immediately
3. Open war room conference call
4. Begin triage and diagnosis (< 5 min)
5. Post status page update (every 5 min)
6. Escalate to engineering manager if not resolved in 15 min

**Escalation Trigger**: No status update in 5 minutes

### P2 - High (15 minutes - 1 hour)

**Impact**: Significant portion of functionality degraded, multiple features unavailable

**Response Time**: Urgent (< 15 minutes)

### P3 - Medium (1-4 hours)

**Impact**: Minor feature degradation, workaround available, non-critical functionality affected

**Response Time**: High (< 30 minutes)

### P4 - Low (> 4 hours)

**Impact**: Cosmetic issues, no functional impact, workaround obvious

**Response Time**: Within business hours (< 24 hours)

---

## Escalation Matrix

See escalation procedures and contact information in full runbook.

---

## Troubleshooting Guides

- [API Troubleshooting](troubleshooting/api.md)
- [Database Troubleshooting](troubleshooting/database.md)
- [WebSocket Troubleshooting](troubleshooting/websocket.md)

---

## Diagnostic Collection

Run diagnostics collection script:

\`\`\`bash
bash scripts/incident/collect-diagnostics.sh
\`\`\`

This collects system metrics, logs, and application state for analysis.

---

For complete procedures, templates, and detailed guides, see related files in this directory.
