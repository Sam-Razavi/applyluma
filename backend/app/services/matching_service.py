"""Job matching algorithm — computes 0-100 match scores for user × job pairs."""
from __future__ import annotations

import re
import uuid
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.models.cv import CV
from app.models.job import RawJobPosting
from app.services.keyword_extractor import KeywordExtractor

if TYPE_CHECKING:
    pass


class MatchingService:
    """Compute weighted 0-100 match scores between a user's CV and job postings.

    Scoring weights:
        skills     40%
        experience 30%
        salary     15%
        education  10%
        location    5%
    """

    WEIGHTS = {
        "skills": 0.40,
        "experience": 0.30,
        "salary": 0.15,
        "education": 0.10,
        "location": 0.05,
    }

    def __init__(self, db: Session) -> None:
        self.db = db
        self.extractor = KeywordExtractor()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calculate_match_score(
        self,
        user_id: uuid.UUID,
        job_id: uuid.UUID,
        job_data: dict,
    ) -> dict:
        """Compute a match score for one user × job pair.

        Parameters
        ----------
        user_id:  UUID of the user
        job_id:   UUID of the raw_job_postings record
        job_data: Dict with keys: title, description, salary_min, salary_max,
                  location, remote_allowed, required_skills,
                  required_experience_years, education

        Returns
        -------
        Dict with overall_score, sub-scores, explanation, matched_skills,
        and missing_skills.
        """
        cv = (
            self.db.query(CV)
            .filter(CV.user_id == user_id, CV.is_default.is_(True))
            .first()
        )
        cv_content = cv.content if cv else ""

        # Extract skills from CV
        cv_keywords = self.extractor.extract_keywords(cv_content or "")
        cv_skills_set: set[str] = {
            item["keyword"].lower()
            for items in cv_keywords.values()
            for item in items
        }

        # Determine required skills from job
        required_skills: list[str] = list(job_data.get("required_skills") or [])
        if not required_skills and job_data.get("description"):
            job_kw = self.extractor.extract_keywords(job_data["description"])
            required_skills = self.extractor.keywords_as_flat_list(job_kw)

        matched = [s for s in required_skills if s.lower() in cv_skills_set]
        missing = [s for s in required_skills if s.lower() not in cv_skills_set]

        skills_match = self._score_skills(required_skills, cv_skills_set)

        required_yoe = int(job_data.get("required_experience_years") or 0)
        user_yoe = self._estimate_years_experience(cv_content or "")
        experience_match = self._score_experience(user_yoe, required_yoe)

        salary_match = self._score_salary(
            job_data.get("salary_min"),
            job_data.get("salary_max"),
        )
        education_match = self._score_education(
            job_data.get("education") or "",
            cv_content or "",
        )
        location_match = self._score_location(
            job_data.get("location") or "",
            bool(job_data.get("remote_allowed")),
        )

        overall = (
            skills_match * self.WEIGHTS["skills"]
            + experience_match * self.WEIGHTS["experience"]
            + salary_match * self.WEIGHTS["salary"]
            + education_match * self.WEIGHTS["education"]
            + location_match * self.WEIGHTS["location"]
        )
        overall = max(0.0, min(100.0, round(overall, 1)))

        explanation = self._build_explanation(
            matched=matched,
            missing=missing,
            user_yoe=user_yoe,
            required_yoe=required_yoe,
            job_data=job_data,
        )

        return {
            "overall_score": overall,
            "skills_match": round(skills_match, 1),
            "experience_match": round(experience_match, 1),
            "salary_match": round(salary_match, 1),
            "education_match": round(education_match, 1),
            "location_match": round(location_match, 1),
            "explanation": explanation,
            "matched_skills": matched,
            "missing_skills": missing,
        }

    def batch_compute_scores(
        self,
        user_ids: list[uuid.UUID],
        job_ids: list[uuid.UUID],
    ) -> list[dict]:
        """Compute scores for multiple user × job combinations.

        Loads job data from the DB in a single query, then iterates. Scores
        are returned (not persisted here — persistence is the caller's job).
        """
        if not user_ids or not job_ids:
            return []

        postings = (
            self.db.query(RawJobPosting)
            .filter(RawJobPosting.id.in_(job_ids))
            .all()
        )
        job_data_map = {
            posting.id: {
                "description": posting.description,
                "title": posting.title,
                "salary_min": posting.salary_min,
                "salary_max": posting.salary_max,
                "location": posting.location,
                "remote_allowed": posting.remote_allowed,
            }
            for posting in postings
        }

        results: list[dict] = []
        for user_id in user_ids:
            for job_id in job_ids:
                job_data = job_data_map.get(job_id)
                if not job_data:
                    continue
                try:
                    score = self.calculate_match_score(user_id, job_id, job_data)
                    score["user_id"] = user_id
                    score["job_id"] = job_id
                    results.append(score)
                except Exception:
                    pass
        return results

    def get_score_explanation(self, score_data: dict) -> str:
        return score_data.get("explanation", "")

    # ------------------------------------------------------------------
    # Sub-score helpers
    # ------------------------------------------------------------------

    def _score_skills(self, required: list[str], cv_skills_set: set[str]) -> float:
        if not required:
            return 70.0
        matched_count = sum(1 for s in required if s.lower() in cv_skills_set)
        return (matched_count / len(required)) * 100

    def _score_experience(self, user_yoe: int, required_yoe: int) -> float:
        if required_yoe <= 0:
            return 100.0
        if user_yoe >= required_yoe:
            return 100.0
        return min((user_yoe / required_yoe) * 100, 100.0)

    def _score_salary(
        self,
        salary_min: int | None,
        salary_max: int | None,
    ) -> float:
        if salary_min is None and salary_max is None:
            return 70.0
        return 70.0

    def _score_education(self, required_education: str, cv_content: str) -> float:
        if not required_education:
            return 100.0

        education_tiers: list[tuple[str, list[str]]] = [
            ("phd", ["phd", "doctorate", "doctoral", "doktor"]),
            ("master", ["master", "msc", "m.sc", "m.eng", "magister", "civilingenjör"]),
            ("bachelor", ["bachelor", "bsc", "b.sc", "b.eng", "degree", "university",
                          "kandidat", "högskola", "universitet"]),
        ]

        req_lower = required_education.lower()
        cv_lower = cv_content.lower()

        for _level, keywords in education_tiers:
            if any(kw in req_lower for kw in keywords):
                if any(kw in cv_lower for kw in keywords):
                    return 100.0
                return 50.0

        return 70.0

    def _score_location(self, job_location: str, remote_allowed: bool) -> float:
        if remote_allowed:
            return 80.0
        if not job_location:
            return 70.0
        return 70.0

    def _estimate_years_experience(self, cv_content: str) -> int:
        """Heuristic: extract the largest 'N years' mention in the CV text."""
        if not cv_content:
            return 0

        patterns = [
            r"(\d+)\+?\s+years?\s+(?:of\s+)?(?:experience|work|professional)",
            r"(\d+)\+?\s+år\s+(?:erfarenhet|arbetslivserfarenhet)",
            r"experience\s+(?:of\s+)?(\d+)\+?\s+years?",
        ]

        max_yoe = 0
        for pattern in patterns:
            for m in re.findall(pattern, cv_content.lower()):
                try:
                    yoe = int(m)
                    if 0 < yoe <= 50 and yoe > max_yoe:
                        max_yoe = yoe
                except ValueError:
                    pass

        return max_yoe

    # ------------------------------------------------------------------
    # Explanation builder
    # ------------------------------------------------------------------

    def _build_explanation(
        self,
        matched: list[str],
        missing: list[str],
        user_yoe: int,
        required_yoe: int,
        job_data: dict,
    ) -> str:
        parts: list[str] = []

        total_skills = len(matched) + len(missing)
        if total_skills > 0:
            matched_str = ", ".join(matched[:5]) if matched else "none"
            missing_str = ", ".join(missing[:3]) if missing else ""
            skill_line = (
                f"You have {len(matched)}/{total_skills} required skills "
                f"({matched_str} matched"
            )
            if missing_str:
                skill_line += f"; missing: {missing_str}"
            skill_line += ")."
            parts.append(skill_line)

        if required_yoe > 0:
            if user_yoe >= required_yoe:
                parts.append(
                    f"Your {user_yoe} YoE meets the {required_yoe} years required."
                )
            elif user_yoe > 0:
                parts.append(
                    f"Your {user_yoe} YoE is below the {required_yoe} years required."
                )

        salary_min = job_data.get("salary_min")
        salary_max = job_data.get("salary_max")
        if salary_min or salary_max:
            if salary_min and salary_max:
                salary_str = f"{salary_min:,}–{salary_max:,}"
            else:
                salary_str = str(salary_min or salary_max)
            parts.append(f"Salary range: {salary_str}.")

        if job_data.get("location"):
            remote_note = " (remote OK)" if job_data.get("remote_allowed") else ""
            parts.append(f"Location: {job_data['location']}{remote_note}.")

        return " ".join(parts) if parts else "Score computed from CV and job description."
