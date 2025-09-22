from morphcloud.api import MorphCloudClient
import os


if __name__ == "__main__":
    client = MorphCloudClient()
    
    # initialize base instance
    snapshot = client.snapshots.create(
        vcpus=1,
        memory=2048,
        disk_size=8192,
        digest="chromebox-1-1",
    )

    snapshot_id = snapshot.id
    instance = client.instances.start(snapshot_id=snapshot_id)

    # upload project to base instance
    with instance.ssh() as ssh:
        sftp = ssh._client.open_sftp()

        sftp.put("./config.yaml", "app/config.yaml")
        sftp.put("./pyproject.toml", "app/pyproject.toml")
        sftp.put("./requirements.txt", "app/requirements.txt")
        sftp.put("./schemas.py", "app/schemas.py")
        sftp.put("./chess_game.py", "app/chess_game.py")

    # basically all file modifications here
    startup_commands = """
    apt-get update
    apt-get install -y python3-pip
    curl -LsSf https://astral.sh/uv/install.sh | bash
    cd app
    uv add pyproject.toml
    """
    instance.exec(command=startup_commands)

    instance_startup = """
    cd app
    source .venv/bin/activate
    """

    snapshot, clones = instance.branch(count=3)
    print(f"Snapshot created: {snapshot.id}")

    game_ids = [1,2,3]
    strategies = ["aggressive", "defensive", "balanced"]

                    
    for clone, game_id, strategy in zip(clones, game_ids, strategies):
        print(f"Starting game {game_id} on instance {clone.id} with strategy {strategy}")
        instance = client.instances.get(instance_id=clones[0].id)
        
        start_game_command = f"python agent.py --game-id {game_id}"
        clone.exec(command=instance_startup + "\n" + start_game_command)
        result = clone.exec(command=f"python agent.py --game-id {game_id} --strategy {strategy}")
        print(f"Stdout:\n{result.stdout}")

