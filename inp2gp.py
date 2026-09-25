#!/usr/bin/env python3
"""inp2gp: turn a CSVY input (YAML frontmatter + CSV) into gnuplot inputs.

    NAME.csvy -> NAME.gp   frontmatter as gnuplot variables, then load '<template>'
              -> NAME.dat  CSV rows, re-written for gnuplot's reader
              -> NAME.d    make dependencies of NAME.gp.tex

It knows nothing about any particular plot: every frontmatter key except
`template` becomes a gnuplot variable, and the template does the rest.

Usage: inp2gp.py NAME.csvy
"""

import csv
import io
import math
import os
import re
import sys
from datetime import date

import yaml

RESERVED = {"data_file", "out_file", "N_rows"}
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


class InputError(Exception):
    pass


def split_csvy(text, path):
    """Return (frontmatter text, CSV text, line number where CSV starts)."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise InputError(f"{path}:1: expected '---' to open the YAML frontmatter")
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "".join(lines[1:i]), "".join(lines[i + 1:]), i + 2
    raise InputError(f"{path}: no closing '---' after the YAML frontmatter")


def flatten(d, prefix=""):
    """{'fig': {'w': 8}} -> {'fig_w': 8}"""
    out = {}
    for k, v in d.items():
        name = f"{prefix}_{k}" if prefix else str(k)
        if isinstance(v, dict):
            out.update(flatten(v, name))
        else:
            out[name] = v
    return out


def gp_scalar(v, key):
    # bool before int: bool is a subclass of int
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        if not math.isfinite(v):
            raise InputError(f"key '{key}': {v} is not a finite number")
        return repr(v)
    if isinstance(v, date):
        v = v.isoformat()
    if isinstance(v, str):
        if "\n" in v or "\r" in v:
            raise InputError(f"key '{key}': strings cannot span lines")
        # single-quoted: gnuplot keeps backslashes as is; '' is a literal '
        return "'" + v.replace("'", "''") + "'"
    if v is None:
        raise InputError(f"key '{key}': empty value")
    raise InputError(f"key '{key}': unsupported value {v!r}")


def gp_assignments(meta):
    out = []
    for key, v in flatten(meta).items():
        if not IDENT.match(key):
            raise InputError(f"key '{key}' is not a valid gnuplot variable name")
        if key in RESERVED:
            raise InputError(f"key '{key}' is reserved (set by inp2gp)")
        if isinstance(v, list):
            items = ", ".join(gp_scalar(x, key) for x in v)
            out.append(f"array {key}[{len(v)}] = [{items}]")
        else:
            out.append(f"{key} = {gp_scalar(v, key)}")
    return out


def gp_field(s, where):
    for bad, name in (('"', "double quote"), ("\t", "tab"), ("\n", "newline"), ("\r", "newline")):
        if bad in s:
            raise InputError(f"{where}: a {name} cannot pass through gnuplot's data reader")
    # strcol() applies backslash escapes once; doubling makes it return s verbatim
    return s.replace("\\", "\\\\")


def read_table(text, path, first_line):
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    rows = []
    header = None
    try:
        for row in reader:
            where = f"{path}:{first_line + reader.line_num - 1}"
            if not any(f.strip() for f in row):
                continue  # blank line
            if header is None:
                header = row
                if any(not h.strip() for h in header):
                    raise InputError(f"{where}: empty column name in the header row")
                dup = {h for h in header if header.count(h) > 1}
                if dup:
                    raise InputError(f"{where}: duplicate column name(s): {', '.join(sorted(dup))}")
                header = [gp_field(h, where) for h in header]
                continue
            if len(row) != len(header):
                raise InputError(f"{where}: {len(row)} fields, but the header has {len(header)}")
            rows.append([gp_field(f, where) for f in row])
    except csv.Error as e:
        raise InputError(f"{path}:{first_line + reader.line_num - 1}: {e}") from None
    if header is None:
        raise InputError(f"{path}: no CSV header row after the frontmatter")
    if not rows:
        raise InputError(f"{path}: no data rows")
    return header, rows


def make_path(p):
    p = os.path.relpath(p)
    if re.search(r"[\s:#$]", p):
        raise InputError(f"path '{p}' cannot be written into a make dependency file")
    return p


def main(argv):
    if len(argv) != 2 or not argv[1].endswith(".csvy"):
        sys.exit(__doc__.strip().splitlines()[-1])
    inp = argv[1]
    base = inp[: -len(".csvy")]
    inp_dir = os.path.dirname(inp) or "."
    name = os.path.basename(base)

    with open(inp, encoding="utf-8") as f:
        front, table, first_line = split_csvy(f.read(), inp)

    try:
        meta = yaml.safe_load(front) or {}
    except yaml.YAMLError as e:
        raise InputError(f"{inp}: YAML frontmatter: {e}") from None
    if not isinstance(meta, dict):
        raise InputError(f"{inp}: the frontmatter must be a mapping of key: value")

    template = meta.pop("template", None)
    if not isinstance(template, str) or not template:
        raise InputError(f"{inp}: frontmatter needs 'template: <path to .gp>'")
    template_path = os.path.normpath(os.path.join(inp_dir, template))
    if not os.path.isfile(template_path):
        raise InputError(f"{inp}: template '{template}' not found (looked for {template_path})")

    try:
        assignments = gp_assignments(meta)
    except InputError as e:
        raise InputError(f"{inp}: {e}") from None
    header, rows = read_table(table, inp, first_line)

    # Everything checked; now write.  Paths inside NAME.gp are relative to
    # its own directory, where gnuplot is run.
    gp = [
        f"# Generated by inp2gp from {name}.csvy -- edit that file instead.",
        f"data_file = {gp_scalar(name + '.dat', 'data_file')}",
        f"out_file = {gp_scalar(name + '.gp.tex', 'out_file')}",
        f"N_rows = {len(rows)}",
        *assignments,
        f"load {gp_scalar(os.path.relpath(template_path, inp_dir), 'template')}",
    ]
    with open(base + ".gp", "w", encoding="utf-8") as f:
        f.write("\n".join(gp) + "\n")

    with open(base + ".dat", "w", encoding="utf-8") as f:
        for row in [header, *rows]:
            f.write("\t".join(row) + "\n")

    tex, gpf, dat, tpl = (make_path(p) for p in
                          (base + ".gp.tex", base + ".gp", base + ".dat", template_path))
    with open(base + ".d", "w", encoding="utf-8") as f:
        f.write(f"{tex}: {gpf} {dat} {tpl}\n{tpl}:\n")


if __name__ == "__main__":
    try:
        main(sys.argv)
    except (InputError, OSError) as e:
        sys.exit(f"inp2gp: {e}")
