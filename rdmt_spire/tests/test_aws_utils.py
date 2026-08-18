import os
from pathlib import Path

from rdmt_spire.utilities.aws_utils import file_exists, load_file_object


def test_load_file_object_local_file1(tmp_path):
    # Check a local file with path beginning with slash
    local_file = tmp_path / "mykey"
    local_file.write_text("content")

    result = load_file_object(str(local_file.parent), local_file.name)
    assert result.read() == b"content"

def test_load_file_object_local_file2(tmp_path, monkeypatch):
    # Check a local file whose path does not being with a slash (i.e., relative path)
    data_dir = tmp_path / "test_data"
    data_dir.mkdir()
    target = data_dir / "check.txt"
    target.write_text("abc")    
    monkeypatch.chdir(tmp_path)  # Change the current working directory to the temp path
    local_file = Path(os.path.join('test_data', 'check.txt'))

    result = load_file_object(str(local_file.parent), local_file.name)
    assert result.read() == b"abc"


def test_file_exists_local_file1(tmp_path, monkeypatch):
    # Check a local file whose path does not being with a slash (i.e., relative path)
    data_dir = tmp_path / "test_data"
    data_dir.mkdir()
    target = data_dir / "check.txt"
    target.write_text("abc")    
    monkeypatch.chdir(tmp_path)  # Change the current working directory to the temp path
    local_file = Path(os.path.join('test_data', 'check.txt'))
    assert file_exists(str(local_file.parent), local_file.name) is True

def test_file_exists_local_file2(tmp_path):
    # Check a local file with path beginning with slash
    local_file = tmp_path / "mykey"
    local_file.write_text("content")
    assert file_exists(str(local_file.parent), local_file.name) is True

