from app import run_pending_jobs, app

with app.app_context():
    run_pending_jobs()

# current process: 1106895
