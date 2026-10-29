"""Read Windows minidump metadata without launching the game or loading its DLLs.

Stdlib only. Reports the recorded exception and module-relative address; it does
not unwind stacks, disassemble code, diagnose save corruption, or repair saves.
Module paths are reduced to basenames. Keep dumps themselves out of Git.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from collections import defaultdict
from pathlib import Path, PureWindowsPath


class DumpError(ValueError):
    pass


class Reader:
    def __init__(self, data: bytes):
        self.data = data

    def block(self, offset: int, size: int) -> bytes:
        if offset < 0 or size < 0 or offset > len(self.data) - size:
            raise DumpError("truncated or invalid minidump range")
        return self.data[offset : offset + size]

    def unpack(self, fmt: str, offset: int):
        return struct.unpack(fmt, self.block(offset, struct.calcsize(fmt)))

    def name(self, offset: int) -> str:
        size, = self.unpack("<I", offset)
        try:
            value = self.block(offset + 4, size).decode("utf-16-le")
        except UnicodeDecodeError as error:
            raise DumpError("invalid module name encoding") from error
        return PureWindowsPath(value).name


def inspect_bytes(data: bytes, name: str = "dump.mdmp") -> dict:
    reader = Reader(data)
    signature, _, count, directory, _, _, _ = reader.unpack("<IIIIIIQ", 0)
    if signature != 0x504D444D:
        raise DumpError("not a Windows MDMP file")
    reader.block(directory, count * 12)
    streams = {}
    for index in range(count):
        kind, size, rva = reader.unpack("<III", directory + index * 12)
        reader.block(rva, size)
        if kind in streams and kind in {4, 6, 7}:
            raise DumpError("duplicate required stream")
        streams[kind] = (rva, size)
    if 6 not in streams:
        raise DumpError("exception stream missing; no crash signature available")

    modules = []
    if 4 in streams:
        offset, size = streams[4]
        if size < 4:
            raise DumpError("truncated module list")
        module_count, = reader.unpack("<I", offset)
        if module_count > (size - 4) // 108:
            raise DumpError("truncated module records")
        for index in range(module_count):
            record = offset + 4 + index * 108
            base, image_size, _, timestamp, name_rva = reader.unpack("<QIIII", record)
            version_ms, version_ls = reader.unpack("<II", record + 32)
            modules.append({
                "name": reader.name(name_rva),
                "base": base,
                "size": image_size,
                "timestamp": timestamp,
                "file_version": ".".join(str(value) for value in (
                    version_ms >> 16, version_ms & 0xFFFF,
                    version_ls >> 16, version_ls & 0xFFFF,
                )),
            })

    offset, size = streams[6]
    if size < 168:
        raise DumpError("truncated exception stream")
    thread_id, _, code, flags, _, address, parameter_count, _ = reader.unpack("<IIIIQQII", offset)
    if parameter_count > 15:
        raise DumpError("invalid exception parameter count")
    parameters = reader.unpack("<15Q", offset + 40)[:parameter_count]
    context_size, context_rva = reader.unpack("<II", offset + 160)
    reader.block(context_rva, context_size)
    module = next((item for item in modules if item["base"] <= address < item["base"] + item["size"]), None)
    module_offset = address - module["base"] if module else None
    exception = {
        "code": f"0x{code:08x}", "flags": flags, "thread_id": thread_id,
        "address": hex(address), "parameters": [hex(value) for value in parameters],
        "module": module["name"] if module else None,
        "module_offset": hex(module_offset) if module_offset is not None else None,
        "module_version": module["file_version"] if module else None,
        "module_timestamp": module["timestamp"] if module else None,
    }
    if code == 0xC0000005 and len(parameters) >= 2:
        exception["access"] = {0: "read", 1: "write", 8: "execute"}.get(parameters[0], "unknown")
        exception["access_address"] = hex(parameters[1])

    architecture = None
    if 7 in streams:
        system_rva, system_size = streams[7]
        if system_size < 2:
            raise DumpError("truncated system info")
        architecture, = reader.unpack("<H", system_rva)
    registers = {}
    if architecture == 9 and context_size >= 256:
        context_flags, = reader.unpack("<I", context_rva + 48)
        # AMD64 CONTEXT_CONTROL: never interpret another architecture's layout.
        if context_flags & 0x100001 == 0x100001:
            for register, relative in (("rsp", 152), ("rip", 248)):
                value, = reader.unpack("<Q", context_rva + relative)
                registers[register] = hex(value)
        if context_flags & 0x100002 == 0x100002:
            for register, relative in (("rax", 120), ("rcx", 128), ("rdx", 136), ("rdi", 176)):
                value, = reader.unpack("<Q", context_rva + relative)
                registers[register] = hex(value)
    return {
        "file": PureWindowsPath(name).name,
        "sha256": hashlib.sha256(data).hexdigest(),
        "size": len(data), "architecture": architecture,
        "exception": exception, "registers": registers,
        "relevant_modules": [item for item in modules if item["name"].lower() in {
            "fc24.exe", "fcliveeditor.dll", "engine.buildinfo.dll", "gameoverlayrenderer64.dll",
        }],
        "limitations": "Exception metadata only; no stack unwind or root-cause inference.",
    }


def summarize(reports: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for report in reports:
        exception = report["exception"]
        keys = ("code", "module", "module_offset", "module_version", "module_timestamp", "access", "access_address")
        signature = tuple(exception.get(key) for key in keys)
        if exception["module"] is None:
            signature += (exception["address"],)
        groups[signature].append(report)
    return [{
        "count": len(group), "exception": group[0]["exception"],
        "files": [item["file"] for item in group],
    } for group in groups.values()]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path, help="Extracted .mdmp/.dmp files or directories")
    args = parser.parse_args(argv)
    files = set()
    for path in args.paths:
        if path.is_dir():
            files.update(item for item in path.iterdir() if item.suffix.lower() in {".dmp", ".mdmp"} and item.is_file())
        else:
            files.add(path)
    if not files:
        parser.error("no extracted minidumps found")
    reports, errors = [], []
    for path in sorted(files):
        try:
            reports.append(inspect_bytes(path.read_bytes(), path.name))
        except (OSError, DumpError) as error:
            # OSError text can include private absolute paths.
            errors.append({"file": path.name, "error": str(error) if isinstance(error, DumpError) else type(error).__name__})
    print(json.dumps({"dumps": reports, "groups": summarize(reports), "errors": errors}, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
