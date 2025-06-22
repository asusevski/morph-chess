from morphcloud.api import MorphCloudClient
import time


client = MorphCloudClient()
instance = client.instances.get("morphvm_0lupadv4")

with instance.ssh() as ssh:
    sftp = ssh._client.open_sftp()
    try:
        # while timeout not reached keep syncing
        start_time = time.time()
        end_time = start_time + 60
        while time.time() < end_time:
            try:
                sftp.get(f"app/chess_autosaves/game_id_1.json", f"chess_autosaves/game_id_1.json")
                time.sleep(0.5)
                print(f"Downloading game state for game 1...")
            except FileNotFoundError:
                continue

    finally:
        sftp.close()


