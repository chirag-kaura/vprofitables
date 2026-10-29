import json

with open("tests/torture_100_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Total Tested: {data['total']} | Passed: {data['passed']} | Failed: {data['failed']}")
print("=" * 80)
for fail in data["failures"]:
    print(f"ID {fail['id']:03d} [{fail['category']}]: '{fail['query']}'")
    for r in fail["fail_reasons"]:
        print(f"   -> {r}")
    if fail.get("missing_tool"):
        print(f"   Missing Tool / Capability Needed: {fail['missing_tool']}")
    print("-" * 80)
