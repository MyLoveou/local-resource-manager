CREATE INDEX IF NOT EXISTS idx_scrape_jobs_resource_id ON scrape_jobs(resource_id, id DESC);
CREATE INDEX IF NOT EXISTS idx_candidates_job_id ON candidates(job_id);
