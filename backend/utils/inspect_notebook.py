import json

NOTEBOOK_PATH = r"C:\Football_Project\YOLO_training\ball_tracking\ball_event_features.ipynb"

with open(
    NOTEBOOK_PATH,
    "r",
    encoding="utf-8"
) as f:
    notebook = json.load(f)

cells = notebook["cells"]

print("=" * 80)
print("NOTEBOOK INSPECTION")
print("=" * 80)

print(f"\nNotebook: {NOTEBOOK_PATH}")
print(f"Total cells: {len(cells)}")

for i, cell in enumerate(cells):

    cell_type = cell.get("cell_type", "unknown")

    source = "".join(
        cell.get("source", [])
    )

    print("\n" + "=" * 80)
    print(f"CELL {i} | TYPE: {cell_type}")
    print("=" * 80)

    print(source)

print("\n" + "=" * 80)
print("DONE")
print("=" * 80)