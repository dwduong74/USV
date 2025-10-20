import re
import json

def parse_command(command: str):
    # Default values
    action = "stop"
    distance = 1.0
    speed = 0.05

    # Normalize to lowercase
    cmd = command.lower()

    # Check multi-word commands first
    if "xoay phải" in cmd or "quay phải" in cmd :
        action = "rotate right"
    elif "xoay trái" in cmd or "quay trái" in cmd :
        action = "rotate left"
    elif "phải" in cmd:
        action = "move right"
    elif "trái" in cmd:
        action = "move left"
    elif "quay lại" in cmd or "quay đầu" in cmd:
        action = "turn around"
    elif any(word in cmd for word in ["lùi", "lùi lại", "đi về sau" ,"sau"]):
        action = "backward"
    elif any(word in cmd for word in ["tiến", "thẳng", "tới", "đi lên", "đi về phía trước"]):
        action = "forward"
    elif any(word in cmd for word in ["dừng", "stop", "đứng lại"]):
        action = "stop"
    else:
        action = "stop"

    match_dist = re.search(r"(\d+(\.\d+)?)\s*(m|mét)?", cmd)
    if match_dist:
        distance = float(match_dist.group(1))

    match_speed = re.search(r"tốc độ\s*(\d+(\.\d+)?)", cmd)
    if match_speed:
        speed = float(match_speed.group(1))

    result = {
        "action": action,
        "distance": distance,
        "speed": speed
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


# Test cases
print(parse_command("đi tới phía bên trái 2m"))

