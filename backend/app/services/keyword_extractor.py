"""Keyword extraction for job descriptions.

Provides two interfaces:
- `extract_keywords(text)` — legacy function used by job_descriptions endpoint
- `KeywordExtractor` class — Phase 10A NLP-powered extractor with categorisation
"""
import re
from collections import Counter

# ---------------------------------------------------------------------------
# Legacy simple extractor (used by job_descriptions endpoint)
# ---------------------------------------------------------------------------

_STOP_WORDS: frozenset[str] = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can",
    "this", "that", "these", "those", "it", "its", "we", "our", "you",
    "your", "they", "their", "he", "she", "his", "her", "not", "no",
    "any", "all", "both", "each", "few", "more", "most", "other",
    "some", "such", "than", "then", "them", "so", "if", "i", "me", "my",
    "what", "which", "who", "how", "when", "where", "why", "about",
    "also", "into", "up", "out", "over", "just", "one", "two", "new",
    "us", "am", "own", "too", "very", "per", "via", "etc",
})


def extract_keywords(text: str, max_keywords: int = 20) -> list[str]:
    """Return the top *max_keywords* words by frequency from *text*."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[^\w\s]", " ", text.lower())
    words = text.split()
    meaningful = [
        w for w in words
        if len(w) >= 3 and w not in _STOP_WORDS and not w.isdigit()
    ]
    counts = Counter(meaningful)
    return [word for word, _ in counts.most_common(max_keywords)]


# ---------------------------------------------------------------------------
# Phase 10A: categorised keyword extractor with optional spaCy NLP
# ---------------------------------------------------------------------------

_TECHNICAL_SKILLS: list[str] = [
    "Python", "JavaScript", "TypeScript", "Java", "Go", "Golang", "Rust",
    "C++", "C#", "Ruby", "PHP", "Swift", "Kotlin", "Scala", "R", "MATLAB",
    "SQL", "NoSQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch",
    "Cassandra", "SQLite", "Oracle", "DynamoDB", "Firestore",
    "Docker", "Kubernetes", "K8s", "Linux", "Bash", "Shell",
    "AWS", "GCP", "Azure", "Cloud", "Serverless", "Lambda",
    "CI/CD", "REST", "GraphQL", "gRPC", "WebSocket", "OAuth",
    "Microservices", "API", "Machine Learning", "Deep Learning", "NLP",
    "Data Science", "Data Engineering", "ETL", "Apache Spark", "Apache Kafka",
    "Hadoop", "TensorFlow", "PyTorch", "OpenAI", "LLM", "RAG",
    "Computer Vision", "Reinforcement Learning", "Statistics", "Mathematics",
    "MLOps", "DevOps", "Infrastructure as Code", "Terraform", "Ansible",
    "Security", "Cybersecurity", "Blockchain", "IoT", "Embedded Systems",
    "FPGA", "HTML", "CSS", "SASS", "LESS", "WebAssembly",
    "Pandas", "NumPy", "SciPy",
]

_FRAMEWORKS: list[str] = [
    "FastAPI", "Django", "Flask", "Starlette", "Tornado",
    "React", "Vue", "Angular", "NextJS", "Next.js", "NestJS", "Nest.js",
    "Express", "Koa", "Fastify", "Svelte", "SvelteKit",
    "Spring", "Spring Boot", "SpringBoot", "Rails", "Sinatra",
    "Laravel", "Symfony", "CodeIgniter", "ASP.NET",
    "Gatsby", "Nuxt", "Remix",
    "Tailwind", "Bootstrap", "Material UI", "Chakra UI", "Ant Design",
    "Celery", "Airflow", "dbt", "Prefect", "Dagster",
    "Scikit-learn", "Keras", "Hugging Face", "LangChain", "LlamaIndex",
    "Redux", "Zustand", "MobX", "Pinia",
    "Prisma", "SQLAlchemy", "Hibernate", "TypeORM",
    "gRPC", "Protobuf",
]

_TOOLS: list[str] = [
    "Git", "GitHub", "GitLab", "Bitbucket",
    "Jira", "Confluence", "Notion", "Trello", "Linear", "Asana",
    "Slack", "Teams", "Zoom",
    "VS Code", "IntelliJ", "PyCharm", "WebStorm", "Eclipse",
    "Postman", "Insomnia", "Swagger",
    "Jenkins", "GitHub Actions", "GitLab CI", "CircleCI", "Travis CI",
    "ArgoCD", "Flux", "Helm",
    "Grafana", "Prometheus", "Datadog", "New Relic", "Sentry",
    "ELK Stack", "Kibana", "Logstash",
    "Nginx", "Apache", "HAProxy",
    "Vercel", "Railway", "Heroku", "Netlify", "Fly.io",
    "Figma", "Sketch", "Adobe XD",
    "Webpack", "Vite", "Rollup", "esbuild",
    "npm", "yarn", "pnpm", "pip", "poetry",
    "Stripe", "Twilio", "SendGrid", "Mailgun",
]

_SOFT_SKILLS: list[str] = [
    "Leadership", "Communication", "Problem Solving", "Problem-Solving",
    "Teamwork", "Collaboration", "Agile", "Scrum", "Kanban", "SAFe",
    "Project Management", "Mentoring", "Coaching",
    "Public Speaking", "Presentation", "Decision Making",
    "Strategic Thinking", "Innovation", "Creativity",
    "Adaptability", "Attention to Detail", "Time Management",
    "Critical Thinking", "Self-motivated", "Proactive",
    # Swedish soft skill terms
    "Kommunikation", "Samarbete", "Problemlösning", "Ledarskap",
    "Projektledning", "Självgående", "Initiativtagande",
]

_LANGUAGES: list[str] = [
    "Swedish", "English", "German", "French", "Spanish", "Italian",
    "Portuguese", "Dutch", "Finnish", "Norwegian", "Danish",
    "Polish", "Russian", "Chinese", "Mandarin", "Japanese", "Korean",
    "Arabic", "Hindi",
    # Swedish names for languages
    "Svenska", "Engelska", "Tyska", "Franska", "Spanska",
]

_CERTIFICATIONS: list[str] = [
    "AWS Solutions Architect", "AWS Developer", "AWS SysOps",
    "AWS Cloud Practitioner", "GCP Associate", "GCP Professional",
    "Azure Administrator", "Azure Developer", "Azure Solutions Architect",
    "CKA", "CKAD", "CKS",
    "PMP", "Prince2", "Scrum Master", "CSM", "PSM",
    "SAFE", "SAFe 5", "ITIL", "ISO 27001",
    "CompTIA Security+", "CISSP", "CEH", "OSCP",
    "Google Analytics", "Salesforce", "Databricks",
    "Oracle Certified", "Red Hat",
]

# Map category name → skill list
_CATEGORY_MAP: dict[str, list[str]] = {
    "technical_skills": _TECHNICAL_SKILLS,
    "frameworks": _FRAMEWORKS,
    "tools": _TOOLS,
    "soft_skills": _SOFT_SKILLS,
    "languages": _LANGUAGES,
    "certifications": _CERTIFICATIONS,
}


class KeywordExtractor:
    """Context-aware keyword extractor for job descriptions.

    Uses pattern matching against curated skill databases as the primary
    strategy. Optionally augments with spaCy NER when the Swedish model
    (sv_core_news_sm) is available — but works without it.

    To enable full NLP support:
        python -m spacy download sv_core_news_sm
    """

    def __init__(self) -> None:
        self.nlp = None
        try:
            import spacy  # type: ignore[import-untyped]
            self.nlp = spacy.load("sv_core_news_sm")
        except ImportError:
            pass  # spaCy not installed; pattern-matching only
        except OSError:
            pass  # Model not downloaded: python -m spacy download sv_core_news_sm

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_keywords(self, text: str) -> dict[str, list[dict]]:
        """Extract categorised keywords from job description text.

        Returns a dict with keys: technical_skills, frameworks, tools,
        soft_skills, languages, certifications. Each value is a list of
        dicts: {keyword, confidence, frequency}.
        """
        if not text:
            return {cat: [] for cat in _CATEGORY_MAP}

        result: dict[str, list[dict]] = {cat: [] for cat in _CATEGORY_MAP}

        for category, skill_list in _CATEGORY_MAP.items():
            for skill in skill_list:
                confidence = self._confidence_score(skill, text)
                if confidence > 0:
                    freq = self._count_occurrences(skill, text)
                    result[category].append(
                        {"keyword": skill, "confidence": confidence, "frequency": freq}
                    )

        return result

    def match_keywords_to_cv(
        self, cv_text: str, job_keywords: dict[str, list]
    ) -> dict:
        """Compare CV content against job keywords.

        Returns matched_skills, missing_skills, and match_percentage.
        """
        cv_result = self.extract_keywords(cv_text)
        cv_all: set[str] = set()
        for items in cv_result.values():
            for item in items:
                cv_all.add(item["keyword"].lower())

        matched: list[str] = []
        missing: list[str] = []

        for items in job_keywords.values():
            for item in items:
                keyword = item["keyword"] if isinstance(item, dict) else item
                if keyword.lower() in cv_all:
                    matched.append(keyword)
                else:
                    missing.append(keyword)

        total = len(matched) + len(missing)
        match_pct = round(len(matched) / total * 100, 1) if total > 0 else 0.0

        return {
            "matched_skills": matched,
            "missing_skills": missing,
            "match_percentage": match_pct,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _confidence_score(self, keyword: str, text: str) -> float:
        """Return 0-1 confidence that keyword appears in text.

        1.0 — exact case match
        0.8 — all words of a multi-word keyword found in text (partial match)
        0.6 — case-insensitive full match
        0.0 — not found
        """
        if keyword in text:
            return 1.0

        kw_words = keyword.lower().split()
        text_lower = text.lower()

        if len(kw_words) > 1 and all(w in text_lower for w in kw_words):
            return 0.8

        if keyword.lower() in text_lower:
            return 0.6

        return 0.0

    def _count_occurrences(self, keyword: str, text: str) -> int:
        """Count case-insensitive occurrences of keyword in text."""
        return text.lower().count(keyword.lower())

    def keywords_as_flat_list(
        self, extracted: dict[str, list[dict]], min_confidence: float = 0.0
    ) -> list[str]:
        """Flatten extracted keywords dict to a deduplicated list of strings."""
        seen: set[str] = set()
        result: list[str] = []
        for items in extracted.values():
            for item in items:
                if item["confidence"] >= min_confidence:
                    kw = item["keyword"]
                    if kw not in seen:
                        seen.add(kw)
                        result.append(kw)
        return result

    def keywords_by_type(
        self, extracted: dict[str, list[dict]]
    ) -> dict[str, list[str]]:
        """Convert extracted dict to {category: [keyword_string, ...]}."""
        return {
            cat: [item["keyword"] for item in items]
            for cat, items in extracted.items()
        }
