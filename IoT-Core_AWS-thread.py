import time
import queue
import threading
import random
import json
import serial 
import paho.mqtt.client as paho
from paho import mqtt
from config import AWS_ENDPOINT, PATH_ROOT_CA, PATH_CERT, PATH_KEY 

# ---------------------------------------------------------
# CONFIGURAZIONE
# ---------------------------------------------------------
MODE         = "random"        # "random" oppure "serial"
SERIAL_PORT  = "COM3"
SERIAL_BAUD  = 115200
QUEUE_MAXSIZE = 10


# ---------------------------------------------------------
# SCHEMA MESSAGGI
# Il micro stampa:  msg_type, val1, val2, ...
# 2 bit -> 4 tipi (0..3), ciascuno con topic e campi propri.
# Modifica fields e topic in base al payload reale del firmware.
# ---------------------------------------------------------
MSG_SCHEMA = {
    0: {
        "topic":  "P5/telemetry",
        "fields": ["speed", "T_engine_1", "T_engine_2", "T_inverter_1"],
        "types":  [int, int, int, int],
    },
    1: {
        "topic":  "P5/telemetry",
        "fields": ["latitude", "longitude"],
        "types":  [float, float],
    },
    2: {
        "topic":  "P5/telemetry",
        "fields": ["V_Moduli", "V_LV", "SoC", "I_BMS", "T_battery"],
        "types":  [int, int, int, int, int],
    },
    3: {
        "topic":  "P5/telemetry",
        "fields": [
            "err_inv1", "err_inv2", "err_apps", "err_overcurrent",
            "err_overvoltage", "err_cell_ow", "err_temp_ow",
            "err_curr_sensor", "err_slave_sensor",
        ],
        "types":  [int] * 9,
    }
}

stop_event = threading.Event()
data_queue: queue.Queue = queue.Queue(maxsize=QUEUE_MAXSIZE)


# ---------------------------------------------------------
# PARSER: riga seriale -> (topic, dict)
# Formato atteso: "msg_type,val1,val2,...\n"
# ---------------------------------------------------------
def parse_frame(line: str) -> tuple[str, dict] | None:
    parts = line.split(",")
    if len(parts) < 2:
        return None

    try:
        msg_type = int(parts[0])
    except ValueError:
        return None

    schema = MSG_SCHEMA.get(msg_type)
    if schema is None:
        print(f"[parser] msg_type {msg_type} non previsto")
        return None

    payload_parts = parts[1:]
    if len(payload_parts) != len(schema["fields"]):
        print(f"[parser] tipo {msg_type}: attesi {len(schema['fields'])} campi, "
              f"ricevuti {len(payload_parts)}")
        return None

    try:
        values = [t(v) for t, v in zip(schema["types"], payload_parts)]
    except ValueError as e:
        print(f"[parser] tipo {msg_type}: conversione fallita - {e}")
        return None

    data = dict(zip(schema["fields"], values))
    return schema["topic"], data


# ---------------------------------------------------------
# PRODUCER: dati randomici (per test senza hardware)
# Genera frame di tutti e 4 i tipi in round-robin
# ---------------------------------------------------------
def random_producer(q: queue.Queue):
    print("[random_producer] avviato")
    lat, lon = 43.586374637187404, 13.516547970917285
    i = 0
    while not stop_event.is_set():
        msg_type = i % 4

        if msg_type == 0:
            raw = f"0,{random.randint(0,100)},{random.randint(0,130)}," \
                  f"{random.randint(0,130)},{random.randint(0,70)}"
        elif msg_type == 1:
            lat += (random.random() - 0.5) * 0.00005
            lon += (random.random() - 0.5) * 0.00008
            raw = f"1,{lat:.8f},{lon:.8f}"
        elif msg_type == 2:
            raw = f"2,{random.randint(0,600)},{random.randint(0,30)}," \
                  f"{random.randint(0,100)},{random.randint(-150,150)}," \
                  f"{random.randint(0,65)}"
        else:
            errs = ",".join(str(random.choices([0,1], weights=[95,5])[0]) for _ in range(9))
            raw = f"3,{errs}"

        result = parse_frame(raw)
        if result:
            topic, data = result
            try:
                q.put((topic, data), timeout=2)
                print(f"[random_producer] #{i} tipo={msg_type} -> {topic}")
            except queue.Full:
                print(f"[random_producer] #{i} SCARTATO - coda piena")
        i += 1
        time.sleep(0.5)
    print("[random_producer] uscita")


# ---------------------------------------------------------
# PRODUCER: dati da porta seriale
# ---------------------------------------------------------
def serial_producer(q: queue.Queue, port: str, baud: int):
    print(f"[serial_producer] apertura {port} @ {baud}")
    try:
        ser = serial.Serial(port, baud, timeout=1)
    except serial.SerialException as e:
        print(f"[serial_producer] ERRORE apertura porta: {e}")
        return

    print("[serial_producer] avviato")
    while not stop_event.is_set():
        try:
            raw = ser.readline()
        except serial.SerialException as e:
            print(f"[serial_producer] errore lettura: {e}")
            time.sleep(0.5)
            continue

        if not raw:
            continue

        line = raw.decode("utf-8", errors="replace").strip()
        if not line:
            continue

        result = parse_frame(line)
        if result is None:
            print(f"[serial_producer] frame ignorato: {repr(line)}")
            continue

        topic, data = result
        try:
            q.put((topic, data), timeout=2)
        except queue.Full:
            print("[serial_producer] SCARTATO - coda piena")

    ser.close()
    print("[serial_producer] uscita")


# ---------------------------------------------------------
# PUBLISHER MQTT
# ---------------------------------------------------------
def mqtt_publisher(q: queue.Queue, client: paho.Client):
    print("[mqtt_publisher] avviato")
    i = 0
    while not stop_event.is_set():
        try:
            topic, data = q.get(timeout=1)
        except queue.Empty:
            continue

        i += 1
        result = client.publish(topic, payload=json.dumps(data), qos=1)
        if result.rc != paho.MQTT_ERR_SUCCESS:
            print(f"[mqtt_publisher] #{i} errore publish rc={result.rc}")
        else:
            print(f"[mqtt_publisher] #{i} -> {topic}: {data}")
        q.task_done()
    print("[mqtt_publisher] uscita")


# ---------------------------------------------------------
# SETUP MQTT
# ---------------------------------------------------------
def build_client() -> paho.Client:
    def on_connect(client, userdata, flags, rc, properties=None):
        if rc == 0:
            print("[MQTT] connesso ad AWS IoT Core")
        else:
            print(f"[MQTT] errore connessione rc={rc}")

    client = paho.Client(client_id="publisher_P5", protocol=paho.MQTTv5)
    client.on_connect = on_connect
    client.tls_set(
        ca_certs=PATH_ROOT_CA,
        certfile=PATH_CERT,
        keyfile=PATH_KEY,
        tls_version=mqtt.client.ssl.PROTOCOL_TLSv1_2,
    )
    client.connect(AWS_ENDPOINT, 8883)
    client.loop_start()
    return client


if __name__ == "__main__":
    client = build_client()
    time.sleep(1)

    if MODE == "serial":
        def producer_fn(q):
            serial_producer(q, SERIAL_PORT, SERIAL_BAUD)
    else:
        producer_fn = random_producer

    t_producer  = threading.Thread(target=producer_fn,    args=(data_queue,), daemon=True)
    t_publisher = threading.Thread(target=mqtt_publisher, args=(data_queue, client), daemon=True)

    t_producer.start()
    t_publisher.start()

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n[main] stop...")
        stop_event.set()
        t_producer.join(timeout=3)
        t_publisher.join(timeout=3)
        client.loop_stop()
        client.disconnect()
        print("[main] terminato")