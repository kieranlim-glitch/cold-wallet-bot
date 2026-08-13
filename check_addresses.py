"""
Reads addresses.csv and validates each address against its network's
expected format using address_validators.py. Also flags any address
string that appears under more than one network_id — almost always
a copy-paste mistake, not a legitimate case.
"""

import csv
import sys
from collections import defaultdict
from address_validators import validate_address


def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "addresses.csv"

    results = []
    address_to_networks = defaultdict(list)

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            symbol = row["symbol"]
            network_id = row["network_id"]
            address = row["address"]
            try:
                ok = validate_address(network_id, address)
            except ValueError as e:
                ok = None
                print(f"WARNING: {e}")
            results.append((symbol, network_id, address, ok))
            address_to_networks[address].append((symbol, network_id))

    print(f"\n{'Symbol':<8}{'Network':<14}{'Status':<10}Address")
    print("-" * 90)
    invalid_count = 0
    for symbol, network_id, address, ok in results:
        if ok is None:
            status = "NO VALIDATOR"
        elif ok:
            status = "VALID"
        else:
            status = "INVALID"
            invalid_count += 1
        print(f"{symbol:<8}{network_id:<14}{status:<10}{address}")

    print("-" * 90)
    print(f"{invalid_count} invalid address(es) out of {len(results)} total.")

    duplicate_issues = 0
    for address, entries in address_to_networks.items():
        distinct_networks = {net for _, net in entries}
        if len(distinct_networks) > 1:
            duplicate_issues += 1
            names = ", ".join(f"{sym} ({net})" for sym, net in entries)
            print(f"\nDUPLICATE ADDRESS across chains: {address}")
            print(f"  Used by: {names}")

    if duplicate_issues:
        print(f"\n{duplicate_issues} address(es) duplicated across different networks.")

    if invalid_count > 0 or duplicate_issues > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
```

**File 4 — `requirements.txt`**
```
