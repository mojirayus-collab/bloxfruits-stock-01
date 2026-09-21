import os
import json
import hashlib
from datetime import datetime, timezone

import requests


# ============================================================
# CONFIG
# ============================================================

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "").strip()

# Public Blox Fruits Stock API
STOCK_API_URL = (
    "https://blox-fruits-api.onrender.com/api/bloxfruits/stock"
)

# ไฟล์เก็บ stock ล่าสุดที่เคยส่ง
LAST_STOCK_FILE = "last_stock.json"

REQUEST_TIMEOUT = 20


# ============================================================
# FRUIT EMOJI
# ============================================================

FRUIT_EMOJIS = {
    "Rocket": "🚀",
    "Spin": "🌀",
    "Blade": "⚔️",
    "Bomb": "💣",
    "Smoke": "💨",
    "Spike": "🌵",
    "Flame": "🔥",
    "Falcon": "🦅",
    "Ice": "❄️",
    "Sand": "🏜️",
    "Dark": "🌑",
    "Diamond": "💎",
    "Light": "✨",
    "Rubber": "🟣",
    "Barrier": "🛡️",
    "Ghost": "👻",
    "Magma": "🌋",
    "Door": "🚪",
    "Quake": "🌊",
    "Buddha": "🗿",
    "Love": "💕",
    "Spider": "🕷️",
    "Sound": "🔊",
    "Phoenix": "🔥",
    "Portal": "🌀",
    "Rumble": "⚡",
    "Pain": "💥",
    "Blizzard": "❄️",
    "Gravity": "🌌",
    "Mammoth": "🐘",
    "T-Rex": "🦖",
    "Dough": "🍩",
    "Shadow": "🌑",
    "Venom": "☠️",
    "Control": "🎮",
    "Spirit": "👻",
    "Leopard": "🐆",
    "Kitsune": "🦊",
    "Dragon": "🐉",
}


# ============================================================
# DISCORD
# ============================================================

def send_discord_message(content=None, embed=None):
    """
    ส่งข้อความไป Discord Webhook
    """

    if not DISCORD_WEBHOOK_URL:
        print("ERROR: ไม่พบ DISCORD_WEBHOOK_URL")
        return False

    payload = {}

    if content:
        payload["content"] = content

    if embed:
        payload["embeds"] = [embed]

    try:
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code in (200, 204):
            print("ส่งข้อความเข้า Discord สำเร็จ")
            return True

        print(
            f"Discord webhook error: "
            f"{response.status_code} - {response.text}"
        )

        return False

    except requests.RequestException as e:
        print(f"Discord connection error: {e}")
        return False


# ============================================================
# LOAD / SAVE LAST STOCK
# ============================================================

def load_last_stock():
    """
    โหลด stock ครั้งล่าสุดที่เคยส่ง
    """

    if not os.path.exists(LAST_STOCK_FILE):
        return None

    try:
        with open(LAST_STOCK_FILE, "r", encoding="utf-8") as file:
            return json.load(file)

    except Exception as e:
        print(f"ไม่สามารถอ่าน {LAST_STOCK_FILE}: {e}")
        return None


def save_last_stock(stock):
    """
    บันทึก stock ล่าสุด
    """

    try:
        with open(
            LAST_STOCK_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                stock,
                file,
                ensure_ascii=False,
                indent=2
            )

    except Exception as e:
        print(f"ไม่สามารถบันทึก stock: {e}")


# ============================================================
# STOCK HASH
# ============================================================

def stock_hash(stock):
    """
    สร้าง hash เพื่อดูว่า stock เปลี่ยนหรือยัง
    """

    data = json.dumps(
        stock,
        sort_keys=True,
        ensure_ascii=False
    )

    return hashlib.sha256(
        data.encode("utf-8")
    ).hexdigest()


# ============================================================
# FETCH STOCK
# ============================================================

def fetch_stock():
    """
    ดึง stock จาก Public Blox Fruits API
    """

    print("กำลังดึง Blox Fruits stock...")

    try:
        response = requests.get(
            STOCK_API_URL,
            timeout=REQUEST_TIMEOUT,
            headers={
                "User-Agent": "BloxFruits-Discord-Stock-Bot/1.0"
            }
        )

        print(
            f"Stock API status: {response.status_code}"
        )

        response.raise_for_status()

        data = response.json()

        # API เก่านี้มีโอกาสคืน JSON ซ้อนมาเป็น string
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                pass

        return data

    except requests.RequestException as e:
        print(f"ไม่สามารถเชื่อมต่อ Stock API ได้: {e}")
        return None

    except ValueError as e:
        print(f"Stock API ไม่ได้ส่ง JSON ที่ถูกต้อง: {e}")
        return None


# ============================================================
# NORMALIZE STOCK
# ============================================================

def normalize_stock(data):
    """
    พยายามรองรับรูปแบบ JSON หลายแบบ
    """

    if not isinstance(data, dict):
        return None

    # รูปแบบที่คาดหวัง
    if "normal" in data or "mirage" in data:
        return {
            "normal": data.get("normal", []),
            "mirage": data.get("mirage", [])
        }

    # API บางตัวอาจห่อข้อมูลด้วย data
    if isinstance(data.get("data"), dict):

        inner = data["data"]

        if "normal" in inner or "mirage" in inner:
            return {
                "normal": inner.get("normal", []),
                "mirage": inner.get("mirage", [])
            }

    # รูปแบบอื่นที่อาจใช้ normal_stock / mirage_stock
    normal = (
        data.get("normal_stock")
        or data.get("normalStock")
        or data.get("Normal")
    )

    mirage = (
        data.get("mirage_stock")
        or data.get("mirageStock")
        or data.get("Mirage")
    )

    if normal is not None or mirage is not None:
        return {
            "normal": normal or [],
            "mirage": mirage or []
        }

    return None


# ============================================================
# FORMAT PRICE
# ============================================================

def format_price(value):
    """
    แปลงราคาให้อ่านง่าย
    """

    if value is None:
        return "ไม่ระบุ"

    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return str(value)


# ============================================================
# GET FRUIT NAME
# ============================================================

def get_fruit_name(item):
    """
    รองรับ field ชื่อผลไม้หลายแบบ
    """

    if not isinstance(item, dict):
        return str(item)

    return (
        item.get("name")
        or item.get("fruit")
        or item.get("fruit_name")
        or item.get("Name")
        or "Unknown"
    )


# ============================================================
# GET FRUIT PRICE
# ============================================================

def get_beli_price(item):
    if not isinstance(item, dict):
        return None

    return (
        item.get("price_beli")
        or item.get("money_price")
        or item.get("price")
        or item.get("beli")
        or item.get("Beli")
    )


def get_robux_price(item):
    if not isinstance(item, dict):
        return None

    return (
        item.get("price_robux")
        or item.get("robux_price")
        or item.get("robux")
        or item.get("Robux")
    )


# ============================================================
# FORMAT STOCK LIST
# ============================================================

def format_stock_list(items):

    if not items:
        return "ไม่มีข้อมูล"

    lines = []

    for item in items:

        name = get_fruit_name(item)

        emoji = FRUIT_EMOJIS.get(
            name,
            "🍎"
        )

        beli = get_beli_price(item)
        robux = get_robux_price(item)

        line = f"{emoji} **{name}**"

        if beli is not None:
            line += f"\n💰 Beli: `{format_price(beli)}`"

        if robux is not None:
            line += f"\n💎 Robux: `{format_price(robux)}`"

        lines.append(line)

    return "\n\n".join(lines)


# ============================================================
# CREATE DISCORD EMBED
# ============================================================

def create_stock_embed(stock):

    normal = stock.get("normal", [])
    mirage = stock.get("mirage", [])

    now = datetime.now(timezone.utc)

    normal_text = format_stock_list(normal)
    mirage_text = format_stock_list(mirage)

    embed = {
        "title": "🍎 Blox Fruits Stock",
        "description": (
            "📦 **Current Blox Fruits Dealer Stock**\n"
            "ตรวจสอบ stock ล่าสุดจากระบบอัตโนมัติ"
        ),
        "fields": [
            {
                "name": "🏪 NORMAL DEALER",
                "value": normal_text[:1024],
                "inline": False
            },
            {
                "name": "🌫️ MIRAGE DEALER",
                "value": mirage_text[:1024],
                "inline": False
            }
        ],
        "footer": {
            "text": (
                "Blox Fruits Stock Bot • "
                f"Updated {now.strftime('%Y-%m-%d %H:%M:%S')} UTC"
            )
        }
    }

    return embed


# ============================================================
# ERROR EMBED
# ============================================================

def create_error_embed(message):

    return {
        "title": "⚠️ Blox Fruits Stock Error",
        "description": message,
        "footer": {
            "text": "Blox Fruits Stock Bot"
        }
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("Blox Fruits Stock Discord Bot")
    print("=" * 60)

    # --------------------------------------------------------
    # Check webhook
    # --------------------------------------------------------

    if not DISCORD_WEBHOOK_URL:

        print(
            "ERROR: "
            "กรุณาตั้งค่า DISCORD_WEBHOOK_URL"
        )

        return

    # --------------------------------------------------------
    # Fetch
    # --------------------------------------------------------

    raw_data = fetch_stock()

    if raw_data is None:

        print("ไม่สามารถดึง stock ได้")

        send_discord_message(
            embed=create_error_embed(
                "❌ ไม่สามารถดึงข้อมูล Blox Fruits Stock ได้\n"
                "Stock API อาจล่มหรือไม่ตอบสนอง"
            )
        )

        return

    # --------------------------------------------------------
    # Normalize
    # --------------------------------------------------------

    stock = normalize_stock(raw_data)

    if stock is None:

        print("ไม่รู้จักรูปแบบข้อมูล API")

        print("RAW DATA:")
        print(
            json.dumps(
                raw_data,
                ensure_ascii=False,
                indent=2
            )[:5000]
        )

        send_discord_message(
            embed=create_error_embed(
                "❌ API ตอบข้อมูลมา แต่รูปแบบข้อมูลไม่ตรงกับที่ระบบรองรับ"
            )
        )

        return

    # --------------------------------------------------------
    # Check empty
    # --------------------------------------------------------

    if not stock["normal"] and not stock["mirage"]:

        print("Stock ว่าง")

        send_discord_message(
            embed=create_error_embed(
                "⚠️ API ตอบกลับมา แต่ไม่พบ stock"
            )
        )

        return

    # --------------------------------------------------------
    # Compare previous stock
    # --------------------------------------------------------

    previous = load_last_stock()

    current_hash = stock_hash(stock)

    previous_hash = (
        stock_hash(previous)
        if previous
        else None
    )

    print(
        f"Current hash : {current_hash}"
    )

    print(
        f"Previous hash: {previous_hash}"
    )

    # --------------------------------------------------------
    # Send only when changed
    # --------------------------------------------------------

    if previous_hash == current_hash:

        print(
            "Stock ยังไม่เปลี่ยน "
            "ไม่ส่ง Discord ซ้ำ"
        )

        return

    # --------------------------------------------------------
    # Create embed
    # --------------------------------------------------------

    embed = create_stock_embed(stock)

    # --------------------------------------------------------
    # Send Discord
    # --------------------------------------------------------

    success = send_discord_message(
        embed=embed
    )

    # --------------------------------------------------------
    # Save only after successful send
    # --------------------------------------------------------

    if success:

        save_last_stock(stock)

        print(
            "บันทึก stock ใหม่เรียบร้อย"
        )

    print("=" * 60)
    print("ทำงานเสร็จแล้ว")
    print("=" * 60)


if __name__ == "__main__":
    main()
