import time
from morphcloud.api import MorphCloudClient, Instance, Snapshot, ApiError
import argparse
import asyncio
import os
import json
import shutil
import logging
import hashlib
from typing import Optional, Union


async def play_chess(client, instance_id, game_id, moves, strategy):
    instance = client.instances.get(instance_id)
    #TODO: update for other model providers/actually use config.yaml for orchestration
    run_agent_cmd = f"export OPENAI_API_KEY={os.environ.get('OPENAI_API_KEY')} && cd app && mkdir chess_autosaves && uv add pyproject.toml && uv run agent.py --game-id {game_id} --moves {moves} --strategy {strategy}"
    await instance.aexec(command=run_agent_cmd)


async def sync_gamestate(client, instance_id, game_id, timeout=60, game_timeout=20):
    """
    Asynchronously synchronize chess game state from a MorphCloud instance
    to local files. Uses hash-based change detection to avoid unnecessary updates.
    """
    os.makedirs("tmp", exist_ok=True)
    os.makedirs("chess_autosaves", exist_ok=True)
    instance = client.instances.get(instance_id)
    last_content_hash = None
    last_activity_time = time.time()
    consecutive_unchanged = 0
    max_unchanged = 15
    def calculate_hash_sync(file_path):
        try:
            with open(file_path, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"Error calculating hash: {e}")
            return None
    async def calculate_hash(file_path):
        return await asyncio.to_thread(calculate_hash_sync, file_path)
    ssh_ = await asyncio.to_thread(instance.ssh)
    with ssh_ as ssh:
        sftp = ssh._client.open_sftp()
        try:
            start_time = time.time()
            end_time = start_time + timeout
            temp_file = f"tmp/game_id_{game_id}_tmp.json"
            target_file = f"chess_autosaves/game_id_{game_id}.json"
            remote_file = f"app/chess_autosaves/game_id_{game_id}.json"
            logger.info(f"Starting synchronization for game {game_id}")
            while time.time() < end_time and consecutive_unchanged <= max_unchanged:
                try:
                    # Run blocking SFTP call in a thread
                    await asyncio.to_thread(sftp.get, remote_file, temp_file)
                    try:
                        # Run blocking JSON load in a thread
                        game_state = await asyncio.to_thread(
                            lambda: json.load(open(temp_file))
                        )
                        #TODO: just check FEN string for changes instead of whole file hash?
                        current_hash = await calculate_hash(temp_file)
                        last_activity_time = time.time()
                        if current_hash != last_content_hash:
                            logger.info(f"Game state changed for game {game_id}")
                            last_content_hash = current_hash
                            consecutive_unchanged = 0
                            # Atomic move
                            await asyncio.to_thread(shutil.move, temp_file, target_file)
                        else:
                            consecutive_unchanged += 1
                    except json.JSONDecodeError:
                        logger.warning(
                            f"Invalid JSON in downloaded file for game {game_id}"
                        )
                        consecutive_unchanged += 1
                except FileNotFoundError:
                    logger.warning(f"Remote file not found for game {game_id}")
                    time_since_activity = time.time() - last_activity_time
                    if time_since_activity > game_timeout:
                        logger.info(
                            f"Game {game_id} inactive (no updates for {time_since_activity:.1f}s)"
                        )
                        break
                await asyncio.sleep(0.5)
            logger.info(
                f"Sync complete for game {game_id}: "
                f"timeout={time.time() >= end_time}, "
                f"unchanged_limit={consecutive_unchanged > max_unchanged}"
            )
        except Exception as e:
            logger.error(f"Error during synchronization: {e}")
        finally:
            sftp.close()


def setup_snapshot(client: MorphCloudClient, snapshot_id: Optional[Union[str, int]], vcpus=1, memory=4096, disk_size=8192) -> Snapshot:
    if snapshot_id:
        try:
            snapshot = client.snapshots.get(snapshot_id)
        except ApiError as e:
            logger.error(f"Failed to retrieve snapshot {snapshot_id}: {e}")
            raise
    else:
        snapshot = client.snapshots.create(
            vcpus=1,
            memory=4096,
            disk_size=8192
        )
    snapshot = (
        snapshot.setup("apt update -y")
        .setup("apt-get install -y python3-pip")
        .setup("curl -LsSf https://astral.sh/uv/install.sh | bash")
        .setup("mkdir app")
    )
    return snapshot


def setup_base_instance(client: MorphCloudClient, snapshot: Snapshot) -> Instance:
    instance = client.instances.start(snapshot_id=snapshot.id, ttl_seconds=3600, ttl_action="stop")
    cwd = os.getcwd()
    # upload project to base instance
    with instance.ssh() as ssh:
        sftp = ssh._client.open_sftp()
        sftp.put(os.path.join(cwd, "config.yaml"), "app/config.yaml")
        sftp.put(os.path.join(cwd, "pyproject.toml"), "app/pyproject.toml")
        sftp.put(os.path.join(cwd, "requirements.txt"), "app/requirements.txt")
        sftp.put(os.path.join(cwd, "schemas.py"), "app/schemas.py")
        sftp.put(os.path.join(cwd, "chess_game.py"), "app/chess_game.py")
        sftp.put(os.path.join(cwd, "chess_engine.py"), "app/chess_engine.py")
        sftp.put(os.path.join(cwd, "agent.py"), "app/agent.py")
    return instance


async def main(*args, **kwargs):
    client = MorphCloudClient()
    snapshot_id = kwargs.get("snapshot_id", None)
    instance_id = kwargs.get("instance_id", None)
    if instance_id:
        base_instance = client.instances.get(instance_id)
        logger.info(f"Using existing base instance: {base_instance.id}")
        snapshot = None # don't need snapshot in this case
    else:
        snapshot = setup_snapshot(client, snapshot_id)
        base_instance = setup_base_instance(client, snapshot)
        logger.info(f"New base instance started: {base_instance.id}")
    # TODO: get these from config --
    NUM_MOVES = 2
    # generate uuids -- MUST have game ids at this point for metadata tracking
    game_ids = [1,2,3]
    strategies = ["aggressive", "defensive", "balanced"]
    # --
    snapshot, clones = base_instance.branch(count=len(game_ids))
    logger.info(f"Clones created from snapshot {snapshot.id}: {[c.id for c in clones]}")
    # create metadata for tracking/visualization
    for game_id, clones, strategy in zip(game_ids, clones, strategies):
        metadata = {
            "instance_id": clones.id,
            "game_id": game_id,
            "strategy": strategy
        }
        os.makedirs("chess_autosaves", exist_ok=True)
        with open(f"chess_autosaves/metadata_game_id_{game_id}.json", "w") as f:
            json.dump(metadata, f, indent=4)
    # TODO: assert lengths
    play_chess_tasks = list(zip(clones, game_ids, strategies))
    sync_gamestate_tasks = list(zip(clones, game_ids))
    await asyncio.gather(
        *[play_chess(client, c.id, g, NUM_MOVES, s) for c, g, s in play_chess_tasks],
        *[sync_gamestate(client, c.id, g) for c, g in sync_gamestate_tasks],
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filename='chess_orchestrator.log'
    )
    logger = logging.getLogger(__name__)
    parser = argparse.ArgumentParser(description='Morph Chess Orchestrator')
    parser.add_argument('--snapshot-id', type=str, help='Snapshot ID to use for instances')
    parser.add_argument('--instance-id', type=str, help='Base instance if already created')
    parser.add_argument('--persist-instances', type=bool, default=False, help='Whether to keep instances running after script ends')
    parser.add_argument('--persist-snapshots', type=bool, default=False, help='Whether to keep snapshots available after script ends')
    args = parser.parse_args()
    if args.instance_id:
        asyncio.run(main(instance_id=args.instance_id))
    elif args.snapshot_id:
        asyncio.run(main(snapshot_id=args.snapshot_id))
    else:
        asyncio.run(main())
    # Cleanup
    client = MorphCloudClient()
    if not args.persist_instances:
        client = MorphCloudClient()
        instances = client.instances.list()
        for instance in instances:
            try:
                instance.stop()
                logger.info(f"Stopped instance {instance.id}")
            except ApiError as e:
                logger.error(f"Failed to stop instance {instance.id}: {e}")
    if not args.persist_snapshots:
        snapshots = client.snapshots.list()
        for snapshot in snapshots:
            try:
                snapshot.delete()
                logger.info(f"Deleted snapshot {snapshot.id}")
            except ApiError as e:
                logger.error(f"Failed to delete snapshot {snapshot.id}: {e}")

