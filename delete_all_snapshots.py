import os
import sys
from morphcloud.api import MorphCloudClient

def delete_all_snapshots(confirm=True):
    """
    Delete all Morph Cloud snapshots.
    
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
    
    # List all snapshots
    try:
        snapshots = client.snapshots.list()
    except Exception as e:
        print(f"Error listing snapshots: {e}")
        sys.exit(1)
    
    # Check if there are any snapshots
    if not snapshots:
        print("No snapshots found.")
        return
    
    # Display the snapshots
    print(f"Found {len(snapshots)} snapshot(s):")
    for i, snapshot in enumerate(snapshots, 1):
        print(f"{i}. ID: {snapshot.id}, Created: {snapshot.created}")
        
        # Display metadata if available
        if hasattr(snapshot, 'metadata') and snapshot.metadata:
            metadata_str = ", ".join(f"{k}={v}" for k, v in snapshot.metadata.items())
            print(f"   Metadata: {metadata_str}")
    
    # Ask for confirmation
    if confirm:
        response = input("\nAre you sure you want to delete ALL these snapshots? (yes/no): ")
        if response.lower() not in ["yes", "y"]:
            print("Operation cancelled.")
            return
    
    # Delete each snapshot
    success_count = 0
    error_count = 0
    
    for i, snapshot in enumerate(snapshots, 1):
        print(f"\nDeleting snapshot {i}/{len(snapshots)}: {snapshot.id}")
        try:
            # Delete the snapshot
            # Try both approaches (API might vary between versions)
            try:
                # Method 1: Delete directly on snapshot object
                snapshot.delete()
            except AttributeError:
                # Method 2: Alternate approach if Method 1 fails
                client.snapshots.delete(snapshot_id=snapshot.id)
            success_count += 1
            print(f"  Successfully deleted snapshot {snapshot.id}")
        except Exception as e:
            error_count += 1
            print(f"  Error deleting snapshot {snapshot.id}: {e}")
    
    # Print summary
    print(f"\nOperation completed: {success_count} snapshots successfully deleted, {error_count} errors")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Delete all Morph Cloud snapshots")
    parser.add_argument("--force", "-f", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()
    
    delete_all_snapshots(confirm=not args.force)
