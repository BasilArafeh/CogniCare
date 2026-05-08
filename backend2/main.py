from fastapi import FastAPI

from routers import (
    agent_test,
    auth,
    notifications,
    patients,
    reports,
    speech,
    system,
    twilio_webhooks,
)

app = FastAPI()

app.include_router(system.router)
app.include_router(patients.router)
app.include_router(auth.router)
app.include_router(speech.router)
app.include_router(notifications.router)
app.include_router(twilio_webhooks.router)
app.include_router(agent_test.router)
app.include_router(reports.router)