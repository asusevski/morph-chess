from logging import exception
from morphcloud.api import MorphCloudClient
import argparse
import time
import json
import shutil


if __name__=="__main__":
    
    # need gameid, instance id, timeout in seconds to keep syncing
    # optional file param if want to test with file
    parser = argparse.ArgumentParser(description='Download files from MorphCloud instance')
    parser.add_argument('-instance_id', type=str, default=None, help='ID of the MorphCloud instance', required=True)
    parser.add_argument('-game_id', type=str, default=None, help='ID of the game to download', required=False)
    # parser.add_argument('-file', type=str, default=None, help='File to download (optional). Full path expected.', required=False)
    parser.add_argument('-timeout', type=int, default=60, help='Timeout in seconds for the download', required=False)
    args = parser.parse_args()

    client = MorphCloudClient()
    instance = client.instances.get(args.instance_id)

    with instance.ssh() as ssh:
        sftp = ssh._client.open_sftp()
        try:
            # while timeout not reached keep syncing
            start_time = time.time()
            end_time = start_time + args.timeout
            last_fen = None
            c = 0
            while time.time() < end_time and c <= 15:
                try:
                    # if args.file is not None:
                    #     sftp.get(args.file, args.file)
                    #     print(f"Downloading game state for game {args.game_id}...")
                    # else:
                    
                    # save to a temp file
                    sftp.get(f"app/chess_autosaves/game_id_{args.game_id}.json", f"tmp/game_id_{args.game_id}_tmp.json")
                    print(f"Downloading game state for game {args.game_id}...")
                    #TODO: add checking for when the game is over (no new updates or max moves reached)
                    game_state = json.load(open(f"tmp/game_id_{args.game_id}_tmp.json"))
                    try:
                        new_fen = game_state["fen"]
                    except KeyError:
                        continue

                    if last_fen is None or last_fen != new_fen:
                        last_fen = new_fen
                        shutil.move(f"tmp/game_id_{args.game_id}_tmp.json", f"chess_autosaves/game_id_{args.game_id}.json")
                    else:
                        c += 1
                    time.sleep(0.5)
                except FileNotFoundError:
                    continue

        finally:
            sftp.close()

