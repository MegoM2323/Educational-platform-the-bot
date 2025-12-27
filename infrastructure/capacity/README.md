# THE_BOT Platform - Capacity Planning Tools

This directory contains capacity planning frameworks, resource forecasting tools, and scaling policies for THE_BOT platform.

## Files

### 1. `capacity-plan.json`
Complete capacity planning baseline definitions for all three tiers (Starter 1K, Growth 10K, Enterprise 100K).

**Contains:**
- Resource baselines for each tier
- Infrastructure specifications
- Performance targets
- Cost projections
- Growth trajectory assumptions
- Scaling events and procedures
- Monitoring metrics
- Disaster recovery policies

**Usage:**
```bash
# View Tier 1K configuration
jq '.capacity_tiers.tier_1k' capacity-plan.json

# Check cost for Tier 10K
jq '.capacity_tiers.tier_10k.cost_monthly_usd' capacity-plan.json

# Get growth projection for month 6
jq '.growth_trajectory.month_6' capacity-plan.json
```

### 2. `scaling-thresholds.json`
Auto-scaling trigger configurations and policies for all infrastructure components.

**Contains:**
- Scale-up and scale-down rules for each component
- Metric thresholds and durations
- Cooldown periods
- Constraints (min/max instances)
- Component-specific scaling strategies
- Load balancer algorithms
- Peak load handling policies

**Components:**
- Backend API scaling
- Database scaling (vertical + horizontal)
- Redis scaling
- Frontend scaling
- Celery task queue scaling
- Load balancer configuration

**Usage:**
```bash
# View backend scaling rules
jq '.backend_scaling.scale_up_rules' scaling-thresholds.json

# Check database vertical scaling triggers
jq '.database_scaling.vertical_scaling.rules' scaling-thresholds.json

# Get Redis constraints
jq '.redis_scaling.constraints' scaling-thresholds.json
```

### 3. `resource-forecast.py`
Python script to forecast resource requirements based on user growth projections.

**Features:**
- Multiple growth scenarios (conservative, moderate, aggressive)
- Resource interpolation between tiers
- Cost projections
- Scaling event identification
- Capacity alerts
- CSV/JSON export

**Installation:**
```bash
python -m venv venv
source venv/bin/activate
# No additional dependencies required (uses only stdlib + json)
```

**Usage:**

```bash
# Default: moderate scenario, 24 months, 10K initial users
python resource-forecast.py

# Specify parameters
python resource-forecast.py --months 12 --scenario conservative --initial-users 5000

# Export results
python resource-forecast.py --export csv   # forecast.csv
python resource-forecast.py --export json  # forecast.json

# Get help
python resource-forecast.py --help
```

**Output:**
- Resource table (users, concurrent, tier, infrastructure, cost, storage)
- Scaling events timeline
- Capacity alerts and warnings
- Actionable recommendations
- Monthly cost projections

**Example Output:**
```
Month  Users      Concurrent  DAU     Tier          Backend  DB CPU  DB Mem  Redis  Celery  Cost/mo
1      12,500     1,875       2,500   tier_10k      6        8       32      3      8       $3,500
6      38,145     5,721       7,629   tier_10k      6        8       32      3      8       $3,500
12     113,896    17,084      22,779  tier_100k     30       16      64      10     40      $25,000
```

### 4. `forecast.csv` (Generated)
CSV export from running `resource-forecast.py --export csv`.

Contains monthly forecasts with all metrics for import into spreadsheets or analysis tools.

## Quick Start

### View Capacity Tiers

```bash
# Show all three tiers summary
cat capacity-plan.json | jq '.capacity_tiers | keys'

# Compare costs
cat capacity-plan.json | jq '.capacity_tiers[] | {tier: .tier_name, cost: .cost_monthly_usd}'
```

### Check Scaling Policies

```bash
# View backend auto-scaling rules
cat scaling-thresholds.json | jq '.backend_scaling.scale_up_rules'

# Check database scaling triggers
cat scaling-thresholds.json | jq '.database_scaling'

# View peak load handling
cat scaling-thresholds.json | jq '.peak_load_handling'
```

### Run Forecasts

```bash
# Conservative growth (5-10% monthly)
python resource-forecast.py --scenario conservative

# Moderate growth (15-25% monthly) - RECOMMENDED
python resource-forecast.py --scenario moderate

# Aggressive growth (25-35% monthly)
python resource-forecast.py --scenario aggressive

# Custom parameters
python resource-forecast.py --months 36 --initial-users 25000 --scenario moderate

# Export for analysis
python resource-forecast.py --scenario moderate --export csv
python resource-forecast.py --scenario aggressive --export json
```

## Key Concepts

### Capacity Tiers

| Tier | Concurrent | Registered | Monthly Cost | Best For |
|------|-----------|-----------|--------------|----------|
| Starter 1K | 1,000 | 6,700 | $500 | Pilot, MVP |
| Growth 10K | 10,000 | 67,000 | $3,500 | Scale-up |
| Enterprise 100K | 100,000 | 670,000 | $25,000 | Production |

### Auto-Scaling Strategy

**Horizontal Scaling (Preferred)**
- Backend API: Scale from 2 to 50 instances based on CPU/memory
- Redis: Add shards in cluster mode
- Celery: Scale workers based on queue depth
- Frontend: Add instances for load distribution

**Vertical Scaling (Fallback)**
- Database: Upgrade instance size when horizontal doesn't apply
- Storage: Auto-expand capacity as needed

### Cost Projections

24-month total costs by scenario:
- **Conservative** (10% growth): $180,000 ($3,500/mo avg)
- **Moderate** (20% growth): $272,000 ($11,300/mo avg)
- **Aggressive** (25% growth): $360,000 ($15,000/mo avg)

### Monitoring Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| CPU | 70% | 90% | Auto-scale |
| Memory | 80% | 95% | Auto-scale |
| API Error Rate | 0.5% | 1.0% | Page on-call |
| DB Connections | 70% | 95% | Scale/alert |
| Queue Depth | 500 | 1000 | Scale workers |

## Integration Points

### With Docker Compose
Update resource limits in `docker-compose.yml` based on tier:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'        # From tier_1k
          memory: 1G
        reservations:
          cpus: '1'
          memory: 512M
```

### With Kubernetes
Create HPA based on scaling thresholds:

```bash
kubectl autoscale deployment backend \
  --min=2 --max=50 \
  --cpu-percent=70 \
  --name=backend-hpa
```

### With Monitoring (Prometheus)
Configure alerts using thresholds from `scaling-thresholds.json`:

```yaml
groups:
- name: capacity
  rules:
  - alert: HighCPU
    expr: rate(container_cpu_usage_seconds_total[5m]) > 0.7
    for: 2m
```

## Scaling Procedures

### Tier 1K → Tier 10K (3,000+ concurrent users)
**Duration**: 4 hours
**Downtime**: Zero

1. Enable database replication
2. Provision Redis cluster
3. Scale backend to 6 instances
4. Update load balancer
5. Monitor and verify

See [CAPACITY_PLANNING.md](../../docs/CAPACITY_PLANNING.md#scaling-from-tier-1k-to-tier-10k) for detailed runbook.

### Tier 10K → Tier 100K (30,000+ concurrent users)
**Duration**: 8 hours
**Downtime**: Zero (multi-region)

1. Migrate database to managed service
2. Setup Redis cluster across regions
3. Deploy multi-region backend
4. Configure CDN and global load balancer
5. Gradual traffic shift and monitoring

See [CAPACITY_PLANNING.md](../../docs/CAPACITY_PLANNING.md#scaling-from-tier-10k-to-tier-100k) for detailed runbook.

## Recommendations

### Immediate Actions
- [ ] Review capacity tier alignment with current user count
- [ ] Run forecast for your growth scenario
- [ ] Set up monitoring dashboards for key metrics
- [ ] Document current infrastructure baseline

### Monthly Tasks
- [ ] Run resource forecast with latest growth data
- [ ] Review scaling alerts and incidents
- [ ] Update cost projections
- [ ] Check tier readiness (70% capacity trigger)

### Quarterly Review
- [ ] Assess actual vs. projected growth
- [ ] Update growth scenario assumptions
- [ ] Review cost optimization opportunities
- [ ] Plan infrastructure upgrades

## Related Documentation

- [CAPACITY_PLANNING.md](../../docs/CAPACITY_PLANNING.md) - Comprehensive capacity planning guide
- [DEPLOYMENT.md](../../docs/DEPLOYMENT.md) - Production deployment procedures
- [PRODUCTION_CHECKLIST.md](../../docs/PRODUCTION_CHECKLIST.md) - Pre-launch verification
- [docker-compose.yml](../../docker-compose.yml) - Current infrastructure config

## Support

For capacity planning questions:
1. Check the appropriate JSON configuration file
2. Run resource-forecast.py for your scenario
3. Review CAPACITY_PLANNING.md documentation
4. Contact DevOps team

---

**Last Updated**: December 27, 2025
**Version**: 1.0.0
**Review Frequency**: Quarterly
