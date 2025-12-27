#!/usr/bin/env python3
"""
Cost Monitoring and Analysis Report Generator

Analyzes cloud infrastructure costs, identifies optimization opportunities,
and generates comprehensive cost reports with recommendations.

Features:
- Monthly cost breakdown by service, project, environment, and owner
- Cost trend analysis and anomaly detection
- Resource rightsizing recommendations
- Unused resource identification
- Budget vs actual spending analysis
- Spot/preemptible instance optimization opportunities
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, asdict, field
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CostTrend(Enum):
    """Cost trend classification."""
    STABLE = "stable"
    INCREASING = "increasing"
    DECREASING = "decreasing"
    ANOMALY = "anomaly"


class ResourceType(Enum):
    """Cloud resource types."""
    COMPUTE = "compute"
    STORAGE = "storage"
    DATABASE = "database"
    NETWORK = "network"
    CACHE = "cache"
    QUEUE = "queue"
    MONITORING = "monitoring"


@dataclass
class ResourceTag:
    """Resource tagging information."""
    project: str
    environment: str  # dev, staging, production
    owner: str
    cost_center: str
    application: str = ""
    team: str = ""
    backup_policy: str = ""
    compliance_level: str = ""


@dataclass
class CostData:
    """Monthly cost data point."""
    month: str
    service: str
    resource_type: ResourceType
    cost: float
    quantity: int = 0
    unit_cost: float = 0.0
    tags: ResourceTag = field(default_factory=lambda: ResourceTag(
        project="unknown",
        environment="unknown",
        owner="unknown",
        cost_center="unknown"
    ))


@dataclass
class CostAnomalyAlert:
    """Cost anomaly detection alert."""
    resource_id: str
    service: str
    expected_cost: float
    actual_cost: float
    deviation_percent: float
    severity: str  # warning, critical
    message: str


@dataclass
class RightsizingRecommendation:
    """Resource rightsizing recommendation."""
    resource_id: str
    resource_type: ResourceType
    current_size: str
    recommended_size: str
    current_cost: float
    estimated_savings: float
    confidence_percent: float
    reason: str


@dataclass
class OptimizationOpportunity:
    """Cost optimization opportunity."""
    opportunity_type: str  # unused, oversized, underutilized, wrong-service
    resource_id: str
    service: str
    current_cost: float
    potential_savings: float
    priority: str  # low, medium, high
    actions: List[str] = field(default_factory=list)


class CostAnalyzer:
    """Analyzes cloud infrastructure costs and generates recommendations."""

    def __init__(self, data_file: Optional[str] = None, months_history: int = 12):
        """Initialize cost analyzer.

        Args:
            data_file: JSON file with cost data
            months_history: Number of months of historical data to analyze
        """
        self.data_file = data_file or "cost_data.json"
        self.months_history = months_history
        self.cost_data: List[CostData] = []
        self.anomalies: List[CostAnymalyAlert] = []
        self.recommendations: List[RightsizingRecommendation] = []
        self.opportunities: List[OptimizationOpportunity] = []

    def load_cost_data(self) -> bool:
        """Load cost data from file.

        Returns:
            True if data loaded successfully, False otherwise
        """
        if not Path(self.data_file).exists():
            logger.warning(f"Cost data file not found: {self.data_file}")
            logger.info("Generating synthetic cost data for demonstration...")
            self._generate_sample_data()
            return True

        try:
            with open(self.data_file, 'r') as f:
                data_dict = json.load(f)
                for item in data_dict.get('costs', []):
                    self.cost_data.append(self._parse_cost_item(item))
            logger.info(f"Loaded {len(self.cost_data)} cost records")
            return True
        except Exception as e:
            logger.error(f"Failed to load cost data: {e}")
            return False

    def _parse_cost_item(self, item: Dict[str, Any]) -> CostData:
        """Parse cost data item.

        Args:
            item: Dictionary with cost data

        Returns:
            CostData object
        """
        tags = item.get('tags', {})
        return CostData(
            month=item.get('month'),
            service=item.get('service'),
            resource_type=ResourceType(item.get('resource_type', 'compute')),
            cost=item.get('cost', 0),
            quantity=item.get('quantity', 1),
            unit_cost=item.get('unit_cost', 0),
            tags=ResourceTag(
                project=tags.get('project', 'unknown'),
                environment=tags.get('environment', 'unknown'),
                owner=tags.get('owner', 'unknown'),
                cost_center=tags.get('cost_center', 'unknown'),
                application=tags.get('application', ''),
                team=tags.get('team', '')
            )
        )

    def _generate_sample_data(self) -> None:
        """Generate sample cost data for demonstration."""
        services = {
            'EC2': {'type': ResourceType.COMPUTE, 'base_cost': 500},
            'RDS': {'type': ResourceType.DATABASE, 'base_cost': 300},
            'S3': {'type': ResourceType.STORAGE, 'base_cost': 150},
            'CloudFront': {'type': ResourceType.NETWORK, 'base_cost': 200},
            'ElastiCache': {'type': ResourceType.CACHE, 'base_cost': 100},
            'SQS': {'type': ResourceType.QUEUE, 'base_cost': 50},
            'CloudWatch': {'type': ResourceType.MONITORING, 'base_cost': 75},
        }

        environments = ['dev', 'staging', 'production']
        projects = ['thebot-platform', 'infrastructure', 'analytics']
        owners = ['devops-team', 'platform-team', 'infrastructure-team']
        cost_centers = ['engineering', 'operations', 'infrastructure']

        # Generate 12 months of data
        now = datetime.now()
        for month_offset in range(self.months_history):
            month_date = now - timedelta(days=30 * month_offset)
            month_str = month_date.strftime('%Y-%m')

            for service, service_info in services.items():
                # Base cost with slight monthly variation
                cost_variation = 0.9 + (month_offset % 3) * 0.05
                base_cost = service_info['base_cost'] * cost_variation

                for env in environments:
                    # Production costs more than dev/staging
                    env_multiplier = {'production': 3, 'staging': 1.5, 'dev': 0.5}.get(env, 1)
                    cost = base_cost * env_multiplier

                    self.cost_data.append(CostData(
                        month=month_str,
                        service=service,
                        resource_type=service_info['type'],
                        cost=cost,
                        quantity=1,
                        unit_cost=cost,
                        tags=ResourceTag(
                            project=projects[hash(service) % len(projects)],
                            environment=env,
                            owner=owners[hash(service + env) % len(owners)],
                            cost_center=cost_centers[hash(env) % len(cost_centers)],
                            application=service.lower(),
                            team=owners[hash(service + env) % len(owners)].replace('-team', '')
                        )
                    ))

    def analyze_cost_trends(self) -> Dict[str, Dict[str, Any]]:
        """Analyze cost trends over time.

        Returns:
            Dictionary with trend analysis per service
        """
        trends = {}

        # Group costs by service and month
        service_costs: Dict[str, Dict[str, float]] = {}
        for item in self.cost_data:
            if item.service not in service_costs:
                service_costs[item.service] = {}
            month_key = item.month
            service_costs[item.service][month_key] = \
                service_costs[item.service].get(month_key, 0) + item.cost

        # Analyze trends
        for service, monthly_costs in service_costs.items():
            months = sorted(monthly_costs.keys())
            costs = [monthly_costs[m] for m in months]

            if len(costs) >= 2:
                current_cost = costs[-1]
                previous_cost = costs[-2]
                avg_cost = sum(costs) / len(costs)

                # Determine trend
                trend = CostTrend.STABLE
                change_percent = ((current_cost - previous_cost) / previous_cost * 100) if previous_cost > 0 else 0

                if abs(change_percent) > 20:
                    if change_percent > 0:
                        trend = CostTrend.INCREASING
                    else:
                        trend = CostTrend.DECREASING

                # Detect anomalies (deviation > 30% from average)
                if current_cost > avg_cost * 1.3 or current_cost < avg_cost * 0.7:
                    trend = CostTrend.ANOMALY

                trends[service] = {
                    'current_cost': current_cost,
                    'previous_cost': previous_cost,
                    'average_cost': avg_cost,
                    'change_percent': change_percent,
                    'trend': trend.value,
                    'month_count': len(costs),
                    'cost_history': dict(zip(months, costs))
                }

        return trends

    def detect_cost_anomalies(self, threshold_percent: float = 30) -> List[CostAnomalyAlert]:
        """Detect cost anomalies.

        Args:
            threshold_percent: Deviation threshold for anomaly detection

        Returns:
            List of detected anomalies
        """
        anomalies = []
        trends = self.analyze_cost_trends()

        for service, trend_data in trends.items():
            current_cost = trend_data['current_cost']
            avg_cost = trend_data['average_cost']

            if current_cost == 0:
                continue

            deviation = abs(current_cost - avg_cost) / avg_cost * 100

            if deviation > threshold_percent:
                severity = "critical" if deviation > 50 else "warning"
                anomalies.append(CostAnomalyAlert(
                    resource_id=f"{service}-{datetime.now().strftime('%Y-%m')}",
                    service=service,
                    expected_cost=avg_cost,
                    actual_cost=current_cost,
                    deviation_percent=deviation,
                    severity=severity,
                    message=f"{service} cost deviation: {deviation:.1f}% "
                            f"(expected ${avg_cost:.2f}, actual ${current_cost:.2f})"
                ))

        self.anomalies = anomalies
        return anomalies

    def identify_rightsize_opportunities(self) -> List[RightsizingRecommendation]:
        """Identify resource rightsizing opportunities.

        Returns:
            List of rightsizing recommendations
        """
        recommendations = []

        # Analyze by resource type and environment
        resource_analysis: Dict[str, Dict[str, List[float]]] = {}
        for item in self.cost_data:
            key = f"{item.service}-{item.tags.environment}"
            if key not in resource_analysis:
                resource_analysis[key] = {'costs': []}
            resource_analysis[key]['costs'].append(item.cost)

        # Generate recommendations based on utilization patterns
        for resource_key, data in resource_analysis.items():
            service, env = resource_key.split('-')
            avg_cost = sum(data['costs']) / len(data['costs']) if data['costs'] else 0

            # High variability suggests oversizing
            if len(data['costs']) >= 2:
                max_cost = max(data['costs'])
                min_cost = min(data['costs'])
                variability = (max_cost - min_cost) / avg_cost * 100 if avg_cost > 0 else 0

                if variability > 50:
                    # Suggest downsizing
                    current_size = self._get_size_class(service, avg_cost)
                    recommended_size = self._get_recommended_size(service, current_size)
                    savings = avg_cost * 0.3  # Estimate 30% savings

                    recommendations.append(RightsizingRecommendation(
                        resource_id=resource_key,
                        resource_type=self._get_resource_type(service),
                        current_size=current_size,
                        recommended_size=recommended_size,
                        current_cost=avg_cost,
                        estimated_savings=savings,
                        confidence_percent=75,
                        reason=f"High cost variability ({variability:.1f}%) suggests oversizing. "
                               f"Consider smaller instance type or reserved instances."
                    ))

        self.recommendations = recommendations
        return recommendations

    def identify_unused_resources(self) -> List[OptimizationOpportunity]:
        """Identify unused or underutilized resources.

        Returns:
            List of unused resource opportunities
        """
        opportunities = []

        # Analyze cost patterns
        trends = self.analyze_cost_trends()

        for service, trend_data in trends.items():
            # Low cost services that could be consolidated or removed
            if trend_data['current_cost'] < 10:
                opportunities.append(OptimizationOpportunity(
                    opportunity_type="unused",
                    resource_id=f"{service}-low-cost",
                    service=service,
                    current_cost=trend_data['current_cost'],
                    potential_savings=trend_data['current_cost'] * 0.9,
                    priority="low",
                    actions=[
                        f"Review {service} usage and necessity",
                        "Consider consolidating with other services",
                        f"Potential monthly savings: ${trend_data['current_cost'] * 0.9:.2f}"
                    ]
                ))

        return opportunities

    def calculate_spot_savings(self) -> Dict[str, Any]:
        """Calculate potential savings from spot/preemptible instances.

        Returns:
            Dictionary with spot savings analysis
        """
        # Identify compute resources that could use spot instances
        compute_costs = sum(
            item.cost for item in self.cost_data
            if item.service == 'EC2'
        )

        # Spot instances typically cost 30-70% of on-demand (assume 50% average)
        spot_discount = 0.5
        potential_savings = compute_costs * spot_discount

        return {
            'service': 'EC2',
            'on_demand_cost': compute_costs,
            'spot_discount_percent': (1 - spot_discount) * 100,
            'potential_monthly_savings': potential_savings,
            'potential_annual_savings': potential_savings * 12,
            'suitable_workloads': [
                'Batch processing',
                'Non-critical background jobs',
                'Development and testing',
                'Data processing pipelines'
            ],
            'caution': [
                'Not suitable for production critical workloads',
                'Ensure proper error handling for interruptions',
                'Use spot instances with auto-scaling groups'
            ]
        }

    def generate_budget_recommendations(self, monthly_budget: float) -> Dict[str, Any]:
        """Generate budget recommendations.

        Args:
            monthly_budget: Monthly budget target

        Returns:
            Dictionary with budget analysis and recommendations
        """
        total_monthly_cost = sum(item.cost for item in self.cost_data if item.month == self._get_current_month())

        if total_monthly_cost == 0:
            # Calculate from all data
            total_monthly_cost = sum(item.cost for item in self.cost_data) / max(12, len(self.cost_data) // 7) if self.cost_data else 0

        budget_status = {
            'monthly_budget': monthly_budget,
            'current_spend': total_monthly_cost,
            'variance': monthly_budget - total_monthly_cost,
            'variance_percent': ((monthly_budget - total_monthly_cost) / monthly_budget * 100) if monthly_budget > 0 else 0,
            'status': 'over_budget' if total_monthly_cost > monthly_budget else 'within_budget',
            'projected_annual': total_monthly_cost * 12,
            'budget_annual': monthly_budget * 12
        }

        return budget_status

    def _get_size_class(self, service: str, cost: float) -> str:
        """Get size classification for resource.

        Args:
            service: Service name
            cost: Monthly cost

        Returns:
            Size class string
        """
        if cost > 1000:
            return "xlarge"
        elif cost > 500:
            return "large"
        elif cost > 200:
            return "medium"
        else:
            return "small"

    def _get_recommended_size(self, service: str, current_size: str) -> str:
        """Get recommended size class.

        Args:
            service: Service name
            current_size: Current size class

        Returns:
            Recommended size class
        """
        size_map = {
            "xlarge": "large",
            "large": "medium",
            "medium": "small",
            "small": "small"
        }
        return size_map.get(current_size, "medium")

    def _get_resource_type(self, service: str) -> ResourceType:
        """Get resource type for service.

        Args:
            service: Service name

        Returns:
            ResourceType enum
        """
        type_map = {
            'EC2': ResourceType.COMPUTE,
            'RDS': ResourceType.DATABASE,
            'S3': ResourceType.STORAGE,
            'CloudFront': ResourceType.NETWORK,
            'ElastiCache': ResourceType.CACHE,
            'SQS': ResourceType.QUEUE,
            'CloudWatch': ResourceType.MONITORING,
        }
        return type_map.get(service, ResourceType.COMPUTE)

    def _get_current_month(self) -> str:
        """Get current month string.

        Returns:
            Month string in YYYY-MM format
        """
        return datetime.now().strftime('%Y-%m')

    def generate_report(self, output_file: Optional[str] = None) -> str:
        """Generate comprehensive cost report.

        Args:
            output_file: Optional output file path

        Returns:
            Report as string
        """
        report_lines = [
            "=" * 80,
            "CLOUD INFRASTRUCTURE COST ANALYSIS REPORT",
            "=" * 80,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ]

        # Executive Summary
        report_lines.extend(self._generate_executive_summary())

        # Cost Trends
        report_lines.extend(self._generate_trends_section())

        # Cost Anomalies
        report_lines.extend(self._generate_anomalies_section())

        # Rightsizing Opportunities
        report_lines.extend(self._generate_rightsizing_section())

        # Spot Instance Opportunities
        report_lines.extend(self._generate_spot_section())

        # Recommendations
        report_lines.extend(self._generate_recommendations_section())

        report = "\n".join(report_lines)

        if output_file:
            Path(output_file).write_text(report)
            logger.info(f"Report saved to {output_file}")

        return report

    def _generate_executive_summary(self) -> List[str]:
        """Generate executive summary section.

        Returns:
            List of report lines
        """
        total_cost = sum(item.cost for item in self.cost_data)
        avg_monthly = total_cost / max(1, len(set(item.month for item in self.cost_data)))

        lines = [
            "EXECUTIVE SUMMARY",
            "-" * 80,
            f"Total Historical Cost: ${total_cost:,.2f}",
            f"Average Monthly Cost: ${avg_monthly:,.2f}",
            f"Total Data Points: {len(self.cost_data)}",
            f"Period Covered: {min((item.month for item in self.cost_data), default='N/A')} - "
            f"{max((item.month for item in self.cost_data), default='N/A')}",
            ""
        ]

        # Cost by service
        service_costs: Dict[str, float] = {}
        for item in self.cost_data:
            service_costs[item.service] = service_costs.get(item.service, 0) + item.cost

        lines.append("Cost by Service:")
        for service, cost in sorted(service_costs.items(), key=lambda x: x[1], reverse=True):
            percent = (cost / total_cost * 100) if total_cost > 0 else 0
            lines.append(f"  {service:<20} ${cost:>12,.2f}  ({percent:>5.1f}%)")

        lines.extend(["", ""])
        return lines

    def _generate_trends_section(self) -> List[str]:
        """Generate cost trends section.

        Returns:
            List of report lines
        """
        trends = self.analyze_cost_trends()

        lines = [
            "COST TRENDS ANALYSIS",
            "-" * 80,
        ]

        for service, trend_data in sorted(trends.items()):
            lines.extend([
                f"\n{service}:",
                f"  Current Cost:        ${trend_data['current_cost']:,.2f}",
                f"  Previous Month:      ${trend_data['previous_cost']:,.2f}",
                f"  Average Cost:        ${trend_data['average_cost']:,.2f}",
                f"  Change:              {trend_data['change_percent']:+.1f}%",
                f"  Trend:               {trend_data['trend'].upper()}",
            ])

        lines.append("\n")
        return lines

    def _generate_anomalies_section(self) -> List[str]:
        """Generate anomalies section.

        Returns:
            List of report lines
        """
        anomalies = self.detect_cost_anomalies()

        lines = [
            "COST ANOMALIES DETECTED",
            "-" * 80,
        ]

        if anomalies:
            for anomaly in anomalies:
                lines.extend([
                    f"\n{anomaly.service} ({anomaly.severity.upper()}):",
                    f"  Resource ID:         {anomaly.resource_id}",
                    f"  Expected Cost:       ${anomaly.expected_cost:,.2f}",
                    f"  Actual Cost:         ${anomaly.actual_cost:,.2f}",
                    f"  Deviation:           {anomaly.deviation_percent:.1f}%",
                    f"  Message:             {anomaly.message}",
                ])
        else:
            lines.append("No anomalies detected.")

        lines.append("\n")
        return lines

    def _generate_rightsizing_section(self) -> List[str]:
        """Generate rightsizing section.

        Returns:
            List of report lines
        """
        recommendations = self.identify_rightsize_opportunities()

        lines = [
            "RIGHTSIZING OPPORTUNITIES",
            "-" * 80,
        ]

        if recommendations:
            total_savings = 0
            for rec in recommendations:
                lines.extend([
                    f"\n{rec.resource_id}:",
                    f"  Resource Type:       {rec.resource_type.value.upper()}",
                    f"  Current Size:        {rec.current_size}",
                    f"  Recommended Size:    {rec.recommended_size}",
                    f"  Current Cost:        ${rec.current_cost:,.2f}",
                    f"  Estimated Savings:   ${rec.estimated_savings:,.2f}/month",
                    f"  Confidence:          {rec.confidence_percent}%",
                    f"  Reason:              {rec.reason}",
                ])
                total_savings += rec.estimated_savings

            lines.extend([
                "",
                f"TOTAL POTENTIAL SAVINGS: ${total_savings:,.2f}/month (${total_savings * 12:,.2f}/year)",
            ])
        else:
            lines.append("No rightsizing opportunities identified.")

        lines.append("\n")
        return lines

    def _generate_spot_section(self) -> List[str]:
        """Generate spot instance section.

        Returns:
            List of report lines
        """
        spot_analysis = self.calculate_spot_savings()

        lines = [
            "SPOT/PREEMPTIBLE INSTANCE STRATEGY",
            "-" * 80,
            f"\nService: {spot_analysis['service']}",
            f"On-Demand Cost:          ${spot_analysis['on_demand_cost']:,.2f}/month",
            f"Spot Discount:           {spot_analysis['spot_discount_percent']:.0f}%",
            f"Potential Savings:       ${spot_analysis['potential_monthly_savings']:,.2f}/month",
            f"Annual Savings:          ${spot_analysis['potential_annual_savings']:,.2f}/year",
            "",
            "Suitable Workloads:",
        ]

        for workload in spot_analysis['suitable_workloads']:
            lines.append(f"  • {workload}")

        lines.extend([
            "",
            "Implementation Cautions:",
        ])

        for caution in spot_analysis['caution']:
            lines.append(f"  • {caution}")

        lines.append("\n")
        return lines

    def _generate_recommendations_section(self) -> List[str]:
        """Generate recommendations section.

        Returns:
            List of report lines
        """
        lines = [
            "OPTIMIZATION RECOMMENDATIONS",
            "-" * 80,
            "",
            "IMMEDIATE ACTIONS (High Priority):",
            "1. Review and address cost anomalies",
            "   - Investigate services with unusual spending patterns",
            "   - Allocate root cause analysis resources",
            "",
            "2. Implement tagging strategy",
            "   - Enforce project, environment, owner, cost-center tags",
            "   - Automate tagging through infrastructure-as-code",
            "",
            "3. Set up budget alerts",
            "   - 50% threshold: informational",
            "   - 80% threshold: warning",
            "   - 100% threshold: critical alert",
            "",
            "MEDIUM-TERM ACTIONS (30 days):",
            "1. Right-size underutilized resources",
            "2. Evaluate reserved instance purchases",
            "3. Implement automated shutdown for dev/staging resources",
            "4. Enable detailed billing and cost allocation reports",
            "",
            "LONG-TERM STRATEGY (90+ days):",
            "1. Migrate suitable workloads to spot instances",
            "2. Implement auto-scaling policies",
            "3. Consolidate similar services where possible",
            "4. Establish cost optimization review cadence (monthly)",
            "",
        ]

        return lines

    def export_json(self, output_file: str) -> None:
        """Export analysis results as JSON.

        Args:
            output_file: Path to output JSON file
        """
        export_data = {
            'generated_at': datetime.now().isoformat(),
            'trends': self.analyze_cost_trends(),
            'anomalies': [asdict(a) for a in self.detect_cost_anomalies()],
            'rightsizing_recommendations': [asdict(r) for r in self.identify_rightsize_opportunities()],
            'spot_analysis': self.calculate_spot_savings(),
        }

        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)

        logger.info(f"Exported analysis to {output_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Cloud cost analysis and optimization report generator'
    )
    parser.add_argument(
        '--data-file',
        help='Path to cost data JSON file',
        default='cost_data.json'
    )
    parser.add_argument(
        '--output',
        help='Output file for text report',
        default='cost_report.txt'
    )
    parser.add_argument(
        '--json-output',
        help='Output file for JSON analysis',
        default='cost_analysis.json'
    )
    parser.add_argument(
        '--monthly-budget',
        type=float,
        help='Monthly budget target for budget analysis',
        default=5000
    )
    parser.add_argument(
        '--months-history',
        type=int,
        help='Number of months of historical data to analyze',
        default=12
    )
    parser.add_argument(
        '--anomaly-threshold',
        type=float,
        help='Anomaly detection threshold percentage',
        default=30
    )

    args = parser.parse_args()

    # Create analyzer
    analyzer = CostAnalyzer(
        data_file=args.data_file,
        months_history=args.months_history
    )

    # Load data
    if not analyzer.load_cost_data():
        logger.error("Failed to load cost data")
        sys.exit(1)

    # Run analysis
    logger.info("Analyzing cost data...")
    report = analyzer.generate_report(args.output)
    print(report)

    # Export JSON
    analyzer.export_json(args.json_output)
    logger.info(f"Analysis complete. Report saved to {args.output}")


if __name__ == '__main__':
    main()
