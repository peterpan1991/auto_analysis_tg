from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from schemas.analysis_schema import (
    AnalysisResponse,
    AnalysisResultResponse,
    AnalyzeStatusResponse,
    AnalyzeLogsResponse,
    CancelResponse,
)
from core.database import get_db
import services.analysis_service as analysis_service
import repository

router = APIRouter()

@router.post("/tasks/{task_id}/analyze", response_model=AnalysisResponse)
def analyze_chat(task_id: int, db: Session = Depends(get_db)):
    task = repository.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if not analysis_service.is_task_analyzable(task):
        raise HTTPException(status_code=400, detail="任务状态不允许分析")

    success, error = analysis_service.start_analysis(db, task_id, task.status)

    if not success:
        if "不存在" in error:
            raise HTTPException(status_code=404, detail=error)
        raise HTTPException(status_code=400, detail=error)

    return AnalysisResponse(result_count=0)

@router.get("/tasks/{task_id}/analyze-status", response_model=AnalyzeStatusResponse)
def get_analyze_status(task_id: int, db: Session = Depends(get_db)):
    status, _ = analysis_service.get_task_status(db, task_id)

    if status == "not_found":
        return AnalyzeStatusResponse(
            status="not_found",
            result_count=0,
            logs=[],
            error=None
        )

    if status == 'completed':
        result_count = repository.count_by_task(db, task_id)
        return AnalyzeStatusResponse(
            status="completed",
            result_count=result_count,
            logs=[],
            error=None
        )

    if status == 'analyzing':
        task_status = analysis_service.get_analysis_status(task_id)
        if task_status["status"] != "not_found":
            return AnalyzeStatusResponse(
                status=task_status["status"],
                result_count=task_status.get("result_count", 0),
                logs=task_status.get("logs", []),
                error=task_status.get("error")
            )
        return AnalyzeStatusResponse(
            status="running",
            result_count=0,
            logs=[],
            error=None
        )

    return AnalyzeStatusResponse(
        status="not_found",
        result_count=0,
        logs=[],
        error=None
    )

@router.get("/tasks/{task_id}/analyze-logs", response_model=AnalyzeLogsResponse)
def get_analyze_logs(task_id: int):
    logs = analysis_service.get_analysis_logs(task_id)
    return AnalyzeLogsResponse(logs=logs)

@router.post("/tasks/{task_id}/analyze/cancel", response_model=CancelResponse)
def cancel_analyze(task_id: int):
    analysis_service.cancel_analysis(task_id)
    return CancelResponse(message="取消请求已发送")

@router.get("/tasks/{task_id}/analysis", response_model=List[AnalysisResultResponse])
def get_analysis_results(task_id: int, db: Session = Depends(get_db)):
    results = analysis_service.get_analysis_results(db, task_id)

    return [
        AnalysisResultResponse(
            id=row["id"],
            task_id=row["task_id"],
            result_type=row["result_type"],
            content=row["content"],
            created_at=row["created_at"],
        )
        for row in results
    ]
