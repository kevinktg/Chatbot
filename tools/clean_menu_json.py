import json
import argparse
from typing import Any, Dict, List, Set, Tuple


def clean_menu_json(input_path: str, output_path: str) -> None:
    """
    Load a JSON array of menu items, clean and standardize fields, and write to output_path.

    Cleaning rules:
      - Drop items missing item_code or item_name
      - Drop duplicate (item_code, item_name) pairs
      - Standardize item_name: trimmed and Title Case
      - Standardize primary_dietary_flag: upper-case and remove spaces
      - Standardize all_dietary_flags: Title Case and replace '-' with ' '

    Args:
        input_path: Path to the input JSON file containing an array of objects
        output_path: Path to write the cleaned JSON array
    """
    with open(input_path, "r", encoding="utf-8") as f:
        data: List[Dict[str, Any]] = json.load(f)

    cleaned: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, str]] = set()

    for item in data:
        # Defensive: ensure dict-like
        if not isinstance(item, dict):
            continue

        code = item.get("item_code")
        name = item.get("item_name")

        if not code or not name:
            # Skip items missing essential identifiers
            continue

        pair = (str(code), str(name))
        if pair in seen:
            # Skip duplicates
            continue
        seen.add(pair)

        # Standardize fields
        name_str = str(name).strip().title()
        item["item_name"] = name_str

        if item.get("primary_dietary_flag") is not None:
            item["primary_dietary_flag"] = (
                str(item["primary_dietary_flag"]).upper().replace(" ", "")
            )

        if item.get("all_dietary_flags") is not None:
            item["all_dietary_flags"] = (
                str(item["all_dietary_flags"]).title().replace("-", " ")
            )

        cleaned.append(item)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, indent=2, ensure_ascii=False)

    print(f"Cleaned data: {len(cleaned)} menu items written to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clean and standardize menu JSON data."
    )
    parser.add_argument(
        "-i",
        "--input",
        default="gf2025-main.json",
        help="Path to input JSON file (default: gf2025-main.json)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="gf2025-cleaned.json",
        help="Path to output cleaned JSON file (default: gf2025-cleaned.json)",
    )

    args = parser.parse_args()
    clean_menu_json(args.input, args.output)


if __name__ == "__main__":
    main()