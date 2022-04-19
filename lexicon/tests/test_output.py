""" Ensure that stdout corresponds to the given reference output """
import json

from lexicon import cli

DATA = [
    {
        "id": "fake-id",
        "type": "TXT",
        "name": "fake.example.com",
        "content": "fake",
        "ttl": 3600,
    },
    {
        "id": "fake2-id",
        "type": "TXT",
        "name": "fake2.example.com",
        "content": "fake2",
        "ttl": 3600,
    },
]


def assert_correct_output(capsys, expected_output_lines):
    out, _ = capsys.readouterr()
    assert out.splitlines() == expected_output_lines


def test_output_function_outputs_json_as_table(capsys):
    expected_output_lines = [
        "ID       TYPE NAME              CONTENT TTL ",
        "-------- ---- ----------------- ------- ----",
        "fake-id  TXT  fake.example.com  fake    3600",
        "fake2-id TXT  fake2.example.com fake2   3600",
    ]

    cli.handle_output(DATA, "TABLE", "list")
    assert_correct_output(capsys, expected_output_lines)


def test_output_function_outputs_json_as_table_with_no_header(capsys):
    expected_output_lines = [
        "fake-id  TXT fake.example.com  fake  3600",
        "fake2-id TXT fake2.example.com fake2 3600",
    ]

    cli.handle_output(DATA, "TABLE-NO-HEADER", "list")
    assert_correct_output(capsys, expected_output_lines)


def test_output_function_outputs_json_as_json_string(capsys):
    cli.handle_output(DATA, "JSON", "list")

    out, _ = capsys.readouterr()
    json_data = json.loads(out)

    assert json_data == DATA


def test_output_function_output_nothing_when_quiet(capsys):
    expected_output_lines = []

    cli.handle_output(DATA, "QUIET", "list")
    assert_correct_output(capsys, expected_output_lines)


def test_output_function_outputs_nothing_with_not_a_json_serializable(capsys):
    expected_output_lines = []

    cli.handle_output(object(), "TABLE", "list")
    assert_correct_output(capsys, expected_output_lines)

    cli.handle_output(object(), "TABLE-NO-HEADER", "list")
    assert_correct_output(capsys, expected_output_lines)

    cli.handle_output(object(), "JSON", "list")
    assert_correct_output(capsys, expected_output_lines)
