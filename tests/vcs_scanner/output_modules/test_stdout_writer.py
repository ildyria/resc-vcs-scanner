# Standard Library
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import call, patch

# Third Party
from vcs_scanner.api.schema.finding import Finding
from vcs_scanner.api.schema.finding_status import FindingStatus
from vcs_scanner.api.schema.repository import (
    RepositoryCreate,
    RepositoryRead,
)
from vcs_scanner.api.schema.scan import ScanRead

# First Party
from vcs_scanner.helpers.providers.ignore_list import IgnoredListProvider
from vcs_scanner.helpers.providers.rule_comment import RuleCommentProvider
from vcs_scanner.helpers.providers.rule_tag import RuleTagProvider
from vcs_scanner.output_modules.stdout_writer import STDOUTWriter

THIS_DIR = Path(__file__).parent.parent


# A test method to check the happy flow of the write_repository method.
@patch("logging.Logger.info")
def test_write_correct_repository(info_log):
    repository = RepositoryCreate(
        project_key="project_key",
        repository_id=str(1),
        repository_name="repository_name",
        repository_url="http://repository.url",
        vcs_instance=1,
    )
    expected_call = f"Scanning repository {repository.project_key}/{repository.repository_name}"

    rule_tag_provider = RuleTagProvider()
    rule_tag_provider.load("toml_path")

    rule_comment_provider = RuleCommentProvider()
    rule_comment_provider.load("toml_path")

    result = STDOUTWriter(
        exit_code_warn=2,
        exit_code_block=1,
        rule_tag_provider=rule_comment_provider,
        rule_comment_provider=rule_comment_provider,
    ).write_repository(repository)
    assert result == repository
    info_log.assert_called_once_with(expected_call)


@patch("sys.exit")
@patch("logging.Logger.info")
def test_write_findings(info_log, exit_mock):
    findings = []
    for i in range(1, 7):
        findings.append(
            Finding(
                file_path=f"file_path_{i}",
                line_number=i,
                column_start=i,
                column_end=i,
                commit_id=f"commit_id_{i}",
                commit_message=f"commit_message_{i}",
                commit_timestamp=datetime.now(UTC),
                author=f"author_{i}",
                email=f"email_{i}",
                status=FindingStatus.NOT_ANALYZED,
                comment=f"comment_{i}",
                event_sent_on=datetime.now(UTC),
                rule_name=f"rule_{i}",
            )
        )
    _ = STDOUTWriter(exit_code_warn=2, exit_code_block=1).write_findings(1, 1, findings)
    calls = [
        call(
            "\n"
            "+-------+--------+------+----------+-------------+---------+\n"
            "| Level | Rule   | Line | Position | File path   | Comment |\n"
            "+-------+--------+------+----------+-------------+---------+\n"
            "| Info  | rule_1 |    1 | 1-1      | file_path_1 |         |\n"
            "| Info  | rule_2 |    2 | 2-2      | file_path_2 |         |\n"
            "| Info  | rule_3 |    3 | 3-3      | file_path_3 |         |\n"
            "| Info  | rule_4 |    4 | 4-4      | file_path_4 |         |\n"
            "| Info  | rule_5 |    5 | 5-5      | file_path_5 |         |\n"
            "| Info  | rule_6 |    6 | 6-6      | file_path_6 |         |\n"
            "+-------+--------+------+----------+-------------+---------+"
        ),
        call("Findings detected : Total - 6, Block - 0, Warn - 0, Info - 6"),
        call("Findings threshold check results: PASS"),
    ]
    info_log.assert_has_calls(calls, any_order=True)
    exit_mock.assert_called_with(0)


@patch("sys.exit")
@patch("logging.Logger.info")
def test_write_findings_with_rules(info_log, exit_mock):
    findings = []
    toml_rule_path = THIS_DIR.parent / "fixtures/rules.toml"
    for i in range(1, 7):
        findings.append(
            Finding(
                file_path=f"file_path_{i}",
                line_number=i,
                column_start=i,
                column_end=i,
                commit_id=f"commit_id_{i}",
                commit_message=f"commit_message_{i}",
                commit_timestamp=datetime.now(UTC),
                author=f"author_{i}",
                email=f"email_{i}",
                status=FindingStatus.NOT_ANALYZED,
                comment=f"comment_{i}",
                event_sent_on=datetime.now(UTC),
                rule_name=f"rule_{i}",
            )
        )
    rule_tag_provider = RuleTagProvider()
    rule_tag_provider.load(str(toml_rule_path))

    rule_comment_provider = RuleCommentProvider()
    rule_comment_provider.load(str(toml_rule_path))

    _ = STDOUTWriter(
        exit_code_warn=2,
        exit_code_block=1,
        rule_tag_provider=rule_tag_provider,
        rule_comment_provider=rule_comment_provider,
    ).write_findings(1, 1, findings)
    calls = [
        call(
            "\n"
            "+-------+--------+------+----------+-------------+-------------+\n"
            "| Level | Rule   | Line | Position | File path   | Comment     |\n"
            "+-------+--------+------+----------+-------------+-------------+\n"
            "| Block | rule_1 |    1 | 1-1      | file_path_1 |             |\n"
            "| Block | rule_2 |    2 | 2-2      | file_path_2 |             |\n"
            "| Block | rule_6 |    6 | 6-6      | file_path_6 |             |\n"
            "| Info  | rule_4 |    4 | 4-4      | file_path_4 |             |\n"
            "| Info  | rule_5 |    5 | 5-5      | file_path_5 |             |\n"
            "| Warn  | rule_3 |    3 | 3-3      | file_path_3 | See rule 3. |\n"
            "+-------+--------+------+----------+-------------+-------------+"
        ),
        call("Findings detected : Total - 6, Block - 3, Warn - 1, Info - 2"),
        call("Scan failed due to policy violations: [Block:3]"),
        call("Findings threshold check results: FAIL"),
    ]
    info_log.assert_has_calls(calls, any_order=True)
    exit_mock.assert_called_with(1)


@patch("sys.exit")
@patch("logging.Logger.info")
def test_write_findings_with_rules_and_ignore(info_log, exit_mock):
    findings = []
    toml_rule_path = THIS_DIR.parent / "fixtures/rules.toml"
    ignore_list_path = THIS_DIR.parent / "fixtures/ignore-findings-list-for-writer.dsv"
    for i in range(1, 7):
        findings.append(
            Finding(
                file_path=f"file_path_{i}",
                line_number=i,
                column_start=i,
                column_end=i,
                commit_id=f"commit_id_{i}",
                commit_message=f"commit_message_{i}",
                commit_timestamp=datetime.now(UTC),
                author=f"author_{i}",
                email=f"email_{i}",
                status=FindingStatus.NOT_ANALYZED,
                comment=f"comment_{i}",
                event_sent_on=datetime.now(UTC),
                rule_name=f"rule_{i}",
            )
        )

    rule_tag_provider = RuleTagProvider()
    rule_tag_provider.load(str(toml_rule_path))

    rule_comment_provider = RuleCommentProvider()
    rule_comment_provider.load(str(toml_rule_path))

    ignore_findings_providers = IgnoredListProvider(ignore_list_path)

    _ = STDOUTWriter(
        exit_code_warn=2,
        exit_code_block=1,
        rule_tag_provider=rule_tag_provider,
        rule_comment_provider=rule_comment_provider,
        ignore_findings_providers=ignore_findings_providers,
    ).write_findings(1, 1, findings)
    calls = [
        call(
            "\n"
            "+---------+--------+------+----------+-------------+-------------+\n"
            "| Level   | Rule   | Line | Position | File path   | Comment     |\n"
            "+---------+--------+------+----------+-------------+-------------+\n"
            "| Block   | rule_2 |    2 | 2-2      | file_path_2 |             |\n"
            "| Ignored | rule_1 |    1 | 1-1      | file_path_1 |             |\n"
            "| Ignored | rule_6 |    6 | 6-6      | file_path_6 |             |\n"
            "| Info    | rule_4 |    4 | 4-4      | file_path_4 |             |\n"
            "| Info    | rule_5 |    5 | 5-5      | file_path_5 |             |\n"
            "| Warn    | rule_3 |    3 | 3-3      | file_path_3 | See rule 3. |\n"
            "+---------+--------+------+----------+-------------+-------------+"
        ),
        call("Findings detected : Total - 6, Block - 1, Warn - 3, Info - 2"),
        call("Scan failed due to policy violations: [Block:1]"),
        call("Findings threshold check results: FAIL"),
    ]
    info_log.assert_has_calls(calls, any_order=True)
    exit_mock.assert_called_with(1)


@patch("sys.exit")
@patch("logging.Logger.info")
def test_write_findings_with_rules_and_ignore_with_directory(info_log, exit_mock):
    findings = []
    toml_rule_path = THIS_DIR.parent / "fixtures/rules.toml"
    ignore_list_path = THIS_DIR.parent / "fixtures/ignore-findings-list-for-writer.dsv"
    for i in range(1, 7):
        findings.append(
            Finding(
                file_path=f"directory_path/file_path_{i}",
                line_number=i,
                column_start=i,
                column_end=i,
                commit_id=f"commit_id_{i}",
                commit_message=f"commit_message_{i}",
                commit_timestamp=datetime.now(UTC),
                author=f"author_{i}",
                email=f"email_{i}",
                status=FindingStatus.NOT_ANALYZED,
                comment=f"comment_{i}",
                event_sent_on=datetime.now(UTC),
                rule_name=f"rule_{i}",
            )
        )

    rule_tag_provider = RuleTagProvider()
    rule_tag_provider.load(str(toml_rule_path))

    rule_comment_provider = RuleCommentProvider()
    rule_comment_provider.load(str(toml_rule_path))

    ignore_findings_providers = IgnoredListProvider(ignore_list_path)

    _ = STDOUTWriter(
        exit_code_warn=2,
        exit_code_block=1,
        working_dir="directory_path/",
        rule_tag_provider=rule_tag_provider,
        rule_comment_provider=rule_comment_provider,
        ignore_findings_providers=ignore_findings_providers,
    ).write_findings(1, 1, findings)
    calls = [
        call(
            "\n"
            "+---------+--------+------+----------+----------------------------+-------------+\n"
            "| Level   | Rule   | Line | Position | File path                  | Comment     |\n"
            "+---------+--------+------+----------+----------------------------+-------------+\n"
            "| Block   | rule_2 |    2 | 2-2      | directory_path/file_path_2 |             |\n"
            "| Ignored | rule_1 |    1 | 1-1      | directory_path/file_path_1 |             |\n"
            "| Ignored | rule_6 |    6 | 6-6      | directory_path/file_path_6 |             |\n"
            "| Info    | rule_4 |    4 | 4-4      | directory_path/file_path_4 |             |\n"
            "| Info    | rule_5 |    5 | 5-5      | directory_path/file_path_5 |             |\n"
            "| Warn    | rule_3 |    3 | 3-3      | directory_path/file_path_3 | See rule 3. |\n"
            "+---------+--------+------+----------+----------------------------+-------------+"
        ),
        call("Findings detected : Total - 6, Block - 1, Warn - 3, Info - 2"),
        call("Scan failed due to policy violations: [Block:1]"),
        call("Findings threshold check results: FAIL"),
    ]
    info_log.assert_has_calls(calls, any_order=True)
    exit_mock.assert_called_with(1)


@patch("logging.Logger.info")
def test_write_scan(info_log):
    rule_pack = "0.0.0"
    repository = RepositoryRead(
        id_=1,
        project_key="project_key",
        repository_id=str(1),
        repository_name="repository_name",
        repository_url="http://repository.url",
        vcs_instance=1,
    )
    expected_result = ScanRead(
        last_scanned_commit="NONE",
        timestamp=datetime.now(UTC),
        repository_id=str(1),
        id_=1,
        rule_pack=rule_pack,
    )
    expected_call = f"Running {expected_result.scan_type} scan on repository {repository.repository_url}"

    rule_tag_provider = RuleTagProvider()
    rule_tag_provider.load("toml_path")

    rule_comment_provider = RuleCommentProvider()
    rule_comment_provider.load("toml_path")

    result = STDOUTWriter(
        exit_code_warn=2,
        exit_code_block=1,
        rule_tag_provider=rule_tag_provider,
        rule_comment_provider=rule_comment_provider,
    ).write_scan(
        expected_result.scan_type,
        expected_result.last_scanned_commit,
        expected_result.timestamp,
        repository,
        rule_pack=rule_pack,
    )
    assert result.id_ == expected_result.id_
    assert result.repository_id == expected_result.repository_id
    assert result.rule_pack == expected_result.rule_pack
    assert result.last_scanned_commit == expected_result.last_scanned_commit
    info_log.assert_called_once_with(expected_call)


def test_get_last_scanned_commit():
    repository = RepositoryRead(
        id_=1,
        project_key="project_key",
        repository_id=str(1),
        repository_name="repository_name",
        repository_url="http://repository.url",
        vcs_instance=1,
    )
    rule_tag_provider = RuleTagProvider()
    rule_tag_provider.load("toml_path")

    rule_comment_provider = RuleCommentProvider()
    rule_comment_provider.load("toml_path")

    result = STDOUTWriter(
        exit_code_warn=2,
        exit_code_block=1,
        rule_tag_provider=rule_tag_provider,
        rule_comment_provider=rule_comment_provider,
    ).get_last_scan_for_repository(repository)
    assert result is None
