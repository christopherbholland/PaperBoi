import pytest
from unittest.mock import MagicMock
from pathlib import Path
import json

@pytest.fixture
def mock_processor_config():
    """
    Simple fixture to mock ProcessorConfig directories.
    """
    mock_base_dir = MagicMock(spec=Path)
    mock_papers_dir = MagicMock(spec=Path)
    mock_summaries_dir = MagicMock(spec=Path)
    mock_metadata_dir = MagicMock(spec=Path)
    mock_errors_dir = MagicMock(spec=Path)

    mock_base_dir.__truediv__.side_effect = lambda x: {
        'full_papers': mock_papers_dir,
        'paperboi_summaries': mock_summaries_dir,
        'metadata': mock_metadata_dir,
        'error_log': mock_errors_dir,
    }.get(x, MagicMock(spec=Path))

    from config import ProcessorConfig
    config = ProcessorConfig()
    config.base_dir = mock_base_dir
    return config, mock_papers_dir, mock_summaries_dir, mock_metadata_dir, mock_errors_dir

def test_processor_config_create_directories(mock_processor_config):
    """
    Test that directories are created using create_directories.
    """
    config, papers_dir, summaries_dir, metadata_dir, errors_dir = mock_processor_config
    config.create_directories()
    papers_dir.mkdir.assert_called_once_with(exist_ok=True)
    summaries_dir.mkdir.assert_called_once_with(exist_ok=True)
    metadata_dir.mkdir.assert_called_once_with(exist_ok=True)
    errors_dir.mkdir.assert_called_once_with(exist_ok=True)

def test_metadata_manager_load_and_save_master():
    """
    Test loading and saving the master metadata file.
    """
    from config import MetadataManager

    # Mock metadata file path
    mock_metadata_file = MagicMock(spec=Path)
    mock_metadata_file.read_text.return_value = json.dumps({"paper1": {"title": "Paper One"}})

    # Mock metadata directory
    mock_metadata_dir = MagicMock(spec=Path)
    mock_metadata_dir.__truediv__.return_value = mock_metadata_file

    manager = MetadataManager(mock_metadata_dir)

    # Test load_master
    loaded_data = manager.load_master()
    assert loaded_data == {"paper1": {"title": "Paper One"}}, "load_master did not return expected data"
    mock_metadata_file.read_text.assert_called_once()

    # Test save_master
    new_data = {"paper2": {"title": "Paper Two"}}
    manager.save_master(new_data)
    mock_metadata_file.write_text.assert_called_once_with(json.dumps(new_data, indent=4))