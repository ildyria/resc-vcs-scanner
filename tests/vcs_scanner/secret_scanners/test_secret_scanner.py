# Standard Library
import sys
from datetime import UTC, datetime
from unittest.mock import patch

# Third Party
from _pytest.monkeypatch import MonkeyPatch

from vcs_scanner.api.schema.repository import Repository
from vcs_scanner.api.schema.scan import ScanRead
from vcs_scanner.api.schema.scan_type import ScanType

# First Party
from vcs_scanner.helpers.providers.rule_file import RuleFileProvider
from vcs_scanner.output_modules.rws_api_writer import RESTAPIWriter

sys.path.insert(0, "src")

mp = MonkeyPatch()
mp.setenv("GITLEAKS_PATH", "fake_gitleaks_path")
mp.setenv("RESC_RABBITMQ_SERVICE_HOST", "fake-rabbitmq-host.fakehost.com")
mp.setenv("RABBITMQ_DEFAULT_VHOST", "vhost")
mp.setenv("RESC_API_NO_AUTH_SERVICE_HOST", "fake_api_service_host")
mp.setenv("RABBITMQ_USERNAME", "fake user")
mp.setenv("RABBITMQ_PASSWORD", "fake pass")
mp.setenv("RABBITMQ_QUEUE", "queuename")
mp.setenv("VCS_INSTANCES_FILE_PATH", "fake_vcs_instance_config_json_path")

from vcs_scanner.secret_scanners.secret_scanner import SecretScanner  # noqa: E402  # isort:skip

BITBUCKET_USERNAME = "test"
GITLEAKS_PATH = "gitleaks_exec"


@patch("git.repo.base.Repo.clone_from")
def test_clone_repo(clone_from):
    rws_url = "https://fakeurl.com:8000"
    username = "username"
    personal_access_token = "personal_access_token"

    repository = Repository(
        project_key="project_key",
        repository_id=str(1),
        repository_name="repository_name",
        repository_url="https://repository.url",
        vcs_instance=1,
    )
    gitleaks_rules_provider = RuleFileProvider("/rules.toml", init=True)
    secret_scanner = SecretScanner(
        gitleaks_binary_path="/tmp/gitleaks",
        gitleaks_rules_provider=gitleaks_rules_provider,
        rule_pack_version="0.0.1",
        output_plugin=RESTAPIWriter(rws_url=rws_url),
        repository=repository,
        username=username,
        personal_access_token=personal_access_token,
    )

    secret_scanner._clone_repo()
    assert secret_scanner._repo_clone_path == f"./{repository.repository_name}"

    url = str(repository.repository_url).replace("https://", "")
    expected_repo_clone_path = f"{secret_scanner._scan_tmp_directory}/{repository.repository_name}"
    expected_repo_clone_url = f"https://{username}:{personal_access_token}@{url}"
    clone_from.assert_called_once()
    clone_from.assert_called_once_with(expected_repo_clone_url, expected_repo_clone_path)


@patch("vcs_scanner.secret_scanners.gitleaks_wrapper.GitLeaksWrapper.start_scan")
def test_scan_repo(start_scan):
    start_scan.return_value = None
    rws_url = "https://fakeurl.com:8000"
    username = "username"
    personal_access_token = "personal_access_token"

    repository = Repository(
        project_key="project_key",
        repository_id=str(1),
        repository_name="repository_name",
        repository_url="https://repository.url",
        vcs_instance=1,
    )
    gitleaks_rules_provider = RuleFileProvider("/rules.toml", init=True)
    secret_scanner = SecretScanner(
        gitleaks_binary_path="/tmp/gitleaks",
        gitleaks_rules_provider=gitleaks_rules_provider,
        rule_pack_version="0.0.1",
        output_plugin=RESTAPIWriter(rws_url=rws_url),
        repository=repository,
        username=username,
        personal_access_token=personal_access_token,
    )
    repo_clone_path = f"{secret_scanner._scan_tmp_directory}/{repository.repository_name}"
    secret_scanner._repo_clone_path = repo_clone_path
    result = secret_scanner._scan_repo(ScanType.BASE, None)
    assert result is None
    start_scan.assert_called_once()


@patch("vcs_scanner.secret_scanners.gitleaks_wrapper.GitLeaksWrapper.start_scan")
def test_scan_directory(start_scan):
    start_scan.return_value = None
    rws_url = "https://fakeurl.com:8000"
    repository = Repository(
        project_key="local",
        repository_id=str(1),
        repository_name="local",
        repository_url="https://repository.url",
        vcs_instance=1,
    )
    gitleaks_rules_provider = RuleFileProvider("/rules.toml", init=True)
    secret_scanner = SecretScanner(
        gitleaks_binary_path="/tmp/gitleaks",
        gitleaks_rules_provider=gitleaks_rules_provider,
        rule_pack_version="0.0.1",
        output_plugin=RESTAPIWriter(rws_url=rws_url),
        repository=repository,
        username="",
        personal_access_token="",
    )
    repo_clone_path = f"{secret_scanner._scan_tmp_directory}/{repository.repository_name}"
    result = secret_scanner._scan_directory(directory_path=repo_clone_path)
    assert result is None
    start_scan.assert_called_once()


# not a test class
def initialize_and_get_repo_scanner():
    repository = Repository(
        project_key="local",
        repository_id=str(1),
        repository_name="local",
        repository_url="https://repository.url",
        vcs_instance=1,
    )
    gitleaks_rules_provider = RuleFileProvider("/rules.toml", init=True)
    secret_scanner = SecretScanner(
        gitleaks_binary_path="/tmp/gitleaks",
        gitleaks_rules_provider=gitleaks_rules_provider,
        rule_pack_version="2.0.1",
        output_plugin=RESTAPIWriter(rws_url="https://fakeurl.com:8000"),
        repository=repository,
        username="",
        personal_access_token="",
    )

    return secret_scanner


def test_scan_type_is_not_set():
    secret_scanner = initialize_and_get_repo_scanner()
    secret_scanner.run_scan(False, False)
    assert not secret_scanner._is_valid()


def test_is_scan_needed_from_latest_commit_when_no_latest_and_repo():
    secret_scanner = initialize_and_get_repo_scanner()
    secret_scanner._as_repo = True
    assert not secret_scanner._is_scan_needed_from_latest_commit()


def test_is_scan_needed_from_latest_commit_when_no_latest_and_dir():
    secret_scanner = initialize_and_get_repo_scanner()
    secret_scanner._as_dir = True
    assert secret_scanner._is_scan_needed_from_latest_commit()


def test_scan_type_is_base_when_a_latest_scan_is_not_present():
    secret_scanner = initialize_and_get_repo_scanner()

    scan_type = secret_scanner._determine_scan_type(None)
    assert scan_type == ScanType.BASE


def test_scan_type_is_base_when_a_latest_scan_is_present_and_rule_pack_is_latest():
    secret_scanner = initialize_and_get_repo_scanner()

    scan_read = ScanRead(
        id_=1,
        repository_id=str(1),
        scan_type=ScanType.BASE,
        last_scanned_commit="latest_commit_1",
        timestamp=datetime.now(UTC),
        increment_number=0,
        rule_pack="2.0.2",
    )

    secret_scanner.latest_commit = "latest_commit"
    scan_type = secret_scanner._determine_scan_type(scan_read)
    assert scan_type == ScanType.BASE


def test_scan_type_is_incremental_when_a_latest_scan_is_present_and_rule_pack_is_same():
    secret_scanner = initialize_and_get_repo_scanner()

    scan_read = ScanRead(
        id_=1,
        repository_id=str(1),
        scan_type=ScanType.BASE,
        last_scanned_commit="latest_commit_1",
        timestamp=datetime.now(UTC),
        increment_number=0,
        rule_pack=secret_scanner.rule_pack_version,
    )

    secret_scanner.latest_commit = "latest_commit"
    scan_type = secret_scanner._determine_scan_type(scan_read)
    assert scan_type == ScanType.INCREMENTAL


def test_scan_type_is_incremental_when_a_latest_scan_is_present_and_rule_pack_is_same_and_last_commit_is_newer():
    secret_scanner = initialize_and_get_repo_scanner()

    scan_read = ScanRead(
        id_=1,
        repository_id=str(1),
        scan_type=ScanType.BASE,
        last_scanned_commit="latest_commit_1",
        timestamp=datetime.now(UTC),
        increment_number=0,
        rule_pack=secret_scanner.rule_pack_version,
    )

    secret_scanner.latest_commit = "latest_commit"
    scan_type = secret_scanner._determine_scan_type(scan_read)
    assert scan_type == ScanType.INCREMENTAL
