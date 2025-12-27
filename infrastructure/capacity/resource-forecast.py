#!/usr/bin/env python3
"""
THE_BOT Platform - Resource Forecasting Tool

This script predicts resource requirements based on user growth projections
and generates capacity planning recommendations.

Usage:
    python resource-forecast.py [--months 24] [--growth-rate 0.20]
    python resource-forecast.py --scenario startup
    python resource-forecast.py --export csv
"""

import json
import sys
import argparse
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import math


class Tier(Enum):
    """Capacity tier classifications."""
    STARTER_1K = "tier_1k"
    GROWTH_10K = "tier_10k"
    ENTERPRISE_100K = "tier_100k"


@dataclass
class ResourcesSnapshot:
    """Resource snapshot at a point in time."""
    month: int
    registered_users: int
    concurrent_peak: int
    daily_active: int
    monthly_api_requests: int
    monthly_messages: int
    tier: Tier
    backend_instances: int
    db_cpu: int
    db_memory_gb: int
    redis_nodes: int
    celery_workers: int
    estimated_cost_usd: float
    storage_gb: int


class GrowthScenario(Enum):
    """Pre-defined growth scenarios."""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class ResourceForecaster:
    """Forecast resource requirements based on user growth."""

    def __init__(self, capacity_plan_path: str = "capacity-plan.json"):
        """Initialize forecaster with capacity plan."""
        with open(capacity_plan_path, 'r') as f:
            self.capacity_plan = json.load(f)
        self.assumptions = self.capacity_plan["assumptions"]
        self.tiers = self.capacity_plan["capacity_tiers"]

    def get_growth_scenario_rates(self, scenario: GrowthScenario) -> Dict[str, float]:
        """Get monthly growth rates for a scenario."""
        base_rates = {
            "month_1_6": 0.25,
            "month_7_12": 0.20,
            "month_13_24": 0.15
        }

        if scenario == GrowthScenario.CONSERVATIVE:
            return {
                "month_1_6": 0.10,
                "month_7_12": 0.08,
                "month_13_24": 0.05
            }
        elif scenario == GrowthScenario.AGGRESSIVE:
            return {
                "month_1_6": 0.35,
                "month_7_12": 0.30,
                "month_13_24": 0.25
            }
        else:  # MODERATE
            return base_rates

    def estimate_concurrent_users(self, registered_users: int) -> int:
        """Estimate concurrent users from registered count."""
        concurrent_ratio = self.assumptions["concurrent_user_ratio"]
        return int(registered_users * concurrent_ratio)

    def estimate_daily_active(self, registered_users: int) -> int:
        """Estimate daily active users."""
        # Typically 20-30% of registered users
        return int(registered_users * 0.20)

    def estimate_api_requests(self, concurrent_users: int, days: int = 30) -> int:
        """Estimate monthly API requests."""
        rate_per_minute = self.assumptions["api_requests_per_user_per_minute"]
        session_duration = self.assumptions["session_duration_minutes"]
        peak_hours_daily = 4

        # Calculate for peak period + off-peak
        peak_requests = concurrent_users * rate_per_minute * session_duration * peak_hours_daily * days
        offpeak_requests = concurrent_users * 0.2 * rate_per_minute * session_duration * 20 * days

        return int(peak_requests + offpeak_requests)

    def estimate_messages(self, concurrent_users: int, days: int = 30) -> int:
        """Estimate monthly messages."""
        rate_per_minute = self.assumptions["message_rate_per_user_per_minute"]
        session_duration = self.assumptions["session_duration_minutes"]
        peak_hours_daily = 4

        peak_messages = concurrent_users * rate_per_minute * session_duration * peak_hours_daily * days
        offpeak_messages = concurrent_users * 0.1 * rate_per_minute * session_duration * 20 * days

        return int(peak_messages + offpeak_messages)

    def estimate_storage(self, registered_users: int, months: int = 1) -> int:
        """Estimate database storage growth."""
        rows_per_user = self.assumptions["database_row_growth_per_user"]
        # Average row size ~1KB
        bytes_per_user = rows_per_user * 1024 * months
        total_bytes = registered_users * bytes_per_user
        return int(total_bytes / (1024**3)) + 50  # Convert to GB, add buffer

    def get_tier_for_concurrent_users(self, concurrent_users: int) -> Tier:
        """Determine appropriate tier based on concurrent users."""
        if concurrent_users <= 1500:
            return Tier.STARTER_1K
        elif concurrent_users <= 15000:
            return Tier.GROWTH_10K
        else:
            return Tier.ENTERPRISE_100K

    def get_database_cpu(self, tier_data: Dict) -> int:
        """Extract database CPU from tier data (handles both formats)."""
        db = tier_data["infrastructure"]["database"]
        if "cpu" in db:
            return db["cpu"]
        elif "primary_cpu" in db:
            return db["primary_cpu"]
        else:
            return 4  # Default

    def get_database_memory(self, tier_data: Dict) -> int:
        """Extract database memory from tier data (handles both formats)."""
        db = tier_data["infrastructure"]["database"]
        if "memory_gb" in db:
            return db["memory_gb"]
        elif "primary_memory_gb" in db:
            return db["primary_memory_gb"]
        else:
            return 16  # Default

    def interpolate_tier_resources(
        self,
        concurrent_users: int,
        lower_tier: Tier,
        upper_tier: Tier
    ) -> Dict:
        """Interpolate resources between two tiers."""
        lower = self.tiers[lower_tier.value]
        upper = self.tiers[upper_tier.value]

        lower_concurrent = lower["concurrent_peak"]
        upper_concurrent = upper["concurrent_peak"]

        # Linear interpolation
        ratio = (concurrent_users - lower_concurrent) / (upper_concurrent - lower_concurrent)
        ratio = max(0, min(1, ratio))  # Clamp to 0-1

        def interpolate_value(lower_val, upper_val):
            return lower_val + (upper_val - lower_val) * ratio

        lower_backend = lower["infrastructure"]["backend"]["instances"]
        upper_backend = upper["infrastructure"]["backend"]["instances"]

        lower_db_cpu = self.get_database_cpu(lower)
        upper_db_cpu = self.get_database_cpu(upper)

        lower_db_mem = self.get_database_memory(lower)
        upper_db_mem = self.get_database_memory(upper)

        lower_redis = lower["infrastructure"]["redis"]["nodes"]
        upper_redis = upper["infrastructure"]["redis"]["nodes"]

        lower_celery = lower["infrastructure"]["celery"]["workers"]
        upper_celery = upper["infrastructure"]["celery"]["workers"]

        return {
            "backend_instances": int(interpolate_value(lower_backend, upper_backend)),
            "db_cpu": int(interpolate_value(lower_db_cpu, upper_db_cpu)),
            "db_memory_gb": int(interpolate_value(lower_db_mem, upper_db_mem)),
            "redis_nodes": int(interpolate_value(lower_redis, upper_redis)),
            "celery_workers": int(interpolate_value(lower_celery, upper_celery))
        }

    def estimate_cost(self, tier: Tier) -> float:
        """Estimate monthly cost for tier."""
        return self.tiers[tier.value]["cost_monthly_usd"]

    def forecast(
        self,
        initial_users: int = 10000,
        months: int = 24,
        growth_rates: Dict[str, float] = None,
        scenario: GrowthScenario = None
    ) -> List[ResourcesSnapshot]:
        """Generate resource forecast for specified period."""

        if scenario:
            growth_rates = self.get_growth_scenario_rates(scenario)
        elif not growth_rates:
            growth_rates = self.get_growth_scenario_rates(GrowthScenario.MODERATE)

        forecasts: List[ResourcesSnapshot] = []
        current_users = initial_users

        for month in range(1, months + 1):
            # Calculate monthly growth rate
            if month <= 6:
                monthly_growth = growth_rates["month_1_6"]
            elif month <= 12:
                monthly_growth = growth_rates["month_7_12"]
            else:
                monthly_growth = growth_rates["month_13_24"]

            # Apply monthly growth
            current_users = int(current_users * (1 + monthly_growth))

            # Estimate metrics
            concurrent = self.estimate_concurrent_users(current_users)
            daily_active = self.estimate_daily_active(current_users)
            api_requests = self.estimate_api_requests(concurrent)
            messages = self.estimate_messages(concurrent)
            storage = self.estimate_storage(current_users, month)

            # Determine tier
            tier = self.get_tier_for_concurrent_users(concurrent)

            # Get resources based on tier
            tier_data = self.tiers[tier.value]

            # Check if we're between tiers
            if tier == Tier.STARTER_1K and concurrent > 1500:
                tier = Tier.GROWTH_10K

            tier_data = self.tiers[tier.value]
            backend_instances = tier_data["infrastructure"]["backend"]["instances"]
            db_cpu = self.get_database_cpu(tier_data)
            db_memory = self.get_database_memory(tier_data)
            redis_nodes = tier_data["infrastructure"]["redis"]["nodes"]
            celery_workers = tier_data["infrastructure"]["celery"]["workers"]
            cost = self.estimate_cost(tier)

            forecast = ResourcesSnapshot(
                month=month,
                registered_users=current_users,
                concurrent_peak=concurrent,
                daily_active=daily_active,
                monthly_api_requests=api_requests,
                monthly_messages=messages,
                tier=tier,
                backend_instances=backend_instances,
                db_cpu=db_cpu,
                db_memory_gb=db_memory,
                redis_nodes=redis_nodes,
                celery_workers=celery_workers,
                estimated_cost_usd=cost,
                storage_gb=storage
            )

            forecasts.append(forecast)

        return forecasts

    def print_forecast_table(self, forecasts: List[ResourcesSnapshot]):
        """Print forecast as formatted table."""
        print("\n" + "="*150)
        print(f"{'Month':<6} {'Users':<10} {'Concurrent':<12} {'DAU':<8} {'Tier':<15} {'Backend':<8} "
              f"{'DB CPU':<7} {'DB Mem':<8} {'Redis':<6} {'Celery':<7} {'Cost/mo':<10} {'Storage':<10}")
        print("="*150)

        for f in forecasts:
            print(f"{f.month:<6} {f.registered_users:<10,} {f.concurrent_peak:<12,} "
                  f"{f.daily_active:<8,} {f.tier.value:<15} {f.backend_instances:<8} "
                  f"{f.db_cpu:<7} {f.db_memory_gb:<8} {f.redis_nodes:<6} {f.celery_workers:<7} "
                  f"${f.estimated_cost_usd:<9,.0f} {f.storage_gb:<10}")

        print("="*150 + "\n")

    def print_scaling_events(self, forecasts: List[ResourcesSnapshot]):
        """Print identified scaling events."""
        print("\nSCALING EVENTS:")
        print("-" * 80)

        prev_tier = None
        prev_backend = None

        for f in forecasts:
            if f.tier != prev_tier:
                print(f"Month {f.month}: Tier Migration to {f.tier.value}")
                print(f"  • Registered Users: {f.registered_users:,}")
                print(f"  • Concurrent Users: {f.concurrent_peak:,}")
                print(f"  • Infrastructure: {f.backend_instances} backend, {f.db_cpu} CPU, "
                      f"{f.redis_nodes} redis nodes")
                prev_tier = f.tier

            if f.backend_instances != prev_backend:
                change = f.backend_instances - (prev_backend or 2)
                action = "scale up" if change > 0 else "scale down"
                print(f"Month {f.month}: Backend {action} to {f.backend_instances} instances")
                prev_backend = f.backend_instances

        print()

    def generate_capacity_alerts(self, forecasts: List[ResourcesSnapshot]):
        """Generate capacity planning alerts."""
        print("\nCAPACITY PLANNING ALERTS:")
        print("-" * 80)

        total_cost_24m = sum(f.estimated_cost_usd for f in forecasts)
        max_storage = max(f.storage_gb for f in forecasts)
        max_concurrent = max(f.concurrent_peak for f in forecasts)

        print(f"• 24-Month Total Cost: ${total_cost_24m:,.0f}")
        print(f"• Peak Concurrent Users: {max_concurrent:,}")
        print(f"• Max Storage Required: {max_storage:,} GB")

        # Check for rapid growth
        growth_rates = []
        for i in range(1, len(forecasts)):
            prev_users = forecasts[i-1].registered_users
            curr_users = forecasts[i].registered_users
            growth_rate = (curr_users - prev_users) / prev_users
            growth_rates.append(growth_rate)

        avg_growth = sum(growth_rates) / len(growth_rates) if growth_rates else 0
        max_growth = max(growth_rates) if growth_rates else 0

        print(f"• Average Monthly Growth: {avg_growth*100:.1f}%")
        print(f"• Peak Monthly Growth: {max_growth*100:.1f}%")

        # Identify critical months
        print("\n• Critical Planning Months:")
        for f in forecasts:
            if f.concurrent_peak > 10000 and forecasts.index(f) < 12:
                print(f"  - Month {f.month}: Rapid growth to {f.concurrent_peak:,} concurrent users")

        print()

    def export_csv(self, forecasts: List[ResourcesSnapshot], filename: str = "forecast.csv"):
        """Export forecast to CSV."""
        import csv

        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "Month", "Registered Users", "Concurrent Peak", "Daily Active",
                "API Requests/Month", "Messages/Month", "Tier", "Backend Instances",
                "DB CPU", "DB Memory (GB)", "Redis Nodes", "Celery Workers",
                "Monthly Cost (USD)", "Storage (GB)"
            ])

            for forecast in forecasts:
                writer.writerow([
                    forecast.month,
                    forecast.registered_users,
                    forecast.concurrent_peak,
                    forecast.daily_active,
                    forecast.monthly_api_requests,
                    forecast.monthly_messages,
                    forecast.tier.value,
                    forecast.backend_instances,
                    forecast.db_cpu,
                    forecast.db_memory_gb,
                    forecast.redis_nodes,
                    forecast.celery_workers,
                    f"{forecast.estimated_cost_usd:.2f}",
                    forecast.storage_gb
                ])

        print(f"Forecast exported to {filename}")

    def generate_recommendations(self, forecasts: List[ResourcesSnapshot]):
        """Generate actionable recommendations."""
        print("\nRECOMMENDATIONS:")
        print("-" * 80)

        final_forecast = forecasts[-1]

        print("\n1. INFRASTRUCTURE:")
        print(f"   • Plan for {final_forecast.backend_instances} backend instances by month 24")
        print(f"   • Database should support {final_forecast.db_cpu} CPUs and {final_forecast.db_memory_gb}GB RAM")
        print(f"   • Redis cluster with {final_forecast.redis_nodes} nodes for caching")
        print(f"   • {final_forecast.celery_workers} Celery workers for async tasks")

        print("\n2. MONITORING:")
        print("   • Implement real-time capacity monitoring dashboards")
        print("   • Set up alerts for CPU >70%, Memory >80%, Storage >80%")
        print("   • Track concurrent user trends weekly")

        print("\n3. DATABASE:")
        print("   • Enable PostgreSQL connection pooling (pgBouncer)")
        print("   • Set up read replicas at tier_10k migration")
        print("   • Implement regular backup strategy (hourly snapshots)")

        print("\n4. CACHING:")
        print("   • Deploy Redis Cluster mode at tier_10k (3+ nodes)")
        print("   • Set eviction policy to allkeys-lru")
        print("   • Monitor cache hit ratio (target: >85%)")

        print("\n5. COST OPTIMIZATION:")
        total_cost = sum(f.estimated_cost_usd for f in forecasts)
        avg_cost = total_cost / len(forecasts)
        print(f"   • 24-month projection: ${total_cost:,.0f}")
        print(f"   • Average monthly: ${avg_cost:,.0f}")
        print("   • Consider reserved instances for 50-60% savings")
        print("   • Use spot instances for non-critical workloads")

        print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="THE_BOT Platform Resource Forecasting Tool"
    )
    parser.add_argument(
        "--months", type=int, default=24,
        help="Forecast period in months (default: 24)"
    )
    parser.add_argument(
        "--initial-users", type=int, default=10000,
        help="Initial registered users (default: 10000)"
    )
    parser.add_argument(
        "--scenario", choices=["conservative", "moderate", "aggressive"],
        default="moderate",
        help="Growth scenario (default: moderate)"
    )
    parser.add_argument(
        "--export", choices=["csv", "json"],
        help="Export forecast to file format"
    )
    parser.add_argument(
        "--capacity-plan", default="capacity-plan.json",
        help="Path to capacity plan JSON file"
    )

    args = parser.parse_args()

    try:
        forecaster = ResourceForecaster(args.capacity_plan)
        scenario = GrowthScenario(args.scenario)

        print("\n" + "="*80)
        print(f"THE_BOT PLATFORM - RESOURCE FORECASTING REPORT")
        print(f"Scenario: {scenario.value.upper()} | Period: {args.months} months")
        print(f"Initial Users: {args.initial_users:,}")
        print("="*80)

        forecasts = forecaster.forecast(
            initial_users=args.initial_users,
            months=args.months,
            scenario=scenario
        )

        forecaster.print_forecast_table(forecasts)
        forecaster.print_scaling_events(forecasts)
        forecaster.generate_capacity_alerts(forecasts)
        forecaster.generate_recommendations(forecasts)

        if args.export == "csv":
            forecaster.export_csv(forecasts)
        elif args.export == "json":
            json_data = {
                "metadata": {
                    "scenario": scenario.value,
                    "initial_users": args.initial_users,
                    "months": args.months,
                    "generated": datetime.now().isoformat()
                },
                "forecasts": [
                    {
                        "month": f.month,
                        "registered_users": f.registered_users,
                        "concurrent_peak": f.concurrent_peak,
                        "daily_active": f.daily_active,
                        "monthly_api_requests": f.monthly_api_requests,
                        "monthly_messages": f.monthly_messages,
                        "tier": f.tier.value,
                        "backend_instances": f.backend_instances,
                        "db_cpu": f.db_cpu,
                        "db_memory_gb": f.db_memory_gb,
                        "redis_nodes": f.redis_nodes,
                        "celery_workers": f.celery_workers,
                        "estimated_cost_usd": f.estimated_cost_usd,
                        "storage_gb": f.storage_gb
                    }
                    for f in forecasts
                ]
            }

            with open("forecast.json", "w") as f:
                json.dump(json_data, f, indent=2)

            print(f"Forecast exported to forecast.json")

        return 0

    except FileNotFoundError:
        print(f"Error: Could not find capacity plan file: {args.capacity_plan}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
