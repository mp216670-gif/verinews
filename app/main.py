import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.article import Article, ArticleStatus
from app.models.verification import Claim, ClaimVerdict, VerificationReport, ReviewerDecision
from app.models.trust_score import TrustScore
from app.services.trust_scoring.scorer import TrustScoringEngine
from app.api.routes import router


def seed_initial_data():
    """Seed demo accounts and sample news articles if database is empty."""
    db = SessionLocal()
    try:
        # 1. Seed demo accounts
        admin = db.query(User).filter(User.username == "demo_admin").first()
        if not admin:
            admin = User(
                username="demo_admin",
                email="admin@verinews.com",
                hashed_password=hash_password("AdminPass123!"),
                role=UserRole.ADMIN,
                is_active=True,
            )
            db.add(admin)

        reporter = db.query(User).filter(User.username == "demo_reporter").first()
        if not reporter:
            reporter = User(
                username="demo_reporter",
                email="reporter@verinews.com",
                hashed_password=hash_password("ReporterPass123!"),
                role=UserRole.REPORTER,
                is_active=True,
            )
            db.add(reporter)

        reader = db.query(User).filter(User.username == "demo_reader").first()
        if not reader:
            reader = User(
                username="demo_reader",
                email="reader@verinews.com",
                hashed_password=hash_password("ReaderPass123!"),
                role=UserRole.READER,
                is_active=True,
            )
            db.add(reader)

        db.commit()

        # 2. Seed initial demonstration articles if none exist
        if db.query(Article).count() == 0:
            scoring_engine = TrustScoringEngine()

            demo_stories = [
                {
                    "title": "Global Renewable Energy Additions Surge by 50% in Record Year, IEA Confirms",
                    "content": (
                        "Global renewable electricity capacity additions jumped by 50% to almost 510 gigawatts, "
                        "according to the International Energy Agency's annual market review. "
                        "The report confirmed solar photovoltaic systems accounted for three-quarters of new additions worldwide. "
                        "Experts stated in official records that international policy incentives drove unprecedented solar farm installations."
                    ),
                    "summary": "The International Energy Agency confirms a 50% surge in global renewable additions, led by rapid solar PV expansion.",
                    "source_url": "https://www.reuters.com/sustainability/renewables-surge-iea-record-year",
                    "publisher": "Reuters",
                    "author": "David Evans",
                    "category": "Climate",
                    "image_url": "https://images.unsplash.com/photo-1497435334941-8c899ee9e8e9?auto=format&fit=crop&w=1200&q=80",
                    "status": ArticleStatus.VERIFIED,
                    "published_at": datetime.now(timezone.utc) - timedelta(hours=3),
                    "claims": [
                        ("Global renewable electricity capacity additions jumped by 50% to almost 510 gigawatts.", ClaimVerdict.TRUE, 0.94, "IEA Renewables 2024 Market Report", "Directly corroborated by published annual IEA market report statistics."),
                        ("Solar photovoltaic systems accounted for three-quarters of new additions worldwide.", ClaimVerdict.TRUE, 0.91, "IEA Official Release data tables", "Empirical assertion substantiated by grid connection datasets."),
                    ],
                    "report_verdict": "Verified / Supported",
                    "notes": "Accredited wire reporting; empirical figures cross-referenced with IEA tables.",
                    "adj": 0.0,
                    "decision": ReviewerDecision.APPROVED,
                },
                {
                    "title": "Next-Gen Quantum Processors Demonstrate Error Mitigation Milestones in Peer-Reviewed Trial",
                    "content": (
                        "Researchers at leading international laboratories have demonstrated physical quantum processors capable of algorithmic fault tolerance. "
                        "According to findings published in Nature, quantum coherence times improved tenfold through topological surface codes. "
                        "Scientists confirmed in peer-reviewed benchmarks that complex molecular simulation runtimes decreased from weeks to seconds."
                    ),
                    "summary": "Physical quantum processors achieve algorithmic fault tolerance, according to peer-reviewed benchmark datasets published in Nature.",
                    "source_url": "https://www.nature.com/articles/s41586-quantum-benchmark-2026",
                    "publisher": "Nature",
                    "author": "Dr. Helena Thorne",
                    "category": "Technology",
                    "image_url": "https://images.unsplash.com/photo-1635070041078-e363dbe005cb?auto=format&fit=crop&w=1200&q=80",
                    "status": ArticleStatus.VERIFIED,
                    "published_at": datetime.now(timezone.utc) - timedelta(hours=8),
                    "claims": [
                        ("Quantum coherence times improved tenfold through topological surface codes.", ClaimVerdict.TRUE, 0.92, "Nature Physics Publication Archive", "Verified against peer-reviewed experimental datasets and hardware benchmarks."),
                        ("Molecular simulation runtimes decreased from weeks to seconds.", ClaimVerdict.TRUE, 0.88, "Oak Ridge National Laboratory Test Records", "Empirical assertion confirmed across independent compute clusters."),
                    ],
                    "report_verdict": "Verified / Supported",
                    "notes": "Peer-reviewed scientific source with replicable benchmark datasets.",
                    "adj": 0.0,
                    "decision": ReviewerDecision.APPROVED,
                },
                {
                    "title": "International Maritime Treaty Signed by 42 Nations to Shield Deep Seabed Ecosystems",
                    "content": (
                        "Diplomats from 42 coastal nations ratified a legally binding treaty prohibiting unauthorized industrial exploitation of benthic marine trenches. "
                        "The Associated Press confirmed that environmental protection zones will encompass over 12 million square kilometers of international waters. "
                        "Official statements released by maritime delegations noted that autonomous monitoring buoys will enforce compliance."
                    ),
                    "summary": "A coalition of 42 nations enacts enforceable protections over 12 million square kilometers of deep seabed ecosystems.",
                    "source_url": "https://apnews.com/article/un-ocean-seabed-treaty-conservation",
                    "publisher": "Associated Press",
                    "author": "Mateo Ramirez",
                    "category": "World",
                    "image_url": "https://images.unsplash.com/photo-1544551763-46a013bb70d5?auto=format&fit=crop&w=1200&q=80",
                    "status": ArticleStatus.VERIFIED,
                    "published_at": datetime.now(timezone.utc) - timedelta(hours=14),
                    "claims": [
                        ("42 coastal nations ratified a legally binding deep seabed protection treaty.", ClaimVerdict.TRUE, 0.93, "UN Treaty Collection Registry", "Official diplomatic treaty depository confirms formal ratifications."),
                        ("Environmental protection zones will encompass over 12 million square kilometers.", ClaimVerdict.TRUE, 0.89, "AP News Maritime Dispatch", "Geographical boundaries cross-referenced with maritime jurisdictional charts."),
                    ],
                    "report_verdict": "Verified / Supported",
                    "notes": "Confirmed diplomatic treaty with official UN depository records.",
                    "adj": 0.0,
                    "decision": ReviewerDecision.APPROVED,
                },
                {
                    "title": "Central Banks Finalize Sovereign Interoperability Framework for Cross-Border Settlement",
                    "content": (
                        "The Bank for International Settlements announced completion of bilateral testing for instant cross-border settlement architecture. "
                        "According to reporting by the Financial Times, transaction friction and foreign exchange conversion costs fell by 40% during trial runs. "
                        "Federal monetary authorities stated in press releases that commercial banks will begin sandbox deployment next quarter."
                    ),
                    "summary": "Central banks conclude multilateral trials reducing foreign exchange conversion costs by 40% using digital settlement bridges.",
                    "source_url": "https://www.ft.com/content/central-banks-settlement-crossborder",
                    "publisher": "Financial Times",
                    "author": "Claire Sterling",
                    "category": "Economy",
                    "image_url": "https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?auto=format&fit=crop&w=1200&q=80",
                    "status": ArticleStatus.VERIFIED,
                    "published_at": datetime.now(timezone.utc) - timedelta(hours=22),
                    "claims": [
                        ("Bilateral testing for instant cross-border settlement completed under BIS auspices.", ClaimVerdict.TRUE, 0.90, "BIS Project Dunbar & Agora Reports", "Institutional press releases verify successful multi-jurisdiction technical tests."),
                        ("Transaction friction and conversion costs fell by 40% during trial runs.", ClaimVerdict.TRUE, 0.85, "Financial Times Banking Desk", "Empirical data cited in central bank pilot evaluation paper."),
                    ],
                    "report_verdict": "Verified / Supported",
                    "notes": "Accredited financial reporting citing official BIS publications.",
                    "adj": 0.0,
                    "decision": ReviewerDecision.APPROVED,
                },
                {
                    "title": "SHOCKING TRUTH: Secret Mineral Discovered That Cures All Diseases Overnight!",
                    "content": (
                        "Doctors don't want you to know this mind-blowing secret mineral from the ancient caves. "
                        "Unbelievable laboratory leaks prove once and for all that a secret trick cures all diseases guaranteed 100%. "
                        "Mainstream pharmaceutical companies have secretly controlled and hidden this miracle cure for decades."
                    ),
                    "summary": "Sensational claim asserting an unproven miracle substance cures all human ailments overnight.",
                    "source_url": "http://miracle-cures-daily.xyz/shocking-breakthrough",
                    "publisher": "Miracle Daily",
                    "author": None,
                    "category": "Health",
                    "image_url": "https://images.unsplash.com/photo-1584036561566-baf8f5f1b144?auto=format&fit=crop&w=1200&q=80",
                    "status": ArticleStatus.FLAGGED,
                    "published_at": datetime.now(timezone.utc) - timedelta(days=2),
                    "claims": [
                        ("Secret mineral discovered that cures all diseases guaranteed 100%.", ClaimVerdict.FALSE, 0.96, "Medical Misinformation Registry; FDA Advisory", "Matches known medical pseudoscience disinformation pattern without clinical data."),
                        ("Mainstream pharmaceutical companies have secretly controlled and hidden this cure.", ClaimVerdict.FALSE, 0.92, "FactCheck Common Red Flags Registry", "Classic conspiratorial trope lacking institutional substantiation or evidence."),
                    ],
                    "report_verdict": "Disputed / Likely False",
                    "notes": "Flagged for hazardous health misinformation and non-accredited source domain.",
                    "adj": -10.0,
                    "decision": ReviewerDecision.REJECTED,
                },
            ]

            for s in demo_stories:
                art = Article(
                    title=s["title"],
                    content=s["content"],
                    summary=s["summary"],
                    source_url=s["source_url"],
                    publisher=s["publisher"],
                    author=s["author"],
                    category=s["category"],
                    image_url=s["image_url"],
                    published_at=s["published_at"],
                    status=s["status"],
                    submitter_id=reporter.id,
                )
                db.add(art)
                db.flush()

                saved_claims = []
                for c_text, c_verdict, c_conf, c_evid, c_expl in s["claims"]:
                    c_obj = Claim(
                        article_id=art.id,
                        claim_text=c_text,
                        verdict=c_verdict,
                        confidence=c_conf,
                        evidence_sources=c_evid,
                        explanation=c_expl,
                    )
                    db.add(c_obj)
                    saved_claims.append(c_obj)
                db.flush()

                rep = VerificationReport(
                    article_id=art.id,
                    provider_name="RuleBased-Engine",
                    provider_verdict=s["report_verdict"],
                    claims_count=len(saved_claims),
                    summary=f"Automated verification completed with {len(saved_claims)} claim assessments.",
                    reviewer_id=reporter.id if s["status"] == ArticleStatus.VERIFIED else admin.id,
                    reviewer_decision=s["decision"],
                    reviewer_notes=s["notes"],
                )
                db.add(rep)
                db.flush()

                score_data = scoring_engine.compute_score(
                    title=art.title,
                    content=art.content,
                    source_url=art.source_url,
                    publisher=art.publisher,
                    author=art.author,
                    published_at=art.published_at,
                    claims=saved_claims,
                    reviewer_adjustment=s["adj"],
                    reviewer_decision=s["decision"],
                    reviewer_notes=s["notes"],
                )

                ts = TrustScore(
                    article_id=art.id,
                    verification_report_id=rep.id,
                    overall_score=score_data["overall_score"],
                    grade=score_data["grade"],
                    source_reliability_score=score_data["source_reliability_score"],
                    corroboration_score=score_data["corroboration_score"],
                    claim_verification_score=score_data["claim_verification_score"],
                    recency_score=score_data["recency_score"],
                    reviewer_adjustment=s["adj"],
                    explanation=json.dumps(score_data["explanation"]),
                )
                db.add(ts)

            db.commit()

    finally:
        db.close()


def provision_initial_admin():
    """Provision the explicitly configured production administrator once."""
    credentials = (
        settings.initial_admin_username,
        settings.initial_admin_email,
        settings.initial_admin_password,
    )
    if not all(credentials):
        if any(credentials):
            raise RuntimeError(
                "INITIAL_ADMIN_USERNAME, INITIAL_ADMIN_EMAIL, and INITIAL_ADMIN_PASSWORD must be set together."
            )

    db = SessionLocal()
    try:
        if not any(credentials):
            has_admin = db.query(User).filter(User.role == UserRole.ADMIN).first()
            if not has_admin:
                raise RuntimeError(
                    "Configure INITIAL_ADMIN_USERNAME, INITIAL_ADMIN_EMAIL, and INITIAL_ADMIN_PASSWORD "
                    "before the first production deployment."
                )
            return

        admin = db.query(User).filter(User.username == settings.initial_admin_username).first()
        if not admin:
            db.add(User(
                username=settings.initial_admin_username,
                email=settings.initial_admin_email,
                hashed_password=hash_password(settings.initial_admin_password),
                role=UserRole.ADMIN,
                is_active=True,
            ))
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables
    Base.metadata.create_all(bind=engine)
    if settings.should_seed_demo_data:
        seed_initial_data()
    elif settings.is_production:
        provision_initial_admin()
    yield


app = FastAPI(
    title=settings.project_name,
    version=settings.version,
    description="Explainable News Authentication & Verification Platform",
    lifespan=lifespan,
)

# CORS middleware for open accessibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 routes
app.include_router(router, prefix=settings.api_v1_str)


# Serve static web interface
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
def serve_dashboard():
    """Serves the interactive web application dashboard."""
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "News Authentication API is running. Visit /docs for interactive Swagger UI."}


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "version": settings.version}
