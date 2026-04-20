import machine
import network
import time
from umqtt.robust import MQTTClient
from secrets import WIFI_SSID, WIFI_PASSWORD, AIO_USERNAME, AIO_KEY

# ── Pins ──────────────────────────────────────────────────────────────────────
ser       = machine.Pin(21, machine.Pin.OUT)
rclk      = machine.Pin(17, machine.Pin.OUT)
srclk     = machine.Pin(16, machine.Pin.OUT)
led       = machine.Pin(22, machine.Pin.OUT)
x_endstop = machine.Pin(36, machine.Pin.IN)
y_endstop = machine.Pin(35, machine.Pin.IN)

# ── Shift register bit assignments ────────────────────────────────────────────
DISABLE_BIT   = 0
PAN_STEP_BIT  = 1
PAN_DIR_BIT   = 2
Z_STEP_BIT    = 3
Z_DIR_BIT     = 4
TILT_STEP_BIT = 5
TILT_DIR_BIT  = 6
BEEPER_BIT    = 7

# ── Motion constants ──────────────────────────────────────────────────────────
X_MAXSTEPS           = 7700
Y_MAXSTEPS           = 4200
FASTMOVE             = 500    # µs between steps (long moves)
SLOMOVE              = 3000   # µs between steps (short moves)
LEDONDELAY           = 20000  # ms to keep LED active after movement stops
KEEP_STEPPER_ENGAGED = 30     # seconds before disabling stepper (saves heat)

# ── MQTT ──────────────────────────────────────────────────────────────────────
AIO_HOST   = "io.adafruit.com"
AIO_PORT   = 1883
MQTT_TOPIC = "{}/feeds/workshop.laser".format(AIO_USERNAME).encode()

# ── State ─────────────────────────────────────────────────────────────────────
shift_state              = 0
tilt_position            = 0
pan_position             = 0
tilt_target              = 0
pan_target               = 0
led_active               = False
motor_moving             = False
led_start_ms             = 0
stepper_engaged_until_ms = 0


# ── Shift register ────────────────────────────────────────────────────────────
def send_shift():
    rclk.value(0)
    for i in range(7, -1, -1):
        srclk.value(0)
        ser.value((shift_state >> i) & 1)
        srclk.value(1)
        time.sleep_us(10)
    rclk.value(1)


def set_bit(bit, state):
    global shift_state
    if state:
        shift_state |= (1 << bit)
    else:
        shift_state &= ~(1 << bit)
    send_shift()


# ── Stepper motion ────────────────────────────────────────────────────────────
def tilt_to(target):
    global tilt_position
    set_bit(TILT_DIR_BIT, target > tilt_position)
    steps    = abs(target - tilt_position)
    delay_us = FASTMOVE if steps > 400 else SLOMOVE
    for _ in range(steps):
        set_bit(TILT_STEP_BIT, True)
        time.sleep_us(delay_us)
        set_bit(TILT_STEP_BIT, False)
        time.sleep_us(delay_us)
    tilt_position = target


def pan_to(target):
    global pan_position
    forward = target > pan_position
    set_bit(PAN_DIR_BIT, forward)
    set_bit(TILT_DIR_BIT, not forward)   # mechanically coupled — must move opposite
    steps    = abs(target - pan_position)
    delay_us = FASTMOVE if steps > 400 else SLOMOVE
    for _ in range(steps):
        set_bit(PAN_STEP_BIT, True)
        set_bit(TILT_STEP_BIT, True)
        time.sleep_us(delay_us)
        set_bit(PAN_STEP_BIT, False)
        set_bit(TILT_STEP_BIT, False)
        time.sleep_us(delay_us)
    pan_position = target


def calibrate():
    global pan_position, tilt_position
    led.value(0)
    set_bit(DISABLE_BIT, False)
    # Pan home: move until X endstop triggers
    set_bit(PAN_DIR_BIT, False)
    set_bit(TILT_DIR_BIT, True)
    while x_endstop.value():
        set_bit(PAN_STEP_BIT, True)
        set_bit(TILT_STEP_BIT, True)
        time.sleep_us(FASTMOVE)
        set_bit(PAN_STEP_BIT, False)
        set_bit(TILT_STEP_BIT, False)
        time.sleep_us(FASTMOVE)
    pan_position = 0
    # Tilt home: move until Y endstop triggers
    set_bit(TILT_DIR_BIT, False)
    while y_endstop.value():
        set_bit(TILT_STEP_BIT, True)
        time.sleep_us(FASTMOVE)
        set_bit(TILT_STEP_BIT, False)
        time.sleep_us(FASTMOVE)
    set_bit(DISABLE_BIT, True)
    tilt_position = 0


# ── WiFi ──────────────────────────────────────────────────────────────────────
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        while not wlan.isconnected():
            time.sleep(0.5)
    print("WiFi connected:", wlan.ifconfig()[0])


# ── MQTT callback ─────────────────────────────────────────────────────────────
def on_message(topic, payload):
    global pan_target, tilt_target
    msg = payload.decode().strip()
    sep = msg.find('/')
    if sep == -1:
        print("Invalid payload (expected x/y):", msg)
        return
    try:
        pan_target  = min(max(int(msg[:sep]),    0), X_MAXSTEPS)
        tilt_target = min(max(int(msg[sep + 1:]), 0), Y_MAXSTEPS)
    except ValueError:
        print("Non-integer coordinates:", msg)
        return
    print("Target → pan={} tilt={}".format(pan_target, tilt_target))
    if pan_target == 0 and tilt_target == 0:
        calibrate()


# ── Startup ───────────────────────────────────────────────────────────────────
connect_wifi()
set_bit(DISABLE_BIT, True)
calibrate()

client = MQTTClient(
    client_id="esp32-laser",
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


# ── Main loop ─────────────────────────────────────────────────────────────────
while True:
    client.check_msg()
    now = time.ticks_ms()

    # Arm LED timer as soon as new target arrives
    if tilt_target != tilt_position or pan_target != pan_position:
        if not led_active:
            led_active   = True
            led_start_ms = now

    # LED state machine: solid while moving, blinking after stop, off after timeout
    if led_active:
        elapsed = time.ticks_diff(now, led_start_ms)
        if elapsed >= LEDONDELAY:
            led_active = False
            led.value(0)
        elif motor_moving:
            led.value(1)
        else:
            led.value(1 if (elapsed // 300) % 2 == 0 else 0)

    # Re-home if stepper was disengaged since last move
    needs_rehome = time.ticks_diff(now, stepper_engaged_until_ms) > 0

    if tilt_target != tilt_position:
        if needs_rehome:
            calibrate()
        motor_moving = True
        set_bit(DISABLE_BIT, False)
        tilt_to(tilt_target)
        stepper_engaged_until_ms = time.ticks_add(time.ticks_ms(), KEEP_STEPPER_ENGAGED * 1000)
        motor_moving = False

    if pan_target != pan_position:
        if needs_rehome:
            calibrate()
        motor_moving = True
        set_bit(DISABLE_BIT, False)
        pan_to(pan_target)
        stepper_engaged_until_ms = time.ticks_add(time.ticks_ms(), KEEP_STEPPER_ENGAGED * 1000)
        motor_moving = False

    # Disengage stepper coils when idle (reduces heat)
    if time.ticks_diff(time.ticks_ms(), stepper_engaged_until_ms) > 0:
        set_bit(DISABLE_BIT, True)

    if tilt_target == tilt_position and pan_target == pan_position:
        time.sleep_ms(10)
