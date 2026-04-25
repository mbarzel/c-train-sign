"""
C Train countdown display — Adafruit Matrix Portal S3 + 64x32 HUB75 panel.

Layout:
  Row 1  y=4   "C train in..."   (light pink, small)
  Row 2  y=17  "8  18  24  49"   (hot pink, 4 numbers spread across display)
  Row 3  y=29  "minutes"          (light pink, small)
"""

import time
import board
import wifi
import socketpool
import adafruit_requests
import adafruit_connection_manager
import displayio
import framebufferio
import rgbmatrix
import terminalio
from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font

try:
    from secrets import secrets
except ImportError:
    raise RuntimeError("secrets.py missing")

POLL_INTERVAL = 30
PINK          = 0xFF1493   # deep hot pink — numbers
PINK_LIGHT    = 0x40E0D0   # turquoise — words
RED           = 0xFF0000

displayio.release_displays()

matrix = rgbmatrix.RGBMatrix(
    width=64, height=32, bit_depth=3,
    rgb_pins=[
        board.MTX_R1, board.MTX_G1, board.MTX_B1,
        board.MTX_R2, board.MTX_G2, board.MTX_B2,
    ],
    addr_pins=[
        board.MTX_ADDRA, board.MTX_ADDRB,
        board.MTX_ADDRC, board.MTX_ADDRD,
    ],
    clock_pin=board.MTX_CLK,
    latch_pin=board.MTX_LAT,
    output_enable_pin=board.MTX_OE,
    doublebuffer=True,
)
display = framebufferio.FramebufferDisplay(matrix, auto_refresh=True)

root = displayio.Group()
display.root_group = root

FONT_SMALL = bitmap_font.load_font("/fonts/4x6.bdf")  # 6px tall — smallest readable font
FONT_NUM   = bitmap_font.load_font("/fonts/helvB08.bdf")  # bold numbers

# Row 1: header — proportional font fits "C train in..." (~53px) in 64px
header_lbl = label.Label(
    FONT_SMALL, text="C train in...",
    color=PINK_LIGHT,
    anchor_point=(0.5, 0.5),
    anchored_position=(32, 4),
)
root.append(header_lbl)

# Row 2: 4 numbers spread across display
num_labels = []
for x in (8, 24, 40, 56):
    lbl = label.Label(
        FONT_NUM, text="",
        color=PINK,
        anchor_point=(0.5, 0.5),
        anchored_position=(x, 16),
    )
    num_labels.append(lbl)
    root.append(lbl)

# Row 3: footer
footer_lbl = label.Label(
    FONT_SMALL, text="minutes",
    color=PINK_LIGHT,
    anchor_point=(0.5, 0.5),
    anchored_position=(32, 27),
)
root.append(footer_lbl)

# Wi-Fi
header_lbl.text = "connecting..."
print("Connecting to Wi-Fi:", secrets["ssid"])
wifi.radio.connect(secrets["ssid"], secrets["password"])
print("Connected. IP:", wifi.radio.ipv4_address)
pool     = adafruit_connection_manager.get_radio_socketpool(wifi.radio)
ssl_ctx  = adafruit_connection_manager.get_radio_ssl_context(wifi.radio)
requests = adafruit_requests.Session(pool, ssl_ctx)
header_lbl.text = "C train in..."

def render(arrivals, error=False):
    if error:
        header_lbl.text  = "no data"
        header_lbl.color = RED
        for lbl in num_labels:
            lbl.text = ""
        footer_lbl.text = ""
        return
    header_lbl.text  = "C train in..."
    header_lbl.color = PINK_LIGHT
    footer_lbl.text  = "minutes" if arrivals else ""
    for i, lbl in enumerate(num_labels):
        lbl.text = str(arrivals[i]) if i < len(arrivals) else ""

def fetch_arrivals():
    r = requests.get(secrets["server_url"], timeout=10)
    data = r.json()
    r.close()
    return data

while True:
    try:
        arrivals = fetch_arrivals()
        print("Arrivals (min):", arrivals)
        render(arrivals)
    except Exception as e:
        print("Error:", e)
        render([], error=True)
    time.sleep(POLL_INTERVAL)
