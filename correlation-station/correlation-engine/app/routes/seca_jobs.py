"""Endpoints to query SECA processing jobs and download results"""
import os
import io
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/seca-jobs/{job_id}")
async def get_job_status(job_id: str):
    jobs = globals().get('JOBS', {})
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # If this is an RQ job, attempt to get more status
    if job.get('rq_id'):
        try:
            from redis import Redis
            from rq import Queue as RQQueue
            redis_url = os.getenv('REDIS_URL')
            if redis_url:
                redis_conn = Redis.from_url(redis_url)
                q = RQQueue('seca', connection=redis_conn)
                from rq.job import Job as RQJob
                rqjob = RQJob.fetch(job['rq_id'], connection=redis_conn)
                return JSONResponse({
                    'job_id': job_id,
                    'status': rqjob.get_status(),
                    'result_path': job.get('result_path')
                })
        except Exception:
            # ignore RQ errors and fall back to stored status
            pass

    return JSONResponse({'job_id': job_id, 'status': job.get('status'), 'error': job.get('error', None)})


@router.get("/seca-jobs/{job_id}/download")
async def download_job_result(job_id: str):
    jobs = globals().get('JOBS', {})
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    result_path = job.get('result_path')
    if not result_path or not os.path.exists(result_path):
        raise HTTPException(status_code=404, detail="Result not available yet")

    def iterfile(path):
        with open(path, 'rb') as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                yield chunk

    filename = os.path.basename(result_path)
    headers = {'Content-Disposition': f'attachment; filename="{filename}"'}
    return StreamingResponse(iterfile(result_path), media_type='application/zip', headers=headers)
