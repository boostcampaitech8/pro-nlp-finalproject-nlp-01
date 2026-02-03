import os
import subprocess
import logging
from typing import Optional
from common.config import settings

logger = logging.getLogger(__name__)

class JobService:
    def __init__(self):
        self.project_id = settings.GCP_PROJECT_ID
        self.region = settings.GCP_REGION
        self.job_name = settings.CLOUD_RUN_JOB_NAME
        self.env = settings.ENV

    def trigger_job(self, task: str, target_id: Optional[int] = None, **kwargs):
        """
        Triggers a Cloud Run Job or runs it locally depending on the environment.
        """
        if self.env in ["production", "preview"]:
            return self._trigger_cloud_run_job(task, target_id, **kwargs)
        else:
            return self._trigger_local_job(task, target_id, **kwargs)

    def trigger_portfolio_extraction(self, portfolio_id: int):
        return self.trigger_job(task="portfolio_extraction", target_id=portfolio_id)

    def trigger_portfolio_analysis(self, portfolio_id: int):
        return self.trigger_job(task="portfolio_analysis", target_id=portfolio_id)

    def trigger_profile_update(self, portfolio_id: int):
        return self.trigger_job(task="profile_update", target_id=portfolio_id)

    def trigger_portfolio_embedding(self, portfolio_id: int):
        return self.trigger_job(task="portfolio_embedding", target_id=portfolio_id)

    def trigger_cover_letter_generation(self, cover_letter_id: int, **kwargs):
        return self.trigger_job(task="cover_letter_generation", target_id=cover_letter_id, **kwargs)

    def trigger_recruit_indexing(self):
        return self.trigger_job(task="recruit_indexing")

    def trigger_cover_letter_item_headline(self, item_id: int):
        return self.trigger_job(task="cover_letter_item_headline", target_id=item_id)

    def trigger_cover_letter_item_refine(self, item_id: int):
        return self.trigger_job(task="cover_letter_item_refine", target_id=item_id)

    def trigger_recommendation_update(self, user_id: Optional[int] = None, **kwargs):
        return self.trigger_job(task="recruit_update", target_id=user_id, **kwargs)

    def _trigger_cloud_run_job(self, task: str, target_id: Optional[int] = None, **kwargs):
        """
        Triggers a Google Cloud Run Job using the official SDK with retry logic.
        """
        logger.info(f"Triggering Cloud Run Job '{self.job_name}': task={task}, id={target_id}")
        
        if not self.project_id:
            logger.error("GCP_PROJECT_ID is not set. Cannot trigger Cloud Run Job.")
            return False

        max_retries = 3
        for attempt in range(max_retries):
            try:
                from google.cloud import run_v2
                
                client = run_v2.JobsClient()
                
                # Prepare arguments for the container
                args = [f"--task={task}"]
                if target_id:
                    args.append(f"--id={target_id}")
                
                # OPTIONAL: Pass kwargs as environment variables
                # The container expects env vars like JOB_EXTRA_TONE, JOB_EXTRA_MODE
                env_vars = []
                for k, v in kwargs.items():
                    env_key = f"JOB_EXTRA_{k.upper()}"
                    env_val = str(v)
                    env_vars.append({"name": env_key, "value": env_val})
                
                # Formatting job path: projects/{project}/locations/{location}/jobs/{job}
                job_path = f"projects/{self.project_id}/locations/{self.region}/jobs/{self.job_name}"
                
                request = run_v2.RunJobRequest(
                    name=job_path,
                    overrides={
                        "container_overrides": [
                            {
                                "args": args,
                                "env": env_vars
                            }
                        ]
                    }
                )
                
                operation = client.run_job(request=request)
                logger.info(f"Cloud Run Job triggered (Attempt {attempt+1}). Operation: {operation.operation.name}")
                return True
                
            except Exception as e:
                logger.warning(f"Failed to trigger Cloud Run Job (Attempt {attempt+1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    logger.error(f"Final failure to trigger Cloud Run Job: {e}")
                    return False
                import time
                time.sleep(2 ** attempt) # Exponential backoff
        return False

    def _trigger_local_job(self, task: str, target_id: Optional[int] = None, **kwargs):
        """
        Runs the job script locally in a detached process for development.
        """
        logger.info(f"Triggering Local Job: task={task}, id={target_id}, extra={kwargs}")
        
        args = [
            "python", 
            "jobs/run_job.py", 
            "--task", task
        ]
        if target_id:
            args.extend(["--id", str(target_id)])
        
        # Pass extra kwargs as environment variables for simplicity in subprocess
        env = os.environ.copy()
        for k, v in kwargs.items():
            env[f"JOB_EXTRA_{k.upper()}"] = str(v)

        try:
            # Run as detached process
            subprocess.Popen(args, cwd=os.getcwd(), env=env)
            logger.info(f"Local job started: {' '.join(args)}")
            return True
        except Exception as e:
            logger.error(f"Failed to start local job: {e}")
            return False

job_service = JobService()
