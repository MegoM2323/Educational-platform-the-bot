#!/usr/bin/env python
"""
Standalone Pachca API token validation script.
Tests Pachca connection without Django's full setup.
"""
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chat.services.pachca_service import PachcaService


def main():
    """Test Pachca API connection."""
    print("=" * 70)
    print("PACHCA API TOKEN VALIDATION TEST")
    print("=" * 70)

    service = PachcaService()

    # Display configuration
    print(f"\nAPI Token: {'***' + service.api_token[-4:] if service.api_token else 'NOT SET'}")
    print(f"Channel ID: {service.channel_id or 'NOT SET'}")
    print(f"Base URL: {service.base_url}")
    print(f"Is Configured: {service.is_configured()}")

    # Test token validation
    if service.is_configured():
        print("\n" + "-" * 70)
        print("Validating token...")
        print("-" * 70)

        if service.validate_token():
            print("✅ SUCCESS: Pachca token is valid!")
            return 0
        else:
            print("❌ FAILED: Pachca token validation failed")
            print("\nCheck logs above for error details.")
            return 1
    else:
        print("\n" + "-" * 70)
        print("⚠️ WARNING: Pachca not configured")
        print("-" * 70)
        print("\nTo configure Pachca, set these environment variables:")
        print("  - PACHCA_FORUM_API_TOKEN")
        print("  - PACHCA_FORUM_CHANNEL_ID")
        print("\nSee .env.example for details.")
        return 2


if __name__ == '__main__':
    sys.exit(main())
