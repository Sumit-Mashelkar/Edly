from app.services.validation import build_validation_report
from app.services.publishing import build_catalogue, publish_catalogue


def test_validation_report_surfaces_publish_blockers(database_session):
    report = build_validation_report(database_session)

    assert "valid" in report
    assert "issues" in report
    assert isinstance(report["issues"], list)
    assert any(issue["blocker"] for issue in report["issues"])


def test_catalogue_build_requires_valid_content(database_session):
    catalogue = build_catalogue(database_session)

    assert isinstance(catalogue, dict)
    assert "shows" in catalogue
    assert isinstance(catalogue["shows"], list)


def test_publish_fails_when_validation_blocks_it(database_session):
    result = publish_catalogue(database_session, user_id=1)

    assert result["status"] == "failed"
    assert "validation" in result["message"].lower()
