import json

path = r"C:\Football_Project\YOLO_training\ball_tracking\ball_event_features.ipynb"

with open(path, "r", encoding="utf-8") as f:
    notebook = json.load(f)

print("TOTAL CELLS:", len(notebook["cells"]))

for i, cell in enumerate(notebook["cells"]):

    print("\n" + "=" * 80)
    print(f"CELL {i} | TYPE: {cell['cell_type']}")
    print("=" * 80)

    source = "".join(cell["source"])

    print(source[:4000])