#!/usr/bin/env python3
"""
Marvel Snap Save Extractor - Tkinter GUI

Inputs:
  - CollectionState.json
  - CharacterMasteryState.json

Features:
  - Auto-load from default SNAP save folder (Windows) when available
  - Choose report (boosters/mastery/variants/albums)
  - Preview in a table
  - Export selected report to CSV
  - Clean UI formatting + default numeric values (no blanks)
"""

from __future__ import annotations

import json
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import pandas as pd


# ----------------------------
# Parsing / data extraction
# ----------------------------

def load_json(path: str):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def extract_boosters(collection_json: dict) -> dict[str, int | None]:
    """
    Returns: { CardDefId: Boosters }
    """
    stats = collection_json["ServerState"]["CardDefStats"]["Stats"]
    boosters: dict[str, int | None] = {}

    for k, v in stats.items():
        if isinstance(k, str) and k.startswith("$"):
            continue
        if isinstance(v, dict) and "Boosters" in v:
            boosters[str(k)] = v.get("Boosters")

    return boosters


def extract_mastery(mastery_json: dict) -> tuple[dict[str, int], dict[str, int]]:
    """
    Returns:
      mastery_level: { CardDefId: int(level) }
      mastery_xp:    { CardDefId: int(experience) }
    """
    char_data = mastery_json["ServerState"]["CharacterMasteryProgress"]["CharacterProgressData"]

    mastery_level: dict[str, int] = {}
    mastery_xp: dict[str, int] = {}

    for k, v in char_data.items():
        if isinstance(k, str) and k.startswith("$"):
            continue
        if not isinstance(v, dict):
            continue

        lvl = v.get("LastClaimedLevel")
        if lvl is not None:
            try:
                mastery_level[str(k)] = int(lvl)
            except Exception:
                pass

        if "Experience" in v:
            try:
                mastery_xp[str(k)] = int(v["Experience"])
            except Exception:
                pass

    return mastery_level, mastery_xp


def merged_boosters_mastery(collection_json: dict, mastery_json: dict) -> pd.DataFrame:
    boosters = extract_boosters(collection_json)
    mastery_level, mastery_xp = extract_mastery(mastery_json)

    all_cards = sorted(set(boosters) | set(mastery_level))
    rows = []
    for card in all_cards:
        rows.append({
            "CardDefId": card,
            "Boosters": boosters.get(card),
            "MasteryLevel": mastery_level.get(card),
            "MasteryXP": mastery_xp.get(card),
        })

    df = pd.DataFrame(rows)

    # Normalize numeric columns for consistent sorting / display
    for col in ["Boosters", "MasteryLevel", "MasteryXP"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Defaults (no blanks)
    # Empty Booster Data Set is 0
    # Default Mastery Level is 1
    # Default Mastery Exp is 0
    df["Boosters"] = df["Boosters"].fillna(0).astype(int)
    df["MasteryLevel"] = df["MasteryLevel"].fillna(1).astype(int)
    df["MasteryXP"] = df["MasteryXP"].fillna(0).astype(int)

    return df


def variants_by_card(collection_json: dict) -> pd.DataFrame:
    cards_list = collection_json["ServerState"]["Cards"]
    variant_map: dict[str, set[str]] = {}

    for c in cards_list:
        if not isinstance(c, dict):
            continue
        card = c.get("CardDefId")
        var = c.get("ArtVariantDefId")
        if not card or not var:
            continue
        variant_map.setdefault(str(card), set()).add(str(var))

    rows = []
    for card, vars_set in variant_map.items():
        rows.append({
            "CardDefId": card,
            "VariantCount": len(vars_set),
            "OwnedVariantIds": "|".join(sorted(vars_set)),
        })

    df = pd.DataFrame(rows)
    df["VariantCount"] = pd.to_numeric(df["VariantCount"], errors="coerce").fillna(0).astype(int)
    return df


def albums_by_completion(collection_json: dict) -> pd.DataFrame:
    cards_list = collection_json["ServerState"]["Cards"]
    owned_variants: set[str] = set()

    for c in cards_list:
        if isinstance(c, dict) and c.get("ArtVariantDefId"):
            owned_variants.add(str(c["ArtVariantDefId"]))

    albums = collection_json["ServerState"].get("AllAlbumData", [])
    rows = []

    for a in albums:
        if not isinstance(a, dict):
            continue
        album_def = a.get("AlbumDef") or {}
        album_id = album_def.get("AlbumDefId")
        album_name = album_def.get("Name") or album_id
        album_vars = album_def.get("AlbumVariants") or []

        # Normalize variant IDs (they may appear as strings or nested dicts)
        norm: list[str] = []
        for av in album_vars:
            if isinstance(av, str):
                norm.append(av)
            elif isinstance(av, dict):
                for key in ("Id", "ArtVariantDefId", "AlbumVariantDefId", "Value"):
                    if key in av and isinstance(av[key], str):
                        norm.append(av[key])
                        break

        total = len(norm)
        if total == 0:
            continue

        owned = sum(1 for v in norm if v in owned_variants)
        needed = total - owned
        pct = (owned / total) * 100 if total else 0

        rows.append({
            "AlbumDefId": album_id,
            "AlbumName": album_name,
            "TotalVariants": total,
            "OwnedVariants": owned,
            "NeededForCompletion": needed,
            "CompletionPct": round(pct, 2),
        })

    df = pd.DataFrame(rows)
    for col in ["TotalVariants", "OwnedVariants", "NeededForCompletion", "CompletionPct"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Fill defaults for cleanliness
    if "TotalVariants" in df.columns:
        df["TotalVariants"] = df["TotalVariants"].fillna(0).astype(int)
    if "OwnedVariants" in df.columns:
        df["OwnedVariants"] = df["OwnedVariants"].fillna(0).astype(int)
    if "NeededForCompletion" in df.columns:
        df["NeededForCompletion"] = df["NeededForCompletion"].fillna(0).astype(int)
    if "CompletionPct" in df.columns:
        df["CompletionPct"] = df["CompletionPct"].fillna(0.0)

    return df


# ----------------------------
# Tkinter GUI
# ----------------------------

REPORTS = [
    "Cards: Boosters (DESC) then Mastery (DESC)",
    "Cards: Boosters (DESC), Max Mastery (30) at Bottom",
    "Cards: Mastery (DESC) then Boosters (DESC)",
    "Cards: Mastery + Boosters (DESC/DESC)",
    "Cards: Mastery + Boosters (DESC/DESC), Max Mastery (30) at Bottom",
    "Variants: Per Card (Most → Least)",
    "Albums: Completion (Most → Least)",
]


class SnapExtractorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Marvel Snap Save Extractor")
        self.geometry("1050x650")

        self.collection_path_var = tk.StringVar()
        self.mastery_path_var = tk.StringVar()
        self.report_var = tk.StringVar(value=REPORTS[0])

        self.collection_json: dict | None = None
        self.mastery_json: dict | None = None
        self.current_df: pd.DataFrame | None = None

        self._build_ui()

        # Try to auto-load default SNAP paths on startup (Windows)
        self.try_autoload_defaults()

    # ---- default path helpers ----
    def default_snap_paths(self) -> tuple[str | None, str | None]:
        """
        Returns (collection_path, mastery_path) if USERPROFILE is available.
        Uses:
          %USERPROFILE%\\AppData\\LocalLow\\Second Dinner\\SNAP\\Standalone\\States\\nvprod\\...
        """
        userprofile = os.environ.get("USERPROFILE")
        if not userprofile:
            return None, None

        base = os.path.join(
            userprofile,
            "AppData", "LocalLow", "Second Dinner", "SNAP",
            "Standalone", "States", "nvprod"
        )
        return (
            os.path.join(base, "CollectionState.json"),
            os.path.join(base, "CharacterMasteryState.json")
        )

    def try_autoload_defaults(self):
        c, m = self.default_snap_paths()
        if not c or not m:
            self.status_var.set("Auto-load unavailable (USERPROFILE not found). Select your JSON files, then click Load JSON.")
            return

        if os.path.isfile(c) and os.path.isfile(m):
            self.collection_path_var.set(c)
            self.mastery_path_var.set(m)
            self.load_files(silent=True)
        else:
            self.status_var.set("Default SNAP save files not found. Select your JSON files, then click Load JSON.")

    def _build_ui(self):
        # Top frame: file selectors
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="CollectionState.json:").grid(row=0, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.collection_path_var, width=90).grid(row=0, column=1, padx=8, sticky="we")
        ttk.Button(top, text="Browse…", command=self.browse_collection).grid(row=0, column=2)

        ttk.Label(top, text="CharacterMasteryState.json:").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(top, textvariable=self.mastery_path_var, width=90).grid(row=1, column=1, padx=8, pady=(8, 0), sticky="we")
        ttk.Button(top, text="Browse…", command=self.browse_mastery).grid(row=1, column=2, pady=(8, 0))

        top.columnconfigure(1, weight=1)

        # Middle controls: report selector + actions
        mid = ttk.Frame(self, padding=(10, 0, 10, 10))
        mid.pack(fill="x")

        ttk.Label(mid, text="Report:").grid(row=0, column=0, sticky="w", pady=10)
        report_menu = ttk.OptionMenu(mid, self.report_var, self.report_var.get(), *REPORTS)
        report_menu.grid(row=0, column=1, sticky="w")

        ttk.Button(mid, text="Load JSON", command=self.load_files).grid(row=0, column=2, padx=10)
        ttk.Button(mid, text="Generate Preview", command=self.generate_preview).grid(row=0, column=3)
        ttk.Button(mid, text="Export CSV…", command=self.export_csv).grid(row=0, column=4, padx=10)

        # Status line
        self.status_var = tk.StringVar(value="Select your JSON files, then click Load JSON.")
        status = ttk.Label(self, textvariable=self.status_var, padding=(10, 4))
        status.pack(fill="x")

        # Table (Treeview) with scrollbars
        table_frame = ttk.Frame(self, padding=10)
        table_frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(table_frame, columns=(), show="headings")
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        # Bottom: row limit
        bottom = ttk.Frame(self, padding=(10, 0, 10, 10))
        bottom.pack(fill="x")
        ttk.Label(bottom, text="Preview rows:").pack(side="left")
        self.preview_rows_var = tk.IntVar(value=200)
        ttk.Spinbox(bottom, from_=25, to=5000, increment=25, textvariable=self.preview_rows_var, width=8).pack(side="left", padx=8)

    def browse_collection(self):
        path = filedialog.askopenfilename(
            title="Select CollectionState.json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if path:
            self.collection_path_var.set(path)

    def browse_mastery(self):
        path = filedialog.askopenfilename(
            title="Select CharacterMasteryState.json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if path:
            self.mastery_path_var.set(path)

    def load_files(self, silent: bool = False):
        cpath = self.collection_path_var.get().strip()
        mpath = self.mastery_path_var.get().strip()

        if not cpath or not os.path.isfile(cpath):
            if not silent:
                messagebox.showerror("Missing file", "Please select a valid CollectionState.json file.")
            return
        if not mpath or not os.path.isfile(mpath):
            if not silent:
                messagebox.showerror("Missing file", "Please select a valid CharacterMasteryState.json file.")
            return

        try:
            self.collection_json = load_json(cpath)
            self.mastery_json = load_json(mpath)
        except Exception as e:
            if not silent:
                messagebox.showerror("Load error", f"Failed to load JSON:\n\n{e}")
            return

        self.status_var.set("Loaded JSON files successfully. Choose a report and click Generate Preview.")
        self.current_df = None
        self._clear_table()

    def generate_preview(self):
        if self.collection_json is None or self.mastery_json is None:
            messagebox.showwarning("Not loaded", "Click Load JSON first.")
            return

        report = self.report_var.get()

        try:
            if report.startswith("Cards:"):
                df = merged_boosters_mastery(self.collection_json, self.mastery_json)

                if report == REPORTS[0]:
                    # Boosters DESC, Mastery DESC
                    df = df.sort_values(
                        by=["Boosters", "MasteryLevel", "CardDefId"],
                        ascending=[False, False, True],
                    )

                elif report == REPORTS[1]:
                    # Boosters DESC, but max mastery (30) at bottom
                    df["IsMaxMastery"] = (df["MasteryLevel"] == 30)
                    df = df.sort_values(
                        by=["IsMaxMastery", "Boosters", "MasteryLevel", "CardDefId"],
                        ascending=[True, False, False, True],
                    ).drop(columns=["IsMaxMastery"])

                elif report == REPORTS[2]:
                    # Mastery DESC, Boosters DESC
                    df = df.sort_values(
                        by=["MasteryLevel", "Boosters", "CardDefId"],
                        ascending=[False, False, True],
                    )

                elif report == REPORTS[3]:
                    # Mastery + Boosters (DESC/DESC)
                    df = df.sort_values(
                        by=["MasteryLevel", "Boosters", "CardDefId"],
                        ascending=[False, False, True],
                    )

                elif report == REPORTS[4]:
                    # Mastery + Boosters (DESC/DESC), but max mastery (30) at bottom
                    df["IsMaxMastery"] = (df["MasteryLevel"] == 30)
                    df = df.sort_values(
                        by=["IsMaxMastery", "MasteryLevel", "Boosters", "CardDefId"],
                        ascending=[True, False, False, True],
                    ).drop(columns=["IsMaxMastery"])

                else:
                    raise ValueError(f"Unknown cards report: {report}")

                # Keep column order consistent for card reports
                df = df[["CardDefId", "Boosters", "MasteryLevel", "MasteryXP"]]

            elif report.startswith("Variants:"):
                df = variants_by_card(self.collection_json).sort_values(
                    by=["VariantCount", "CardDefId"],
                    ascending=[False, True],
                    na_position="last"
                )

            elif report.startswith("Albums:"):
                df = albums_by_completion(self.collection_json).sort_values(
                    by=["CompletionPct", "OwnedVariants", "TotalVariants", "AlbumName"],
                    ascending=[False, False, False, True],
                    na_position="last"
                )

            else:
                raise ValueError(f"Unknown report: {report}")

            self.current_df = df
            limit = int(self.preview_rows_var.get())
            self._populate_table(df.head(limit))
            self.status_var.set(f"Previewing {min(len(df), limit)} of {len(df)} rows. Ready to export.")

        except Exception as e:
            messagebox.showerror("Generate error", f"Failed to generate report:\n\n{e}")

    def export_csv(self):
        if self.current_df is None:
            messagebox.showwarning("No report", "Generate a preview first (this builds the report).")
            return

        default_name = self._default_export_filename()
        path = filedialog.asksaveasfilename(
            title="Save CSV",
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not path:
            return

        try:
            self.current_df.to_csv(path, index=False)
            self.status_var.set(f"Exported CSV: {path}")
            messagebox.showinfo("Exported", f"Saved:\n{path}")
        except Exception as e:
            messagebox.showerror("Export error", f"Failed to export CSV:\n\n{e}")

    def _default_export_filename(self) -> str:
        report = self.report_var.get()
        mapping = {
            REPORTS[0]: "cards_by_boosters_then_mastery.csv",
            REPORTS[1]: "cards_by_boosters_max_mastery_bottom.csv",
            REPORTS[2]: "cards_by_mastery_then_boosters.csv",
            REPORTS[3]: "cards_by_mastery_plus_boosters.csv",
            REPORTS[4]: "cards_by_mastery_plus_boosters_max_mastery_bottom.csv",
            REPORTS[5]: "variants_by_card_most_to_least.csv",
            REPORTS[6]: "albums_by_completion_most_to_least.csv",
        }
        return mapping.get(report, "snap_export.csv")

    def _clear_table(self):
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = ()
        for col in self.tree["columns"]:
            self.tree.heading(col, text="")
            self.tree.column(col, width=100)

    def _populate_table(self, df: pd.DataFrame):
        self._clear_table()

        cols = list(df.columns)
        self.tree["columns"] = cols

        # Columns we want displayed as integers
        int_cols = {
            "Boosters", "MasteryLevel", "MasteryXP",
            "TotalVariants", "OwnedVariants", "NeededForCompletion",
            "VariantCount",
        }

        # headings + column widths (simple heuristics)
        for col in cols:
            self.tree.heading(col, text=col)
            width = 140
            if col in ("CardDefId", "AlbumName"):
                width = 220
            if col in ("OwnedVariantIds",):
                width = 500
            self.tree.column(col, width=width, anchor="w", stretch=True)

        def format_cell(col_name: str, value):
            if value is None:
                return ""

            # Handle pandas NA
            try:
                if pd.isna(value):
                    return ""
            except Exception:
                pass

            # Int-like columns: always show clean int
            if col_name in int_cols:
                try:
                    return str(int(value))
                except Exception:
                    return str(value)

            # Percent: show with 2 decimals
            if col_name == "CompletionPct":
                try:
                    return f"{float(value):.2f}"
                except Exception:
                    return str(value)

            return str(value)

        for _, row in df.iterrows():
            values = [format_cell(col, row[col]) for col in cols]
            self.tree.insert("", "end", values=values)


if __name__ == "__main__":
    app = SnapExtractorApp()
    app.mainloop()
