"""AI-assisted job-fit assessment (thesis component; design in thesis/DESIGN.md).

A language model reads the job ad and the CV; fixed rules decide the
recommendation. Nothing in this package touches the database, so the
evaluation runner can call it exactly as the app does.
"""

from app.services.fit_advisor.decision import RULES_VERSION, Decision, decide
from app.services.fit_advisor.llm import MODEL, FitAdvisorError
from app.services.fit_advisor.prompts import PROMPT_VERSION
from app.services.fit_advisor.service import assess

__all__ = [
    "MODEL",
    "PROMPT_VERSION",
    "RULES_VERSION",
    "Decision",
    "FitAdvisorError",
    "assess",
    "decide",
]
