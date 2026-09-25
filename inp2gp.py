#!/usr/bin/env python3
"""inp2gp: turn a CSVY input (YAML frontmatter + CSV) into gnuplot inputs.

    NAME.csvy -> NAME.gp   vars as gnuplot variables, gnuplot entries as
                           'set' lines, then load '<template>.gp'
              -> NAME.dat  CSV rows, re-written for gnuplot's reader
              -> NAME.d    make dependencies of NAME.gp.tex

The frontmatter has up to three keys (a mapping, or a list of one-key maps):

    template: path/to/STEM     STEM.gp is the plot, STEM.csvy its defaults
    vars:     {...}            gnuplot variables (nested keys joined with _)
    gnuplot:  {...}            'set k v' per entry (true/empty: 'set k',
                               false: 'unset k'); may be a list of one-key maps

The user's vars and gnuplot entries are applied over STEM.csvy's.  inp2gp
knows nothing about any particular plot.

Usage: inp2gp.py [--template=STEM] NAME.csvy
"""

import argparse
import csv
import io
import math
import os
import re
import sys
from datetime import date

import yaml

RESERVED_VARS = {"data_file", "out_file", "N_rows"}
# gnuplot settings that would break the tikz / out_file / .dat contract.
# A key is refused if its first word is any abbreviation of one of these.
RESERVED_SETS = ("terminal", "output", "datafile", "table")
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
EXISTS = re.compile(r"""\bexists\s*\(\s*["']([A-Za-z_][A-Za-z0-9_]*)["']\s*\)""")


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


def one_key_maps(obj, where):
    """A mapping, or a list of one-key mappings -> list of (key, value)."""
    if obj is None:
        return []
    if isinstance(obj, dict):
        return list(obj.items())
    if isinstance(obj, list):
        pairs = []
        for item in obj:
            if not (isinstance(item, dict) and len(item) == 1):
                raise InputError(f"{where}: list items must be one-key mappings, got {item!r}")
            pairs.extend(item.items())
        return pairs
    raise InputError(f"{where}: expected a mapping or a list of one-key mappings")


def read_header(front, path, allowed):
    try:
        meta = yaml.safe_load(front)
    except yaml.YAMLError as e:
        raise InputError(f"{path}: YAML frontmatter: {e}") from None
    header = {}
    for key, value in one_key_maps(meta, f"{path}: frontmatter"):
        if key not in allowed:
            raise InputError(f"{path}: unknown frontmatter key '{key}' "
                             f"(allowed: {', '.join(allowed)}; template settings go under 'vars:')")
        if key in header:
            raise InputError(f"{path}: frontmatter key '{key}' given twice")
        header[key] = value
    return header


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


def read_vars(value, path):
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise InputError(f"{path}: 'vars' must be a mapping")
    out = flatten(value)
    for key in out:
        if not IDENT.match(key):
            raise InputError(f"{path}: var '{key}' is not a valid gnuplot variable name")
        if key in RESERVED_VARS:
            raise InputError(f"{path}: var '{key}' is reserved (set by inp2gp)")
    return out


def read_sets(value, path):
    pairs = []
    for key, v in one_key_maps(value, f"{path}: 'gnuplot'"):
        if not isinstance(key, str) or not key.split():
            raise InputError(f"{path}: gnuplot key {key!r} must be a setting name")
        key = " ".join(key.split())
        first = key.split()[0].lower()
        for name in RESERVED_SETS:
            if name.startswith(first):
                raise InputError(f"{path}: gnuplot '{key}' is reserved "
                                 f"('{name}' is set by the template or inp2gp)")
        pairs.append((key, v))
    return pairs


def gp_scalar(v, key):
    # bool before int: bool is a subclass of int
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        if not math.isfinite(v):
            raise InputError(f"var '{key}': {v} is not a finite number")
        return repr(v)
    if isinstance(v, date):
        v = v.isoformat()
    if isinstance(v, str):
        if "\n" in v or "\r" in v:
            raise InputError(f"var '{key}': strings cannot span lines")
        # single-quoted: gnuplot keeps backslashes as is; '' is a literal '
        return "'" + v.replace("'", "''") + "'"
    if v is None:
        raise InputError(f"var '{key}': empty value")
    raise InputError(f"var '{key}': unsupported value {v!r}")


def gp_assignment(key, v):
    if isinstance(v, list):
        items = ", ".join(gp_scalar(x, key) for x in v)
        return f"array {key}[{len(v)}] = [{items}]"
    return f"{key} = {gp_scalar(v, key)}"


def gp_set(key, v):
    if v is True or v is None:
        return f"set {key}"
    if v is False:
        return f"unset {key}"
    if isinstance(v, (int, float)):
        if isinstance(v, float) and not math.isfinite(v):
            raise InputError(f"gnuplot '{key}': {v} is not a finite number")
        return f"set {key} {v}"
    if isinstance(v, str):
        if "\n" in v or "\r" in v:
            raise InputError(f"gnuplot '{key}': the value must be one line (use '>-' in YAML)")
        return f"set {key} {v}" if v.strip() else f"set {key}"
    raise InputError(f"gnuplot '{key}': unsupported value {v!r}")


def merge_sets(defaults, user):
    """User entries replace every default entry with the same key, in place;
    new keys go at the end."""
    user_keys = {k for k, _ in user}
    out, placed = [], set()
    for k, v in defaults:
        if k not in user_keys:
            out.append((k, v))
        elif k not in placed:
            out.extend((uk, uv) for uk, uv in user if uk == k)
            placed.add(k)
    out.extend((k, v) for k, v in user if k not in placed)
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


def read_template(stem):
    """STEM.gp and STEM.csvy -> (defaults vars, defaults sets, optional vars)."""
    gp, defaults = stem + ".gp", stem + ".csvy"
    for p in (gp, defaults):
        if not os.path.isfile(p):
            raise InputError(f"template '{stem}': {p} not found")
    with open(defaults, encoding="utf-8") as f:
        front, rest, _ = split_csvy(f.read(), defaults)
    if rest.strip():
        raise InputError(f"{defaults}: a template's defaults file has a header only, no data")
    header = read_header(front, defaults, ("vars", "gnuplot"))
    # vars the template tests with exists() need no default (e.g. t_end)
    with open(gp, encoding="utf-8") as f:
        optional = set(EXISTS.findall(f.read())) - RESERVED_VARS
    return (read_vars(header.get("vars"), defaults),
            read_sets(header.get("gnuplot"), defaults),
            optional)


def make_path(p):
    p = os.path.relpath(p)
    if re.search(r"[\s:#$]", p):
        raise InputError(f"path '{p}' cannot be written into a make dependency file")
    return p


def main(argv):
    parser = argparse.ArgumentParser(
        prog="inp2gp.py", description="CSVY -> gnuplot inputs (NAME.gp, NAME.dat, NAME.d)")
    parser.add_argument("--template", metavar="STEM",
                        help="template to use, overriding the frontmatter's 'template'")
    parser.add_argument("input", metavar="NAME.csvy")
    args = parser.parse_args(argv[1:])

    inp = args.input
    if not inp.endswith(".csvy"):
        parser.error("the input must be a .csvy file")
    base = inp[: -len(".csvy")]
    inp_dir = os.path.dirname(inp) or "."
    name = os.path.basename(base)

    with open(inp, encoding="utf-8") as f:
        front, table, first_line = split_csvy(f.read(), inp)
    header = read_header(front, inp, ("template", "vars", "gnuplot"))

    if args.template:  # relative to the current directory
        stem = args.template
    elif isinstance(header.get("template"), str) and header["template"]:
        stem = os.path.join(inp_dir, header["template"])  # relative to the input
    else:
        raise InputError(f"{inp}: frontmatter needs 'template: <path/to/STEM>' "
                         "(or give --template)")
    stem = os.path.normpath(stem[:-3] if stem.endswith(".gp") else stem)

    def_vars, def_sets, optional = read_template(stem)
    user_vars = read_vars(header.get("vars"), inp)
    user_sets = read_sets(header.get("gnuplot"), inp)

    unknown = [k for k in user_vars if k not in def_vars and k not in optional]
    if unknown:
        raise InputError(f"{inp}: unknown var(s) {', '.join(unknown)} "
                         f"(not in {stem}.csvy, nor tested with exists() in {stem}.gp)")

    merged_vars = {**def_vars, **user_vars}
    merged_sets = merge_sets(def_sets, user_sets)
    assignments = [gp_assignment(k, v) for k, v in merged_vars.items()]
    sets = [gp_set(k, v) for k, v in merged_sets]
    header_row, rows = read_table(table, inp, first_line)

    # Everything checked; now write.  Paths inside NAME.gp are relative to
    # its own directory, where gnuplot is run.
    source = f"{os.path.relpath(stem, inp_dir)}.csvy, then {name}.csvy"
    gp = [
        f"# Generated by inp2gp from {name}.csvy -- edit that file instead.",
        f"data_file = {gp_scalar(name + '.dat', 'data_file')}",
        f"out_file = {gp_scalar(name + '.gp.tex', 'out_file')}",
        f"N_rows = {len(rows)}",
        f"# vars: {source}",
        *assignments,
        f"# gnuplot: {source}",
        *sets,
        f"load {gp_scalar(os.path.relpath(stem + '.gp', inp_dir), 'template')}",
    ]
    with open(base + ".gp", "w", encoding="utf-8") as f:
        f.write("\n".join(gp) + "\n")

    with open(base + ".dat", "w", encoding="utf-8") as f:
        for row in [header_row, *rows]:
            f.write("\t".join(row) + "\n")

    tex, gpf, dat, dep, tgp, tcsvy = (make_path(p) for p in (
        base + ".gp.tex", base + ".gp", base + ".dat", base + ".d", stem + ".gp", stem + ".csvy"))
    # 'file: ;' (an empty recipe) marks the template's files as sources: without
    # it make would try its '%.gp: %.csvy' rule on STEM.gp and STEM.csvy.
    with open(base + ".d", "w", encoding="utf-8") as f:
        f.write(f"{tex}: {gpf} {dat} {tgp}\n"
                f"{gpf} {dat} {dep}: {tcsvy}\n"
                f"{tgp}: ;\n{tcsvy}: ;\n")


if __name__ == "__main__":
    try:
        main(sys.argv)
    except (InputError, OSError) as e:
        sys.exit(f"inp2gp: {e}")
