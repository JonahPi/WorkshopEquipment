import machine
import neopixel
import network
import time
from umqtt.robust import MQTTClient
from secrets import WIFI_SSID, WIFI_PASSWORD, AIO_USERNAME, AIO_KEY

AIO_HOST   = "io.adafruit.com"
AIO_PORT   = 1883
MQTT_TOPIC = "{}/feeds/workshop.box".format(AIO_USERNAME).encode()

# D8 on ESP8266 = GPIO15
PIXEL_PIN      = machine.Pin(15, machine.Pin.OUT)
NUM_PIXELS     = 443          # max 0-based index is 442
BLINK_DURATION = 10           # seconds to blink after MQTT message
BLINK_INTERVAL = 0.4          # seconds per on/off toggle
STARTUP_DELAY  = 0.05         # seconds each box is lit during startup sweep
PING_INTERVAL  = 15           # seconds between MQTT keepalive pings

# Pixel indices are 0-based (original C++ config was 1-based; all values -1).
BOX_CONFIG = [
    [],                         # 0 — unused
    [0, 1],                     # 1
    [2, 3],
    [6, 7],
    [10, 11],
    [14, 15],
    [16, 17],
    [20, 21],
    [24, 25],
    [28, 29],
    [30, 31],                   # 10
    [34, 35],
    [38, 39],
    [42, 43],
    [44, 45],
    [48, 49],
    [52, 53],
    [56, 57],
    [58, 59],
    [62, 63],
    [66, 67],                   # 20
    [70, 71],
    [72, 73],
    [76, 77],
    [80, 81],
    [84, 85],
    [86, 87],
    [90, 91],
    [94, 95],
    [98, 99],
    [100, 101],                 # 30
    [104, 105],
    [108, 109],
    [112, 113],
    [114, 115],
    [118, 119],
    [122, 123],
    [126, 127],
    [128, 129],
    [130, 131],
    [134, 135],                 # 40
    [138, 139],
    [142, 143],
    [144, 145],
    [148, 149],
    [152, 153],
    [156, 157],
    [158, 159],
    [162, 163],
    [166, 167],
    [170, 171],                 # 50
    [172, 173],
    [175, 176],
    [177, 178],
    [181, 182],
    [183, 184],
    [187, 188],
    [191, 192],
    [195, 196],
    [197, 198],
    [201, 202],                 # 60
    [205, 206],
    [209, 210],
    [211, 212],
    [215, 216],
    [219, 220],
    [223, 224],
    [225, 226],
    [229, 230],
    [233, 234],
    [237, 238],                 # 70
    [239, 240],
    [243, 244],
    [247, 248],
    [251, 252],
    [254, 253],
    [260, 259],
    [266, 265],
    [268, 267],
    [274, 273],
    [280, 279],                 # 80
    [282, 281],
    [288, 287],
    [294, 293],
    [425],                      # 84
    [425, 426],
    [425, 426, 427],
    [428],
    [428, 429],
    [428, 429, 430],
    [431],                      # 90
    [431, 432],
    [431, 432, 433],
    [434],
    [434, 435],
    [434, 435, 436],
    [437],
    [437, 438],
    [437, 438, 439],
    [440],
    [440, 441],                 # 100
    [440, 441, 442],
    [298, 299, 302, 303],       # 102
    [308, 309],
    [311, 312],
    [316, 317],
    [319, 320],
    [321, 322],
    [324, 325],
    [329, 330],
    [332, 333],                 # 110
    [334, 335],
    [337, 338],
    [342, 343],
    [345, 346],
    [347, 348],
    [350, 351],
    [355, 356],
    [358, 359],
    [360, 361],
    [363, 364],                 # 120
    [368, 369],
    [371, 372],
    [373, 374],
    [376, 377],
    [381, 382],
    [385, 384],
    [386, 387],
    [389, 390],
    [394, 395],
    [397, 398],                 # 130
    [399, 400],
    [402, 403],
    [407, 408],
    [410, 411],
    [412, 413],
    [415, 416],
    [420, 421],                 # 137
    [423, 424],                 # 138
]

strip = neopixel.NeoPixel(PIXEL_PIN, NUM_PIXELS)


def all_off():
    strip.fill((0, 0, 0))
    strip.write()


def set_box(box_nr, color):
    if 0 < box_nr < len(BOX_CONFIG):
        for px in BOX_CONFIG[box_nr]:
            strip[px] = color
    strip.write()


def startup_sweep():
    for box_nr in range(1, len(BOX_CONFIG)):
        if BOX_CONFIG[box_nr]:
            all_off()
            set_box(box_nr, (0, 255, 0))
            time.sleep(STARTUP_DELAY)
    all_off()


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        while not wlan.isconnected():
            time.sleep(0.5)
    print("WiFi connected:", wlan.ifconfig()[0])


# ── Blink state ───────────────────────────────────────────────────────────────
blink_box    = 0
blink_until  = 0
blink_toggle = 0
blink_on     = False


def on_message(topic, payload):
    global blink_box, blink_until, blink_toggle, blink_on
    try:
        box_nr = int(payload.decode().strip())
    except ValueError:
        print("Ignoring non-integer payload:", payload)
        return

    print("box_nr received:", box_nr)
    all_off()
    if box_nr == 0:
        blink_box = 0
    else:
        blink_box    = box_nr
        blink_until  = time.time() + BLINK_DURATION
        blink_toggle = time.time()
        blink_on     = True
        set_box(blink_box, (0, 255, 0))


def mqtt_connect():
    client.connect()
    client.subscribe(MQTT_TOPIC)
    print("Subscribed to", MQTT_TOPIC.decode())


# ── Startup ───────────────────────────────────────────────────────────────────
connect_wifi()
startup_sweep()

client = MQTTClient(
    client_id="esp8266-neopixel",
    server=AIO_HOST,
    port=AIO_PORT,
    user=AIO_USERNAME,
    password=AIO_KEY,
    keepalive=60,
)
client.set_callback(on_message)
mqtt_connect()

# ── Main loop ─────────────────────────────────────────────────────────────────
last_ping = time.time()

while True:
    try:
        client.check_msg()

        now = time.time()

        # Periodic ping to keep the broker connection alive
        if now - last_ping >= PING_INTERVAL:
            client.ping()
            last_ping = now

        # Blink state machine
        if blink_box:
            if now >= blink_until:
                all_off()
                blink_box = 0
            elif now >= blink_toggle:
                blink_on = not blink_on
                set_box(blink_box, (0, 255, 0) if blink_on else (0, 0, 0))
                blink_toggle = now + BLINK_INTERVAL

    except Exception as e:
        print("MQTT error:", e, "— reconnecting in 5 s")
        time.sleep(5)
        try:
            mqtt_connect()
            last_ping = time.time()
        except Exception as e2:
            print("Reconnect failed:", e2)

    time.sleep(0.05)
