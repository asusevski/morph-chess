#!/usr/bin/env python3
"""
Script to delete all Morph Cloud instances.
This script will list all running instances and stop them.
"""

import os
import sys
import time
from morphcloud.api import MorphCloudClient

def delete_all_instances(confirm=True):
    """
    Delete all Morph Cloud instances.
    
    Args:
        confirm (bool): Whether to ask for confirmation before deleting.
    """
    # Initialize the Morph Cloud client
    try:
        client = MorphCloudClient()
    except Exception as e:
        print(f"Error initializing Morph Cloud client: {e}")
        print("Make sure you have set up your API key correctly.")
        sys.exit(1)
    
    # List all instances
    try:
        instances = client.instances.list()
    except Exception as e:
        print(f"Error listing instances: {e}")
        sys.exit(1)
    
    # Check if there are any instances
    if not instances:
        print("No instances found.")
        return
    
    # Display the instances
    print(f"Found {len(instances)} instance(s):")
    for i, instance in enumerate(instances, 1):
        print(f"{i}. ID: {instance.id}, Status: {instance.status}")
        
        # Display metadata if available
        if hasattr(instance, 'metadata') and instance.metadata:
            metadata_str = ", ".join(f"{k}={v}" for k, v in instance.metadata.items())
            print(f"   Metadata: {metadata_str}")
    
    # Ask for confirmation
    if confirm:
        response = input("\nAre you sure you want to delete ALL these instances? (yes/no): ")
        if response.lower() not in ["yes", "y"]:
            print("Operation cancelled.")
            return
    
    # Delete each instance
    success_count = 0
    error_count = 0
    
    for i, instance in enumerate(instances, 1):
        print(f"\nStopping instance {i}/{len(instances)}: {instance.id}")
        try:
            print(f"  Status before stop: {instance.status}")
            
            # Stop the instance
            instance.stop()
            
            # Wait for the instance to stop
            for _ in range(30):  # Try for up to 30 seconds
                # Refresh instance status
                instance = client.instances.get(instance_id=instance.id)
                print(f"  Current status: {instance.status}")
                
                if instance.status == "stopped":
                    break
                    
                time.sleep(1)
            
            success_count += 1
            print(f"  Successfully stopped instance {instance.id}")
        except Exception as e:
            error_count += 1
            print(f"  Error stopping instance {instance.id}: {e}")
    
    # Print summary
    print(f"\nOperation completed: {success_count} instances successfully stopped, {error_count} errors")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Delete all Morph Cloud instances")
    parser.add_argument("--force", "-f", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()
    
    delete_all_instances(confirm=not args.force)
