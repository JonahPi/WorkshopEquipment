import machine
import neopixel
import network
import time
from umqtt.robust import MQTTClient
from secrets import WIFI_SSID, WIFI_PASSWORD, AIO_USERNAME, AIO_KEY

AIO_HOST   = "io.adafruit.com"
AIO_PORT   = 1883
MQTT_TOPIC = "{}/feeds/workshop.box".format(AIO_USERNAME).encode()

NEOPIXEL_CONFIG = {
    1: [0, 1],
    2: [2, 3],
    3: [4, 5],
    4: [6, 7],
    5: [8, 9],
}

PIXEL_PIN        = machine.Pin(2, machine.Pin.OUT)
NUM_PIXELS       = 10
AUTO_OFF_SECONDS = 10

strip = neopixel.NeoPixel(PIXEL_PIN, NUM_PIXELS)


def all_off():
    strip.fill((0, 0, 0))
    strip.write()


def highlight_box(box_nr):
    strip.fill((0, 0, 0))
    if box_nr in NEOPIXEL_CONFIG:
        for px in NEOPIXEL_CONFIG[box_nr]:
            strip[px] = (0, 255, 0)
    strip.write()


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        while not wlan.isconnected():
            time.sleep(0.5)
    print("WiFi connected:", wlan.ifconfig()[0])


lit_until = 0


def on_message(topic, payload):
    global lit_until
    try:
        box_nr = int(payload.decode().strip())
    except ValueError:
        print("Ignoring non-integer payload:", payload)
        return

    print("box_nr received:", box_nr)
    if box_nr == 0:
        all_off()
        lit_until = 0
    else:
        highlight_box(box_nr)
        lit_until = time.time() + AUTO_OFF_SECONDS if AUTO_OFF_SECONDS else 0


connect_wifi()
all_off()

client = MQTTClient(
    client_id="esp8266-workshop",
    server=AIO_HOST,
    port=AIO_PORT,
    user=AIO_USERNAME,
    password=AIO_KEY,
    keepalive=30,
)
client.set_callback(on_message)
client.connect()
client.subscribe(MQTT_TOPIC)
print("Subscribed to", MQTT_TOPIC.decode())

while True:
    client.check_msg()

    if AUTO_OFF_SECONDS and lit_until and time.time() >= lit_until:
        all_off()
        lit_until = 0

    time.sleep(0.1)
