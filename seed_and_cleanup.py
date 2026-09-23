import os
import random
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from recruiter_workflow.database import Base, DATABASE_URL
from recruiter_workflow.models import JobDescription, Resume, Candidate, Meeting, RecruitmentStage

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

STANDARD_ROLES = [
    ("Python ML Engineer", "Engineering", "Python, PyTorch, TensorFlow, Scikit-Learn, MLOps, Docker, FastAPI"),
    ("Frontend React Developer", "Engineering", "React, TypeScript, Next.js, HTML5, CSS3, Redux, Tailwind"),
    ("DevOps & Cloud Engineer", "Infrastructure", "AWS, Kubernetes, Terraform, Docker, CI/CD, Linux, Python"),
    ("Data Scientist", "Data", "Python, SQL, R, Machine Learning, NLP, Data Visualization, Pandas"),
    ("Full Stack Software Engineer", "Engineering", "Node.js, React, Python, PostgreSQL, REST APIs, Git"),
    ("Senior Product Manager", "Product", "Product Roadmap, Agile, User Stories, Data Analytics, Jira"),
    ("QA Automation Engineer", "Quality Assurance", "Selenium, Cypress, Python, PyTest, CI/CD, API Testing"),
    ("Cyber Security Analyst", "Security", "SIEM, Penetration Testing, Network Security, Python, ISO27001"),
    ("Mobile Application Developer", "Engineering", "React Native, Flutter, Swift, Kotlin, iOS, Android, REST"),
    ("Cloud Data Architect", "Data", "Snowflake, Databricks, Python, Spark, ETL, PostgreSQL, AWS Redshift"),
    ("Site Reliability Engineer", "Infrastructure", "Linux, Prometheus, Grafana, Kubernetes, Go, Python, SRE")
]

FIRST_NAMES = [
    "Aarav", "Elena", "Marcus", "Priya", "David", "Sophia", "Liam", "Maya", "Carlos", "Fatima",
    "Ethan", "Chloe", "Vikram", "Zoe", "Alexander", "Hannah", "Rohan", "Isabella", "Gabriel", "Ananya",
    "Noah", "Olivia", "Lucas", "Emily", "Mateo", "Mia", "Siddharth", "Charlotte", "Daniel", "Amara",
    "Benjamin", "Layla", "Kavya", "James", "Arjun", "Zara", "Leo", "Nisha", "Julian", "Tara",
    "William", "Amina", "Oliver", "Sana", "Henry", "Meera", "Samuel", "Pooja", "Jack", "Leila"
]

LAST_NAMES = [
    "Sharma", "Rostova", "Vance", "Patel", "Kim", "Martinez", "Chen", "Gupta", "Silva", "Ali",
    "Wright", "Zhao", "Reddy", "Dubois", "Kovacs", "Nakamura", "Deshmukh", "Santos", "Muller", "Iyer",
    "O'Connor", "Novak", "Singh", "Lopez", "Verma", "Jensen", "Mehta", "Tanaka", "Bhat", "Al-Mansoor",
    "Taylor", "Davies", "Wilson", "Evans", "Thomas", "Roberts", "Walker", "Johnson", "Brown", "Hall"
]

DOMAINS = ["gmail.com", "techmail.io", "devstudio.org", "cloudnet.com", "ai-labs.net"]

SAMPLE_SKILLS = [
    "Python, Django, PostgreSQL, Docker, Redis, Celery, REST APIs",
    "React, TypeScript, Next.js, Redux, TailwindCSS, GraphQL",
    "Kubernetes, Docker, AWS, Terraform, CI/CD, Linux, Python",
    "Python, PyTorch, TensorFlow, Scikit-Learn, Pandas, NumPy, NLP",
    "Node.js, React, Express, PostgreSQL, MongoDB, TypeScript",
    "Agile/Scrum, Product Roadmap, SQL, Mixpanel, User Research, Jira",
    "Selenium, Cypress, PyTest, API Testing, Jenkins, Postman",
    "Penetration Testing, Wireshark, SIEM, Python, OWASP, Network Security",
    "React Native, Swift, Kotlin, iOS, Android, Firebase",
    "Snowflake, Spark, Python, ETL Pipelines, SQL, PostgreSQL, AWS",
    "Kubernetes, Prometheus, Grafana, Linux, Python, Go, Incident Management"
]


def seed_exact_resume_benchmark_data():
    """Seeds exactly 11 Job Descriptions, 77 Resumes, and 228 Candidate profile records."""
    db = SessionLocal()
    try:
        print("--- Step 1: Initializing Database Schema ---")
        Base.metadata.create_all(bind=engine)

        print("--- Step 2: Clearing existing records ---")
        db.query(Meeting).delete()
        db.query(RecruitmentStage).delete()
        db.query(Candidate).delete()
        db.query(Resume).delete()
        db.query(JobDescription).delete()
        db.commit()

        print("--- Step 3: Seeding Exactly 11 Job Descriptions ---")
        jds = []
        for title, dept, skills in STANDARD_ROLES[:11]:
            jd = JobDescription(
                title=title,
                department=dept,
                description=f"We are hiring a high-performing {title} to build next-generation scalable systems.",
                required_skills=skills
            )
            db.add(jd)
            jds.append(jd)
        db.commit()
        for jd in jds:
            db.refresh(jd)
        assert len(jds) == 11, f"Expected 11 JDs, got {len(jds)}"
        print(f"Created {len(jds)} Job Descriptions.")

        print("--- Step 4: Seeding Exactly 77 Resumes ---")
        os.makedirs("./uploads", exist_ok=True)
        resumes = []
        random.seed(42)  # For reproducible test benchmarks

        for i in range(1, 78):
            fname = FIRST_NAMES[(i - 1) % len(FIRST_NAMES)]
            lname = LAST_NAMES[(i - 1) % len(LAST_NAMES)]
            c_name = f"{fname} {lname}"
            c_email = f"{fname.lower()}.{lname.lower()}{i}@example.com"
            c_phone = f"+1 (555) {100 + i:03d}-{2000 + i:04d}"
            exp_years = (i % 8) + 2
            skills = SAMPLE_SKILLS[(i - 1) % len(SAMPLE_SKILLS)]

            raw_text = f"""
            {c_name}
            Email: {c_email} | Phone: {c_phone}
            
            SUMMARY:
            Experienced engineer with {exp_years} years of professional expertise in modern technology stacks.
            
            EXPERIENCE:
            Senior Engineer (2020 - Present)
            - Engineered scalable architectures using {skills.split(',')[0]} and {skills.split(',')[1]}.
            - Improved system throughput and reliability across distributed teams.
            
            SKILLS:
            {skills}
            
            EDUCATION:
            B.S. in Computer Science / Information Systems
            """

            file_path = f"./uploads/resume_{i:03d}_{fname.lower()}_{lname.lower()}.pdf"
            resume = Resume(
                file_path=file_path,
                candidate_name=c_name,
                email=c_email,
                phone=c_phone,
                education="B.S. in Computer Science",
                skills=skills,
                experience=f"{exp_years} years",
                raw_text=raw_text.strip()
            )
            db.add(resume)
            resumes.append(resume)

        db.commit()
        for r in resumes:
            db.refresh(r)
        assert len(resumes) == 77, f"Expected 77 Resumes, got {len(resumes)}"
        print(f"Created {len(resumes)} Resumes.")

        print("--- Step 5: Seeding Exactly 228 Candidate Profiles ---")
        candidates = []
        candidate_count = 0
        target_candidates = 228

        # Distribute mappings across all 11 JDs and 77 Resumes deterministically
        pairs_set = set()
        
        # 1. First ensure every resume has at least 2 JD applications (77 * 2 = 154)
        for r_idx, resume in enumerate(resumes):
            jd_primary = jds[r_idx % len(jds)]
            jd_secondary = jds[(r_idx + 1) % len(jds)]
            for jd in [jd_primary, jd_secondary]:
                pairs_set.add((jd.id, resume.id))

        # 2. Add remaining pairs until exactly 228 candidate records are formed
        r_cycle = 0
        while len(pairs_set) < target_candidates:
            resume = resumes[r_cycle % len(resumes)]
            jd_idx = (r_cycle * 3 + len(pairs_set)) % len(jds)
            jd = jds[jd_idx]
            pairs_set.add((jd.id, resume.id))
            r_cycle += 1

        for jd_id, resume_id in list(pairs_set)[:target_candidates]:
            sim_score = round(random.uniform(65.0, 98.5), 1)
            cand = Candidate(
                jd_id=jd_id,
                resume_id=resume_id,
                similarity_score=sim_score,
                summary=f"Evaluated candidate match with similarity score {sim_score}%.",
                explanation="Candidate demonstrates relevant domain experience aligned with role expectations.",
                interview_questions="1. Walk through your recent architectural projects.\n2. How do you handle production debugging?",
                status=random.choice(["New", "Screening", "Interview", "Offer"])
            )
            db.add(cand)
            candidates.append(cand)

        db.commit()
        assert len(candidates) == 228, f"Expected 228 Candidates, got {len(candidates)}"
        print(f"Created {len(candidates)} Candidate Profiles.")

        total_jds = db.query(JobDescription).count()
        total_res = db.query(Resume).count()
        total_cands = db.query(Candidate).count()

        print("\n=== Benchmark Seed Verification ===")
        print(f"[OK] Job Descriptions: {total_jds} (Target: 11)")
        print(f"[OK] Resumes:          {total_res} (Target: 77)")
        print(f"[OK] Candidate Records:{total_cands} (Target: 228)")
        print("Database is seeded and verified!")

    finally:
        db.close()


if __name__ == "__main__":
    seed_exact_resume_benchmark_data()
