#!/usr/bin/env python3
"""Helper script to parse playwright-cli eval output and save to file."""
import sys
import json
import re

def main():
    output_file = sys.argv[1]
    raw = sys.stdin.read()
    
    # Find the JSON string after "### Result"
    match = re.search(r'### Result\n\n(.*?)\n### Ran Playwright code', raw, re.DOTALL)
    if not match:
        # Try alternative: everything after "### Result" until end
        match = re.search(r'### Result\n\n(.*)', raw, re.DOTALL)
    
    if match:
        json_str = match.group(1).strip()
        try:
            parsed = json.loads(json_str)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(parsed)
            print(f"Saved {len(parsed)} chars to {output_file}")
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print(f"First 200 chars: {json_str[:200]}")
    else:
        print("Could not find Result section")

if __name__ == '__main__':
    main()
