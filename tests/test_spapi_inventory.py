from datetime import datetime, timezone

import pandas as pd

from modules import spapi_inventory as inv


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload


class FakeReportsClient:
    def __init__(self, reports=None, statuses=None, document="sku\tasin\tafn-fulfillable-quantity\tafn-total-quantity\nS1\tA1\t7\t12\n"):
        self.reports = reports or []
        self.statuses = list(statuses or [])
        self.document = document
        self.created = 0
        self.polled = 0
        self.downloaded = 0

    def get_reports(self, **_kwargs):
        return FakeResponse({"reports": self.reports})

    def create_report(self, **_kwargs):
        self.created += 1
        return FakeResponse({"reportId": "new-report"})

    def get_report(self, reportId):
        self.polled += 1
        if self.statuses:
            return FakeResponse(self.statuses.pop(0))
        return FakeResponse({"reportId": reportId, "processingStatus": "DONE", "reportDocumentId": "doc-new"})

    def get_report_document(self, **_kwargs):
        self.downloaded += 1
        return FakeResponse({"document": self.document})


def test_latest_same_day_completed_report_reused():
    client = FakeReportsClient(
        reports=[
            {
                "reportId": "old",
                "reportType": inv.REPORT_TYPE_NAME,
                "processingStatus": "DONE",
                "createdTime": "2026-06-08T23:00:00Z",
                "reportDocumentId": "doc-old",
            },
            {
                "reportId": "today",
                "reportType": inv.REPORT_TYPE_NAME,
                "processingStatus": "DONE",
                "createdTime": "2026-06-09T14:00:00Z",
                "reportDocumentId": "doc-today",
            },
        ]
    )

    report = inv._latest_completed_same_day_report(client, now_utc=datetime(2026, 6, 9, 15, tzinfo=timezone.utc))

    assert report["reportId"] == "today"
    assert client.created == 0


def test_latest_same_day_completed_report_ignores_in_progress():
    client = FakeReportsClient(
        reports=[
            {
                "reportId": "pending",
                "reportType": inv.REPORT_TYPE_NAME,
                "processingStatus": "IN_PROGRESS",
                "createdTime": "2026-06-09T14:00:00Z",
            }
        ]
    )

    report = inv._latest_completed_same_day_report(client, now_utc=datetime(2026, 6, 9, 15, tzinfo=timezone.utc))

    assert report is None


def test_wait_for_report_done_times_out_cleanly():
    client = FakeReportsClient(statuses=[{"processingStatus": "IN_PROGRESS"}])

    try:
        inv._wait_for_report_done(client, "r1", poll_seconds=0, max_wait_seconds=0)
    except TimeoutError as exc:
        assert str(exc) == inv.SP_TIMEOUT_MESSAGE
    else:
        raise AssertionError("expected timeout")


def test_download_report_dataframe_parses_tsv():
    client = FakeReportsClient()

    df = inv._download_report_dataframe(client, "doc")

    assert df.iloc[0]["sku"] == "S1"
    assert df.iloc[0]["afn-total-quantity"] == 12


def _patch_reports(monkey_client):
    original_reports = inv.Reports
    original_credentials = inv.get_spapi_credentials
    inv.Reports = lambda credentials: monkey_client
    inv.get_spapi_credentials = lambda: {"refresh_token": "x", "lwa_app_id": "x", "lwa_client_secret": "x"}
    return original_reports, original_credentials


def _restore_reports(original_reports, original_credentials):
    inv.Reports = original_reports
    inv.get_spapi_credentials = original_credentials


def test_request_inventory_report_reuses_same_day_by_default():
    client = FakeReportsClient(
        reports=[
            {
                "reportId": "today",
                "reportType": inv.REPORT_TYPE_NAME,
                "processingStatus": "DONE",
                "createdTime": datetime.now(timezone.utc).isoformat(),
                "reportDocumentId": "doc-today",
            }
        ]
    )
    original_reports, original_credentials = _patch_reports(client)
    try:
        result = inv.request_inventory_report()
    finally:
        _restore_reports(original_reports, original_credentials)

    assert result.report_id == "today"
    assert client.created == 0
    assert client.downloaded == 1


def test_request_inventory_report_force_fresh_bypasses_reusable_report():
    client = FakeReportsClient(
        reports=[
            {
                "reportId": "today",
                "reportType": inv.REPORT_TYPE_NAME,
                "processingStatus": "DONE",
                "createdTime": datetime.now(timezone.utc).isoformat(),
                "reportDocumentId": "doc-today",
            }
        ],
        statuses=[{"reportId": "new-report", "processingStatus": "DONE", "reportDocumentId": "doc-new"}],
    )
    original_reports, original_credentials = _patch_reports(client)
    try:
        result = inv.request_inventory_report(force_fresh=True)
    finally:
        _restore_reports(original_reports, original_credentials)

    assert result.report_id == "new-report"
    assert client.created == 1
    assert client.polled == 1


def test_request_inventory_report_force_fresh_timeout_falls_back_to_reusable_report():
    client = FakeReportsClient(
        reports=[
            {
                "reportId": "today",
                "reportType": inv.REPORT_TYPE_NAME,
                "processingStatus": "DONE",
                "createdTime": datetime.now(timezone.utc).isoformat(),
                "reportDocumentId": "doc-today",
            }
        ],
        statuses=[{"reportId": "new-report", "processingStatus": "IN_PROGRESS"}],
    )
    original_reports, original_credentials = _patch_reports(client)
    try:
        result = inv.request_inventory_report(force_fresh=True, poll_seconds=0, max_wait_seconds=0)
    finally:
        _restore_reports(original_reports, original_credentials)

    assert result.report_id == "today"
    assert client.created == 1
