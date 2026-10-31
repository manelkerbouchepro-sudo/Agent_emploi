"""Importe ta liste d'entreprises (fichier Excel, onglet « Toutes ») dans cibles.json.

Usage : python importer_liste.py "Entreprises_Stage_Alternance_France.xlsx"

Garde Nancy / Metz, Strasbourg et Paris, les domaines logiciel, IA, électronique, automatisme,
mécatronique et robotique, retire les ESN, puis classe chaque entreprise en A, B ou C
(règles dans agent/targets.py). Relance-le après avoir modifié le fichier Excel.
"""
import collections
import json
import sys

import openpyxl

from agent import targets


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    cfg = json.load(open("config.json", encoding="utf-8"))
    wb = openpyxl.load_workbook(sys.argv[1], read_only=True, data_only=True)
    if "Toutes" not in wb.sheetnames:
        sys.exit(f"Onglet « Toutes » introuvable. Onglets présents : {', '.join(wb.sheetnames)}")
    cibles = targets.from_rows(wb["Toutes"].iter_rows(min_row=2, values_only=True), cfg)
    with open("cibles.json", "w", encoding="utf-8") as f:
        json.dump(cibles, f, ensure_ascii=False, indent=1)
    n = collections.Counter(c["priorite"] for c in cibles)
    print(f"cibles.json : {len(cibles)} entreprises (A : {n['A']}, B : {n['B']}, C : {n['C']})")


if __name__ == "__main__":
    main()
