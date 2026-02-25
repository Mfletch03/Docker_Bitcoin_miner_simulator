# Docker Bitcoin Miner Simulator

Lightweight simulation of a simplified Bitcoin-style mining network using MQTT + Docker.

This repository contains an MQTT broker (Eclipse Mosquitto), a controller service that coordinates mining rounds, and two miner clients which attempt to find hashes by brute force. The components communicate using MQTT topics so you can simulate competition, discovery, and result propagation.

**Contents**
- Broker: MQTT broker (mosquitto) for message passing.
- Controller: Orchestrates mining rounds, announces blocks, and accepts miner results.
- Clients (Miner1 & Miner2): Simulated miners that listen for start/stop commands and publish found blocks.

**MQTT Topics**
- `controller_cmd` — Commands to the controller (e.g. `start`, `stop`).
- `mine` — Sent by controller to tell miners to `start` or `stop` mining.
- `foundblock` — Miners publish their mined block information here.
- `newblock` — Controller publishes the winning block hash so miners update their prev_hash.
- `final_results` — Controller publishes a summary when mining stops.

How It Works
- The controller subscribes to `foundblock` to receive miner reports. When the first valid block for the current round is received, it publishes the new block hash to `newblock` and records a win for the miner that reported it.
- When the controller publishes `mine: start`, miners begin hashing for a block. When a hash matching the configured DIFFICULTY (`0` prefix length) is found, the miner publishes details to `foundblock`.

Service variables
- `MQTT_HOST` — Hostname of the MQTT broker (defaults to `broker` when using Docker Compose).
- `MINER_NAME` — Identifier for a miner (e.g. `Miner1`).
- `DIFFICULTY` — Number of leading zeros required for a valid hash (default `4`).
- `START_DELAY` — Delay between blocks when running in the controller.

Running services locally (with Docker Compose recommended)
1. If you want to keep the existing `docker-compose.yml` name, use the file explicitly:

```bash
docker compose up
```

2. open a second termial to publish the commands

start command:
```bash
#In termial 2
docker compose -f docker-compose.yml exec broker mosquitto_pub -h localhost -p 1883 -t controller_cmd -m start
```
Stop command:
```bash
#In termial 2
docker compose -f docker-compose.yml exec broker mosquitto_pub -h localhost -p 1883 -t controller_cmd -m stop
```

3. When you are finished using the code the following command to take down and remove the docker containers.  
```bash
#In termial 2
docker compose down
```

Running services locally (without Docker)
1. Install requirements for client and controller:
```bash
python -m pip install -r controller/requirements.txt
python -m pip install -r client1/requirements.txt
python -m pip install -r client2/requirements.txt
```
2. Run a local mosquitto broker (if not using Docker):
```bash
mosquitto -c Broker/mosquitto.conf
```
3. In separate terminals run the controller and each miner:
```bash
# Terminal A: Controller
MQTT_HOST=localhost python controller/controllor.py

# Terminal B: Miner 1
MQTT_HOST=localhost MINER_NAME=Miner1 python client1/CC1.py

# Terminal C: Miner 2
MQTT_HOST=localhost MINER_NAME=Miner2 python client2/CC2.py
```

Interacting with the simulation
- Start mining: publish `start` to `controller_cmd` (controller will publish `mine:start`):
```bash
# Example using mosquitto_pub
mosquitto_pub -h <broker_host> -t controller_cmd -m start
```
- Stop mining: publish `stop` to `controller_cmd`.
- Subscribe to topics to monitor events:
```bash
mosquitto_sub -h <broker_host> -t foundblock -v
mosquitto_sub -h <broker_host> -t newblock -v
```

Important note
- You can use any synonym for start and stop for the start and stop command.  

Troubleshooting
- If a miner does not connect, ensure `MQTT_HOST` resolves from the container (with Compose it should be `broker`).
- Watch logs for errors (file names and case mismatches are common; see 'Known Issues' above).
- If miners are crashing due to modules not found, verify `paho-mqtt` is installed in the environment the script runs in.

License
- MIT-like: this repo doesn't include a license file — add one if you plan to share publicly.

Enjoy the simulation and tweak `DIFFICULTY`, `START_DELAY`, or add more miners for testing!
