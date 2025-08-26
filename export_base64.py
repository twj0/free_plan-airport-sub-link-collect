import base64
import os
import sys
import yaml

# Paths
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
MERGED_FILE = os.path.join(PROJECT_ROOT, 'merged_subscription.yaml')
OUTPUT_FILE = os.path.join(PROJECT_ROOT, 'base64.txt')


def read_text(path: str) -> str:
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def write_text(path: str, content: str) -> None:
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def to_base64(text: str) -> str:
    # Encode to base64 without newlines
    return base64.b64encode(text.encode('utf-8')).decode('utf-8')


def main() -> int:
    if not os.path.exists(MERGED_FILE):
        print(f"Error: '{MERGED_FILE}' not found. Please generate it first (e.g., `python main.py weekly`).")
        return 1

    # Load YAML
    raw = read_text(MERGED_FILE)
    try:
        data = yaml.safe_load(raw) or {}
    except Exception:
        # If YAML parse fails, fall back to encoding the entire file content
        b64 = to_base64(raw)
        write_text(OUTPUT_FILE, b64)
        print(f"Wrote base64 of raw content to: {OUTPUT_FILE}")
        return 0

    # Prefer encoding only the proxies section if present; otherwise encode entire YAML
    if isinstance(data, dict) and 'proxies' in data and isinstance(data['proxies'], list):
        # Dump proxies list to a compact YAML string
        proxies_yaml = yaml.dump({'proxies': data['proxies']}, sort_keys=False, allow_unicode=True, default_flow_style=False)
        b64 = to_base64(proxies_yaml)
        write_text(OUTPUT_FILE, b64)
        print(f"Wrote base64 of proxies section to: {OUTPUT_FILE}")
        return 0
    else:
        b64 = to_base64(raw)
        write_text(OUTPUT_FILE, b64)
        print(f"Wrote base64 of full file to: {OUTPUT_FILE}")
        return 0


if __name__ == '__main__':
    sys.exit(main())
