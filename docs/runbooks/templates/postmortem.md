# Postmortem Template

Use this template to document learning from incidents.

---

## Postmortem Information

**Incident Title**: [Clear, concise title]
**Date**: [YYYY-MM-DD]
**Time Range**: [HH:MM UTC] to [HH:MM UTC] (Duration: [XX minutes])
**Severity**: [P1 / P2 / P3]
**Author(s)**: [List of people who were in war room]

**Status**: [ ] Draft [ ] In Review [ ] Approved [ ] Archived

---

## 1. Incident Summary

### What happened?

One-paragraph executive summary suitable for non-technical stakeholders.

### Impact

**Scope**:
- [ ] Total outage
- [ ] Significant degradation (> 25% of users)
- [ ] Moderate degradation (5-25% of users)
- [ ] Minor degradation (< 5% of users)

**Quantification**:
- Affected Users: [X users] or [X% of user base]
- Affected Features: [List]
- Mean Time to Resolution (MTTR): [XX minutes]
- Mean Time to Detection (MTTD): [XX minutes]

### Timeline

| Timestamp (UTC) | Event | Actor |
|-----------------|-------|-------|
| HH:MM:SS | [What happened] | [Who/What] |

---

## 2. Root Cause Analysis

### Root Cause

State the root cause clearly and specifically.

### Five Whys

1. **Why did the API become slow?**
   - Answer: [Root cause level 1]

2. **Why did [root cause 1] happen?**
   - Answer: [Root cause level 2]

...continue asking why until reaching systemic issue

### Contributing Factors

What conditions made this worse?

---

## 3. Incident Response Quality

### What Went Well

Things we did right.

- [x] Alert fired quickly
- [x] On-call engineer responded fast
- [x] War room productive

### What Didn't Go Well

Things that slowed response.

- [ ] Alert threshold too high
- [ ] Rollback took time
- [ ] Status page delayed

---

## 4. Lessons Learned

### What We Now Understand

Clear statements of what we learned.

**Before**: [Old understanding]
**After**: [New understanding]

---

## 5. Action Items

All action items must be specific, assigned, and tracked.

### Immediate (This week)

- [ ] [Action] (Owner: [Name], Due: [Date], GitHub: [Link])

### Short-term (This month)

- [ ] [Action] (Owner: [Name], Due: [Date], GitHub: [Link])

### Long-term (This quarter)

- [ ] [Action] (Owner: [Name], Due: [Date], GitHub: [Link])

---

## Sign-Off

**Postmortem Facilitator**: [Name] - [Date]
**Engineering Manager**: [Name] - [Date]
**VP Engineering** (P1 only): [Name] - [Date]

---

**Created**: [Auto-filled]
**Last Modified**: [Auto-filled]
**Version**: 1.0
**Status**: [DRAFT / APPROVED]
