# controller.py
import paho.mqtt.client as mqtt
import json
import time
import os
from collections import defaultdict

# Environment variables from docker-compose
MQTT_HOST = os.getenv("MQTT_HOST", "broker")
START_DELAY = 2.0

# Global state
controller_running = False
current_block = 1
winner_announced = False
winning_hash = None

wins = defaultdict(int)
win_blocks = defaultdict(list)

# ========== MQTT CALLBACK ==========
def on_message(client, userdata, message):
    global current_block, winner_announced, winning_hash, controller_running

    msg = message.payload.decode("utf-8").strip()
    topic = message.topic
    print(f"[Controller] Received on '{topic}': {msg}")

    # Start / Stop Commands
    if topic == "controller_cmd":
        lower = msg.lower()
        if lower in ["start", "go", "begin"]:
            if not controller_running:
                controller_running = True
                print("🚀 [Controller] Starting miners...")
            else:
                print("⚙️ [Controller] Already running.")

        elif lower in ["stop", "end", "finish"]:
            if controller_running:
                controller_running = False
                print("⏹️ [Controller] Stopping miners...")
                stop_controller(client)
            else:
                print("⏸️ [Controller] Already stopped.")

    # Found block report from miners
    elif topic == "foundblock":
        try:
            data = json.loads(msg)
        except json.JSONDecodeError:
            print("⚠️ [Controller] Invalid JSON from miner.")
            return

        miner = data.get("miner")
        block = data.get("block")
        h = data.get("hash")

        if not miner or not h or block is None:
            print("⚠️ [Controller] Missing miner or hash field.")
            return

        # Accept winner only if it's for the current block and no winner yet
        if block == current_block and not winner_announced:
            winner_announced = True
            winning_hash = h
            print(f"🏆 [Controller] Winner for Block #{block}: {miner} ({h[:12]})")

            # Record results
            wins[miner] += 1
            win_blocks[miner].append(block)

            # Publish next block seed so miners update prev_hash
            client.publish("newblock", h)

        elif block == current_block and winner_announced:
            print(f"⏱️ [Controller] Late result from {miner} for Block #{block}")
        else:
            print(f"🗑️ [Controller] Ignored result from {miner} for Block #{block}")


# ========== FINAL STATS ==========
def print_final_stats(client):
    print("\n======= Final Mining Statistics ======")
    if not wins:
        print("No blocks were mined.")
        # still publish empty summary
        client.publish("final_results", json.dumps({"results": {}, "winner": None, "total_blocks": 0}))
        return

    averages = {}
    for miner, blocks in win_blocks.items():
        avg_block = sum(blocks) / len(blocks) if blocks else 0
        averages[miner] = avg_block
    
    total_blocks_mined = sum(wins.values())
    top_miner = max(wins, key=wins.get)
    top_wins = wins[top_miner]

    print(f"Total blocks mined: {total_blocks_mined}")

    for miner in sorted(wins.keys()):
        print(f"  --{miner}: {wins[miner]} wins, avg block = {averages[miner]:.2f}")

    print(f"\n🏁 Miner with most wins: {top_miner} ({top_wins} total)")
    print("=====================================\n")

    # Also publish summary
    summary = {
        "results": {
            miner: {"wins": wins[miner], "avg_block": averages[miner]}
            for miner in wins
        },
        "winner": top_miner,
        "total_blocks": sum(wins.values()),
    }
    client.publish("final_results", json.dumps(summary))
    print("[Controller] 📢 Published final results to 'final_results' topic.")


# ========== STOP CONTROLLER ==========
def stop_controller(client):
    global controller_running
    controller_running = False
    # tell miners to stop
    client.publish("mine", "stop")
    # give miners a moment to stop and for any remaining foundblock messages to arrive
    time.sleep(0.5)
    print_final_stats(client)


# ========== MAIN CONTROLLER LOOP ==========
def run_controller():
    global current_block, winner_announced, winning_hash

    # pick callback_api_version to avoid deprecation warning (paho >= 1.6)
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_message = on_message
    client.connect(MQTT_HOST, 1883)
    client.subscribe("foundblock")
    client.subscribe("controller_cmd")
    client.loop_start()

    print("[Controller] Ready — waiting for 'start' command...")

    try:
        while True:
            if controller_running:
                if not winner_announced:
                    print(f"🧱 [Controller] Starting mining for Block #{current_block}")
                    client.publish("mine", "start")

                    # Wait until a miner reports a block or stop is pressed
                    while controller_running and not winner_announced:
                        time.sleep(0.2)

                if winner_announced:
                    print(f"⏭️ [Controller] Preparing next block...")
                    time.sleep(START_DELAY)
                    current_block += 1
                    winner_announced = False
                    winning_hash = None
            else:
                time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[Controller] Interrupted by user.")
        stop_controller(client)
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    run_controller()

