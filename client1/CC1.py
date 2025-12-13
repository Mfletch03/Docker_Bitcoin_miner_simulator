import paho.mqtt.client as mqtt
import time
import hashlib
import json
import os
import threading

# Environment variables
MQTT_HOST = os.getenv("MQTT_HOST", "broker")
MINER_NAME = os.getenv("MINER_NAME", "Miner1")
DIFFICULTY = int(os.getenv("DIFFICULTY", 4))

# Shared state
prev_hash = "0" * 64
nonce = 0
current_block = 1
mining_event = threading.Event()

# ========== HASHING ==========
def compute_hash():
    global nonce, prev_hash, MINER_NAME
    data = f"{MINER_NAME}{prev_hash}{nonce}".encode("utf-8")
    return hashlib.sha256(data).hexdigest()


# ========== MINING LOOP ==========
def mine_block(client, diff):
    global nonce, prev_hash, current_block

    target = "0" * diff
    local_prev = prev_hash
    print(f"⚒️  [{MINER_NAME}] Mining Block #{current_block} (prev {local_prev[:8]})...")

    while mining_event.is_set():
        nonce += 2
        b_hash = compute_hash()

        # Stop mining if new block found elsewhere
        if local_prev != prev_hash:
            print(f"🛑 [{MINER_NAME}] Detected new block — stopping current work.")
            break

        if b_hash.startswith(target):
            print(f"✅ [{MINER_NAME}] Found valid hash {b_hash[:12]}...")
            result = {"miner": MINER_NAME, "block": current_block, "hash": b_hash}
            client.publish("foundblock", json.dumps(result))
            break

        # Periodic throttling to protect VM CPU
        if nonce % 5000 == 0:
            time.sleep(0.05)

    # Ensure mining stops cleanly
    mining_event.clear()


# ========== MQTT CALLBACKS ==========
def on_message(client, userdata, msg):
    global prev_hash, current_block

    payload = msg.payload.decode("utf-8").strip()
    topic = msg.topic
    print(f"[{MINER_NAME}] 📨 Received on '{topic}': {payload}")

    if topic == "mine":
        if payload.lower() == "start":
            if not mining_event.is_set():
                mining_event.set()
                threading.Thread(target=mine_block, args=(client, DIFFICULTY), daemon=True).start()
        elif payload.lower() == "stop":
            if mining_event.is_set():
                mining_event.clear()
                print(f"🟥 [{MINER_NAME}] Stopping mining...")

    elif topic == "newblock":
        prev_hash = payload
        current_block += 1
        print(f"🔄 [{MINER_NAME}] Updated previous hash: {prev_hash[:12]}")


# ========== MAIN LOOP ==========
def run_miner():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_message = on_message

    # Connect to broker (retry until success)
    while True:
        try:
            client.connect(MQTT_HOST, 1883)
            break
        except Exception as e:
            print(f"❌ [{MINER_NAME}] Broker connection failed: {e}. Retrying in 2s...")
            time.sleep(2)

    client.subscribe("mine")
    client.subscribe("newblock")
    client.loop_start()

    print(f"[{MINER_NAME}] Miner online — waiting for controller commands...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"🛑 [{MINER_NAME}] Interrupted by user.")
        mining_event.clear()
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    run_miner()

