import json
import os
import time
from datetime import datetime, timedelta
from json import JSONDecodeError
from typing import List, Literal

import pandas as pd
import pandas_gbq
import streamlit as st
from dotenv import load_dotenv
from google.oauth2 import service_account
from sp_api.asyncio.api import Reports
from sp_api.base import (
    ApiResponse,
    ReportType,
    SellingApiBadRequestException,
    SellingApiRequestThrottledException,
)

from modules.gcloud_modules import bigquery, gcloud_connect

load_dotenv()

REFRESH_TOKEN_US = os.environ.get(
    "AMZ_REFRESH_TOKEN_US", st.secrets["AMZ_REFRESH_TOKEN_US"]
)
SELLER_ID = os.environ.get("AMZ_SELLER_ID", st.secrets["AMZ_SELLER_ID"])
MARKETPLACE_IDS = ["ATVPDKIKX0DER"]

credentials = dict(
    refresh_token=REFRESH_TOKEN_US,
    lwa_app_id=os.environ["AMZ_CLIENT_ID"],
    lwa_client_secret=os.environ["AMZ_CLIENT_SECRET"],
)

GC_CREDENTIALS = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)


async def check_and_download_report(
    response: ApiResponse | None = None, report_id: str | None = None, timeout=5
) -> dict:
    rate_limit = 0.0167
    if all([response is None, report_id is None]):
        raise ValueError("Either a response or a report ID must be provided")

    report_id = response.payload["reportId"] if response is not None else report_id
    async with Reports(credentials=credentials) as report:
        report_status_job = await report.get_report(reportId=report_id)
        report_status = report_status_job.payload

        attempt = 1

        while report_status["processingStatus"] in ("IN_PROGRESS", "IN_QUEUE"):
            attempt += 1
            print(f"Waiting for {timeout} seconds, attempt # {attempt}")
            time.sleep(timeout)
            report_status_job = await report.get_report(reportId=report_id)
            report_status = report_status_job.payload

            print(f"report status: {report_status['processingStatus']}")

        if report_status["processingStatus"] == "DONE":
            try:
                report_document_obj = await report.get_report_document(
                    reportDocumentId=report_status["reportDocumentId"],
                    download=True,
                    timeout=timeout,
                )
                try:
                    report_document = json.loads(
                        report_document_obj.payload["document"]
                    )
                except JSONDecodeError:
                    report_document = report_document_obj.payload["document"]
            except SellingApiRequestThrottledException:
                print(f"Hit rate limits, sleeping for {int(1/rate_limit)+2} seconds")
                time.sleep(int(1 / rate_limit) + 2)
                report_status = await check_and_download_report(
                    report_id=report_id, timeout=int(1 / rate_limit) + 2
                )
                report_document = report_status["document"]

            except Exception as e:
                print(
                    f"Unknown error occurred, cooling down and retrying.\n Error: {e}"
                )
                time.sleep(int(1 / rate_limit) + 2)
                report_status = await check_and_download_report(
                    report_id=report_id, timeout=int(1 / rate_limit) + 2
                )
                report_document = report_status["document"]

            print(f"document id: {report_status['reportDocumentId']}")
        else:
            print(f"report status: {report_status['processingStatus']}")
            return {"status": report_status["processingStatus"], "document": ""}
        return {
            "status": report_status["processingStatus"],
            "document": report_document,
        }


def chunk_asins(asins: str | list, chunk_size: int = 18) -> list:
    asins_list = asins.split() if isinstance(asins, str) else asins
    clean_asins = []
    for chunk in range(0, len(asins_list), chunk_size):
        asins_str = asins_list[chunk : chunk + chunk_size]
        clean_asins.append(" ".join(asins_str))
    return clean_asins


async def fetch_reports(
    report_types: list = [
        ReportType.GET_BRAND_ANALYTICS_SEARCH_CATALOG_PERFORMANCE_REPORT
    ],
    processing_statuses: List[
        Literal["CANCELLED", "DONE", "FATAL", "IN_PROGRESS", "IN_QUEUE"]
    ] = [],
    created_since=None,
    created_before=None,
):
    """
    Queries Amazon for already created report for the time period.
    """
    sleep_time = round(1 / 0.0222, 2) + 1
    all_reports = []
    async with Reports(credentials=credentials) as report:
        r = await report.get_reports(
            reportTypes=report_types,
            processingStatuses=processing_statuses,
            createdSince=created_since,
            createdUntil=created_before,
            pageSize=100,
        )
    all_reports.extend(r.payload["reports"])
    next_token = r.next_token
    page = 2
    while next_token:
        print(
            f"Pulling next page ({page}), sleeping for {sleep_time} seconds. Currently {len(all_reports)} reports colected"
        )
        time.sleep(sleep_time)
        try:
            async with Reports(credentials=credentials) as report:
                r = await report.get_reports(nextToken=next_token)
                all_reports.extend(r.payload["reports"])
                next_token = r.next_token
                page += 1
        except (SellingApiBadRequestException, SellingApiRequestThrottledException):
            print(f"Ran out of limits, waiting for {sleep_time} seconds")
            time.sleep(sleep_time)
        except Exception as e:
            print(f"Unknown error: {e}")
    return all_reports


async def check_if_ba_report_exists(document):
    asins = document["reportSpecification"].get("reportOptions", {}).get("asin")
    print("Checking asins: ")
    print(asins)
    asins = [x.strip() for x in asins.split()]
    start_date = datetime.strptime(
        document["reportSpecification"].get("dataStartTime"), "%Y-%m-%d"
    ).date()
    period = (
        document["reportSpecification"].get("reportOptions", {}).get("reportPeriod")
    )

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("asins", "STRING", asins),
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
            bigquery.ScalarQueryParameter("period", "STRING", period),
        ]
    )
    query = """
    SELECT DISTINCT asin
    FROM `mellanni-project-da.auxillary_development.sqp_asin_weekly`
    WHERE DATE(startDate) = @start_date
      AND period = @period
      AND asin IN UNNEST(@asins)
      """

    with gcloud_connect() as client:
        bq_result = client.query(query, job_config=job_config)
    duplicate_asins = {x.asin for x in bq_result}
    unique_asins = [x for x in asins if x not in duplicate_asins]
    if duplicate_asins:
        print(
            f"[[DUPLICATES]] {len(duplicate_asins)} duplicate asins found for {start_date} {period}: ",
            ", ".join(duplicate_asins),
        )
    if unique_asins:
        print(
            f"[[UNIQUE]] {len(unique_asins)} unique asins found for {start_date} {period}: ",
            ", ".join(unique_asins),
        )
    return unique_asins


def process_document(document):
    result = pd.DataFrame()
    columns = dict()

    def process_row(row, prefix=None):
        for key, value in row.items():
            if isinstance(value, dict):
                process_row(value, prefix=key)
            else:
                key = f"{prefix}_{key}" if prefix else key
                columns[key] = value
        return columns

    for row in document["dataByAsin"]:
        columns = process_row(row)
        result = pd.concat(
            [
                result,
                pd.DataFrame(data=[columns.values()], columns=pd.Index(columns.keys())),
            ]
        )
    period = (
        document["reportSpecification"].get("reportOptions", {}).get("reportPeriod")
    )
    asins = document["reportSpecification"].get("reportOptions", {}).get("asin")
    asins = [x.strip() for x in asins.split()]

    start_date = datetime.strptime(
        document["reportSpecification"].get("dataStartTime"), "%Y-%m-%d"
    ).date()
    marketplaces = document["reportSpecification"].get("marketplaceIds", [])

    if len(document["dataByAsin"]) == 0:

        result["asin"] = asins
        result["startDate"] = start_date

    result["period"] = period
    result["marketplaces"] = ", ".join(sorted(marketplaces))
    return result


async def upload_ba_report(document):
    if not document or document == "":
        return {"status": "failed", "error": "document is empty"}
    try:
        unique_asins_job = check_if_ba_report_exists(document)
        report_df = process_document(document)

        unique_asins = await unique_asins_job

        report_to_upload = report_df.loc[report_df["asin"].isin(unique_asins)]
        if len(report_to_upload) == 0:
            print("[[RESULT]] All records are duplicates, skipping")
        else:
            print(f"[[RESULT]] Uploading {len(report_to_upload)} rows to bigquery")
            pandas_gbq.to_gbq(
                dataframe=report_to_upload,
                project_id="mellanni-project-da",
                destination_table="mellanni-project-da.auxillary_development.sqp_asin_weekly",
                credentials=GC_CREDENTIALS,
                if_exists="append",
            )
        return {"status": "success"}
    except Exception as e:
        return {"status": "failed", "error": e}


def convert_date_to_isoformat(date_raw: str | datetime) -> str:
    if isinstance(date_raw, datetime):
        return date_raw.isoformat()
    elif isinstance(date_raw, str):
        date_clean = datetime.strptime(date_raw, "%Y-%m-%d")
        return date_clean.isoformat()


async def collect_sqp_reports(created_since, created_before):
    print(f"[[DATE: {created_since} to {created_before}]]")
    created_since = (
        convert_date_to_isoformat(created_since)
        if isinstance(created_since, datetime)
        else created_since
    )
    created_before = (
        convert_date_to_isoformat(created_before)
        if isinstance(created_before, datetime)
        else created_before
    )

    try:
        all_reports = await fetch_reports(
            report_types=[
                ReportType.GET_BRAND_ANALYTICS_SEARCH_QUERY_PERFORMANCE_REPORT
            ],
            processing_statuses=["DONE"],
            created_since=created_since,
            created_before=created_before,
        )
        for i, report_record in enumerate(all_reports, start=1):
            document_status = await check_and_download_report(
                report_id=report_record["reportId"]
            )
            if document_status["status"] == "DONE":
                _ = await upload_ba_report(document=document_status["document"])
                print(f"Uploaded {i} reports of {len(all_reports)}", end="\n\n")
    except Exception as e:
        print(f"[[ERROR for {str(e)}]]: {e}\nRetrying...")
        await collect_sqp_reports(
            created_since=created_since,
            created_before=created_before,
        )


async def run_sqp_reports(date_asin_dict: dict[str | datetime, str | list]) -> list:
    """
    Downloads SQP reports for a given selection of dates and for a given set of ASINs.
    ASINs are chunked 18 at a time.
    """
    failed_reports = []

    clean_date_asin_dict = {
        convert_date_to_isoformat(start_date): chunk_asins(asin_list)
        for start_date, asin_list in date_asin_dict.items()
    }

    try:
        ba_report_jobs = {}
        for week_start, asin_list in clean_date_asin_dict.items():
            for asin_chunk in asin_list:
                ba_report_jobs[week_start, asin_chunk] = brand_analytics_report(
                    week_start=week_start,
                    report_type=ReportType.GET_BRAND_ANALYTICS_SEARCH_QUERY_PERFORMANCE_REPORT,
                    asin=asin_chunk,
                )

        responses = {}
        for date_asin, ba_report_job in ba_report_jobs.items():
            responses[date_asin] = await ba_report_job

        document_jobs = {}
        for date_asin, response in responses.items():
            document_jobs[date_asin] = check_and_download_report(response=response)

        report_documents = {}
        for date_asin, document_job in document_jobs.items():
            report_documents[date_asin] = await document_job

        ba_uploads = {}
        for date_asin, report_document in report_documents.items():
            if report_document["status"] == "FATAL":
                failed_reports.append(date_asin)
            else:
                ba_uploads[date_asin] = upload_ba_report(report_document)

        for date_asin, ba_upload in ba_uploads.items():
            await ba_upload
    except ValueError as e:
        print(f"Wrong date submitted: {e}")
    except Exception as e:
        print(f"Error while creating sqp reports: {e}")
    return failed_reports


def get_last_sunday(date: datetime | None = None, day_delta: int = 7):
    if not date:
        date = datetime.now()
    if not isinstance(date, datetime):
        raise BaseException("Date must be in datetime format")
    delta = date.isocalendar().weekday + day_delta
    last_sunday = date - timedelta(days=delta)
    return last_sunday


async def brand_analytics_report(
    week_start: datetime | str | None = None,
    report_type: Literal[
        ReportType.GET_BRAND_ANALYTICS_SEARCH_CATALOG_PERFORMANCE_REPORT,
        ReportType.GET_BRAND_ANALYTICS_SEARCH_QUERY_PERFORMANCE_REPORT,
    ] = ReportType.GET_BRAND_ANALYTICS_SEARCH_CATALOG_PERFORMANCE_REPORT,
    asin: str | None = None,
    timeout=round(1 / 0.0167, 1) + 1,
):
    """
    Creates a brand analytics report - search query performance or search catalog performance.
    """

    if not week_start:
        week_start = get_last_sunday(datetime.now())
    if isinstance(week_start, str):
        week_start = datetime.strptime(week_start.split("T")[0], "%Y-%m-%d")
    if not week_start.weekday() == 6:
        week_start = get_last_sunday(week_start, day_delta=0)

    if (datetime.now() - week_start).days < 8:
        raise ValueError(f"The reports are not ready for {week_start.date()} yet")

    report_options = {
        "reportPeriod": "WEEK",
    }

    if report_type == ReportType.GET_BRAND_ANALYTICS_SEARCH_QUERY_PERFORMANCE_REPORT:
        if not asin:
            raise BaseException("ASIN was not provided!")
        report_options["asin"] = asin

    try:
        async with Reports(credentials=credentials) as report:
            response = await report.create_report(
                reportType=report_type,
                reportOptions=report_options,
                dataStartTime=str(week_start.date()),
                dataEndTime=str(week_start.date() + timedelta(days=6)),
                marketplaceIds=MARKETPLACE_IDS,
            )
    except (SellingApiBadRequestException, SellingApiRequestThrottledException) as e:
        print(f"Ran into rate limits, waiting for {timeout} seconds. {e}")
        time.sleep(timeout)
        response = await brand_analytics_report(
            week_start=week_start, report_type=report_type, asin=asin
        )

    report_id = response.payload["reportId"]
    print(f"report id: {report_id}")
    return response
