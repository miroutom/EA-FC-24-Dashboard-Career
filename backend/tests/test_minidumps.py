"""Synthetic binary format fixtures; real user dumps are never committed."""

import importlib.util
import struct
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "inspect_minidumps", Path(__file__).resolve().parents[2] / "scripts" / "inspect_minidumps.py"
)
inspector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inspector)


def dump(base=0x140000000, access=0, target=2, architecture=9, code=0xC0000005):
    data = bytearray(1024)
    struct.pack_into("<IIIIIIQ", data, 0, 0x504D444D, 0xA793, 3, 32, 0, 0, 0)
    for index, stream in enumerate(((4, 112, 128), (6, 168, 256), (7, 56, 448))):
        struct.pack_into("<III", data, 32 + index * 12, *stream)
    struct.pack_into("<I", data, 128, 1)
    struct.pack_into("<QIIII", data, 132, base, 0x3000000, 0, 123, 512)
    struct.pack_into("<II", data, 132 + 32, 0x00010002, 0x00030004)
    name = "C:\\Users\\Private\\Games\\FC24.exe".encode("utf-16-le")
    struct.pack_into("<I", data, 512, len(name))
    data[516 : 516 + len(name)] = name
    struct.pack_into("<IIIIQQII", data, 256, 42, 0, code, 0, 0, base + 0x13EBA2F, 2, 0)
    struct.pack_into("<QQ", data, 296, access, target)
    struct.pack_into("<II", data, 416, 256, 640)
    struct.pack_into("<H", data, 448, architecture)
    struct.pack_into("<I", data, 640 + 48, 0x100003)
    struct.pack_into("<Q", data, 640 + 248, base + 0x13EBA2F)
    return bytes(data)


def test_module_relative_signature_groups_aslr_and_omits_private_paths():
    reports = [inspector.inspect_bytes(dump(base), "C:\\private\\sample.mdmp") for base in (0x140000000, 0x180000000)]
    exception = reports[0]["exception"]
    assert exception["module"] == "FC24.exe"
    assert exception["module_offset"] == "0x13eba2f"
    assert exception["module_version"] == "1.2.3.4"
    assert exception["access"] == "read"
    assert exception["access_address"] == "0x2"
    assert reports[0]["registers"]["rip"] == "0x1413eba2f"
    assert reports[0]["file"] == "sample.mdmp"
    assert "Private" not in str(reports)
    assert inspector.summarize(reports)[0]["count"] == 2


@pytest.mark.parametrize("access,label", [(0, "read"), (1, "write"), (8, "execute")])
def test_access_violation_operation_and_unknown_architecture(access, label):
    result = inspector.inspect_bytes(dump(access=access, architecture=12))
    assert result["exception"]["access"] == label
    assert result["registers"] == {}


def test_non_access_exception_is_not_misclassified():
    result = inspector.inspect_bytes(dump(code=0x80000003))
    assert "access" not in result["exception"]


@pytest.mark.parametrize("data", [b"", b"MDMP", dump()[:700], b"NOPE" + dump()[4:]])
def test_invalid_or_truncated_dumps_fail_explicitly(data):
    with pytest.raises(inspector.DumpError):
        inspector.inspect_bytes(data)


def test_exception_count_and_stream_size_are_validated():
    data = bytearray(dump())
    struct.pack_into("<I", data, 256 + 32, 16)
    with pytest.raises(inspector.DumpError, match="parameter count"):
        inspector.inspect_bytes(bytes(data))
    data = bytearray(dump())
    struct.pack_into("<I", data, 32 + 12 + 4, 40)
    with pytest.raises(inspector.DumpError, match="exception stream"):
        inspector.inspect_bytes(bytes(data))


def test_cli_reports_bad_file_and_continues(tmp_path, capsys):
    import json

    (tmp_path / "good.mdmp").write_bytes(dump())
    (tmp_path / "bad.mdmp").write_bytes(b"bad")
    assert inspector.main([str(tmp_path)]) == 1
    output = json.loads(capsys.readouterr().out)
    assert len(output["dumps"]) == 1
    assert output["errors"][0]["file"] == "bad.mdmp"
    assert str(tmp_path) not in str(output)
