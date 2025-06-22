from morphcloud.api import MorphCloudClient
import argparse
import time
import json
import shutil
import os
import logging
import hashlib

# Configure simple logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='chess_sync.log'
)
logger = logging.getLogger('ChessSync')

def sync_game_state(instance_id, game_id, timeout=60, game_timeout=20):
    """
    Synchronize chess game state from a MorphCloud instance to local files.
    Uses hash-based change detection to avoid unnecessary updates.
    
    Args:
        instance_id (str): MorphCloud instance ID
        game_id (str): Game ID to synchronize
        timeout (int): How long to continue synchronizing in seconds
        game_timeout (int): How long a game can be missing before considered inactive
    """
    # Create necessary directories
    os.makedirs("tmp", exist_ok=True)
    os.makedirs("chess_autosaves", exist_ok=True)
    
    # Initialize client and connect to instance
    client = MorphCloudClient()
    instance = client.instances.get(instance_id)
    
    # Track last seen state to avoid redundant updates
    last_content_hash = None
    last_activity_time = time.time()
    consecutive_unchanged = 0
    max_unchanged = 15  # Stop after 15 unchanged checks
    
    def calculate_hash(file_path):
        """Calculate MD5 hash of file contents"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"Error calculating hash: {e}")
            return None
    
    with instance.ssh() as ssh:
        sftp = ssh._client.open_sftp()
        try:
            # Set up timing
            start_time = time.time()
            end_time = start_time + timeout
            
            temp_file = f"tmp/game_id_{game_id}_tmp.json"
            target_file = f"chess_autosaves/game_id_{game_id}.json"
            remote_file = f"app/chess_autosaves/game_id_{game_id}.json"
            
            logger.info(f"Starting synchronization for game {game_id}")
            
            while time.time() < end_time and consecutive_unchanged <= max_unchanged:
                try:
                    # Download to temp file
                    sftp.get(remote_file, temp_file)
                    
                    # Verify if the file is valid JSON and has changed
                    try:
                        # Check if valid JSON
                        game_state = json.load(open(temp_file))
                        
                        # Get content hash
                        current_hash = calculate_hash(temp_file)
                        
                        # Update last activity time
                        last_activity_time = time.time()
                        
                        # Only update if content has changed
                        if current_hash != last_content_hash:
                            logger.info(f"Game state changed for game {game_id}")
                            last_content_hash = current_hash
                            consecutive_unchanged = 0
                            
                            # Move atomically to avoid partial reads by the monitor
                            shutil.move(temp_file, target_file)
                            print(f"Updated game state for game {game_id}")
                        else:
                            consecutive_unchanged += 1
                            
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in downloaded file for game {game_id}")
                        consecutive_unchanged += 1
                        
                except FileNotFoundError:
                    logger.warning(f"Remote file not found for game {game_id}")
                    
                    # Check if the game has been missing too long
                    time_since_activity = time.time() - last_activity_time
                    if time_since_activity > game_timeout:
                        logger.info(f"Game {game_id} appears to be inactive (no updates for {time_since_activity:.1f}s)")
                        break
                
                # Wait before next check
                time.sleep(0.5)
                
            logger.info(f"Sync complete for game {game_id}: timeout={time.time() >= end_time}, "
                       f"unchanged_limit={consecutive_unchanged > max_unchanged}")
            
        except Exception as e:
            logger.error(f"Error during synchronization: {e}")
        finally:
            sftp.close()


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Download files from MorphCloud instance')
    parser.add_argument('-instance_id', type=str, required=True, 
                        help='ID of the MorphCloud instance')
    parser.add_argument('-game_id', type=str, required=True, 
                        help='ID of the game to download')
    parser.add_argument('-timeout', type=int, default=60, 
                        help='Timeout in seconds for the download')
    parser.add_argument('-game_timeout', type=int, default=20,
                        help='How long a game can be missing before considered inactive')
    args = parser.parse_args()

    # Run synchronization
    sync_game_state(
        args.instance_id, 
        args.game_id, 
        timeout=args.timeout,
        game_timeout=args.game_timeout
    )
