from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .config import settings
from .schemas import AnalysisCreate, AnalysisResult


def _connect() -> psycopg.Connection:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not configured")
    return psycopg.connect(settings.database_url, row_factory=dict_row)


def save_analysis(owner_id: str, request: AnalysisCreate, result: AnalysisResult) -> None:
    request_json = request.model_dump(mode="json")
    result_json = result.model_dump(mode="json")

    with _connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "select organization_id from public.profiles where id = %s",
                (owner_id,),
            )
            profile = cursor.fetchone()
            organization_id = profile["organization_id"] if profile else None

            cursor.execute(
                """
                insert into public.analysis_jobs (
                    analysis_id, owner_id, organization_id,
                    athlete_id, athlete_name, lane,
                    event, phase, video_object_key, status,
                    request_payload, model_output,
                    model_version, contract_version,
                    started_at, completed_at
                ) values (
                    %(analysis_id)s, %(owner_id)s, %(organization_id)s,
                    %(athlete_id)s, %(athlete_name)s, %(lane)s,
                    %(event)s, %(phase)s, %(video_object_key)s, %(status)s,
                    %(request_payload)s::jsonb, %(model_output)s::jsonb,
                    %(model_version)s, %(contract_version)s,
                    now(), now()
                )
                on conflict (analysis_id) do update set
                    status = excluded.status,
                    model_output = excluded.model_output,
                    model_version = excluded.model_version,
                    completed_at = excluded.completed_at
                """,
                {
                    "analysis_id": result.analysis_id,
                    "owner_id": owner_id,
                    "organization_id": organization_id,
                    "athlete_id": request.athlete_id,
                    "athlete_name": request.athlete_name,
                    "lane": request.lane,
                    "event": request.event.value,
                    "phase": request.phase,
                    "video_object_key": request.video_object_key,
                    "status": result.status.value,
                    "request_payload": Jsonb(request_json),
                    "model_output": Jsonb(result_json),
                    "model_version": result.model_version,
                    "contract_version": result.contract_version,
                },
            )


def load_analysis(owner_id: str, analysis_id: str) -> AnalysisResult | None:
    with _connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select model_output
                from public.analysis_jobs
                where owner_id = %s and analysis_id = %s
                """,
                (owner_id, analysis_id),
            )
            row: dict[str, Any] | None = cursor.fetchone()

    if not row or not row["model_output"]:
        return None
    return AnalysisResult.model_validate(row["model_output"])
