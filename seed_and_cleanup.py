import random
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from recruiter_workflow.database import Base
from recruiter_workflow.models import JobDescription, Resume, Candidate, Meeting, RecruitmentStage

DATABASE_URL = "sqlite:///./recruiter_workflow.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def cleanup_duplicates_and_seed():
    db = SessionLocal()
    try:
        print("--- Step 1: Cleaning up duplicate Job Descriptions ---")
        all_jds = db.query(JobDescription).order_by(JobDescription.id.asc()).all()
        seen_titles = {}
        duplicates_removed = 0
        
        for jd in all_jds:
            normalized_title = jd.title.strip().lower()
            if normalized_title in seen_titles:
                master_jd = seen_titles[normalized_title]
                # Re-assign candidates from duplicate JD to master JD
                candidates_to_update = db.query(Candidate).filter(Candidate.jd_id == jd.id).all()
                for c in candidates_to_update:
                    # Check if candidate already linked to master JD
                    existing_link = db.query(Candidate).filter(
                        Candidate.jd_id == master_jd.id,
                        Candidate.resume_id == c.resume_id
                    ).first()
                    if existing_link:
                        db.query(Meeting).filter(Meeting.candidate_id == c.id).update({"candidate_id": existing_link.id})
                        db.query(RecruitmentStage).filter(RecruitmentStage.candidate_id == c.id).update({"candidate_id": existing_link.id})
                        db.delete(c)
                    else:
                        c.jd_id = master_jd.id
                db.delete(jd)
                duplicates_removed += 1
            else:
                seen_titles[normalized_title] = jd
        
        db.commit()
        print(f"Successfully removed {duplicates_removed} duplicate Job Descriptions.")
        
        # Ensure we have core standard JDs if db is light
        standard_roles = [
            ("Python ML Engineer", "Engineering", "Python, PyTorch, TensorFlow, Scikit-Learn, MLOps, Docker, FastAPI"),
            ("Frontend React Developer", "Engineering", "React, TypeScript, Next.js, HTML5, CSS3, Redux, Tailwind"),
            ("DevOps & Cloud Engineer", "Infrastructure", "AWS, Kubernetes, Terraform, Docker, CI/CD, Linux, Python"),
            ("Data Scientist", "Data", "Python, SQL, R, Machine Learning, NLP, Data Visualization, Pandas"),
            ("Full Stack Software Engineer", "Engineering", "Node.js, React, Python, PostgreSQL, REST APIs, Git"),
            ("Senior Product Manager", "Product", "Product Roadmap, Agile, User Stories, Data Analytics, Jira"),
            ("QA Automation Engineer", "Quality Assurance", "Selenium, Cypress, Python, PyTest, CI/CD, API Testing"),
            ("Cyber Security Analyst", "Security", "SIEM, Penetration Testing, Network Security, Python, ISO27001")
        ]
        
        existing_jds_list = db.query(JobDescription).all()
        existing_titles_set = {j.title.strip().lower() for j in existing_jds_list}
        
        for title, dept, skills in standard_roles:
            if title.strip().lower() not in existing_titles_set:
                new_jd = JobDescription(
                    title=title,
                    department=dept,
                    description=f"We are looking for an experienced {title} to join our dynamic team.",
                    required_skills=skills
                )
                db.add(new_jd)
                db.commit()
                db.refresh(new_jd)
                existing_jds_list.append(new_jd)
        
        active_jds = db.query(JobDescription).all()
        print(f"Total Unique Job Descriptions in DB: {len(active_jds)}")
        
        print("\n--- Step 2: Seeding 75 Sample Resumes & Candidates ---")
        
        first_names = ["Aarav", "Elena", "Marcus", "Priya", "David", "Sophia", "Liam", "Maya", "Carlos", "Fatima",
                       "Ethan", "Chloe", "Vikram", "Zoe", "Alexander", "Hannah", "Rohan", "Isabella", "Gabriel", "Ananya",
                       "Noah", "Olivia", "Lucas", "Emily", "Mateo", "Mia", "Siddharth", "Charlotte", "Daniel", "Amara"]
        
        last_names = ["Sharma", "Rostova", "Vance", "Patel", "Kim", "Martinez", "Chen", "Gupta", "Silva", "Ali",
                      "Wright", "Zhao", "Reddy", "Dubois", "Kovacs", "Nakamura", "Deshmukh", "Santos", "Muller", "Iyer",
                      "O'Connor", "Novak", "Singh", "Lopez", "Verma", "Jensen", "Mehta", "Tanaka", "Bhat", "Al-Mansoor"]

        domains = ["gmail.com", "techmail.io", "devstudio.org", "cloudnet.com", "ai-labs.net"]
        
        sample_skills_by_role = {
            "ml": ["Python", "PyTorch", "TensorFlow", "Scikit-Learn", "BERT", "LLMs", "Docker", "Pandas", "MLflow"],
            "frontend": ["React", "TypeScript", "Next.js", "Redux Toolkit", "TailwindCSS", "CSS Grid", "GraphQL"],
            "devops": ["AWS", "Kubernetes", "Docker", "Terraform", "GitHub Actions", "Prometheus", "Linux", "Bash"],
            "data": ["Python", "SQL", "Pandas", "NumPy", "Tableau", "Apache Spark", "Scikit-Learn", "A/B Testing"],
            "fullstack": ["Node.js", "Express", "React", "PostgreSQL", "MongoDB", "TypeScript", "REST APIs", "Docker"],
            "product": ["Agile/Scrum", "Product Vision", "Roadmapping", "SQL", "Mixpanel", "User Research", "Jira"],
            "qa": ["Selenium", "Cypress", "PyTest", "Postman", "API Testing", "Jenkins", "Performance Testing"],
            "security": ["Penetration Testing", "Wireshark", "Burp Suite", "Python", "SIEM", "Cloud Security", "OWASP"]
        }

        inserted_count = 0
        os.makedirs("./uploads", exist_ok=True)
        
        for i in range(1, 76):
            fname = random.choice(first_names)
            lname = random.choice(last_names)
            c_name = f"{fname} {lname}"
            clean_email_name = f"{fname.lower()}.{lname.lower()}{random.randint(10, 99)}"
            c_email = f"{clean_email_name}@{random.choice(domains)}"
            c_phone = f"+1 ({random.randint(200,999)}) {random.randint(100,999)}-{random.randint(1000,9999)}"
            
            # Select target JD
            target_jd = random.choice(active_jds)
            jd_title_lower = target_jd.title.lower()
            
            if "ml" in jd_title_lower or "python" in jd_title_lower or "ai" in jd_title_lower:
                role_key = "ml"
            elif "front" in jd_title_lower or "react" in jd_title_lower:
                role_key = "frontend"
            elif "devops" in jd_title_lower or "cloud" in jd_title_lower:
                role_key = "devops"
            elif "data" in jd_title_lower:
                role_key = "data"
            elif "full" in jd_title_lower:
                role_key = "fullstack"
            elif "product" in jd_title_lower:
                role_key = "product"
            elif "qa" in jd_title_lower or "quality" in jd_title_lower:
                role_key = "qa"
            else:
                role_key = "security"
                
            skills_list = random.sample(sample_skills_by_role[role_key], min(5, len(sample_skills_by_role[role_key])))
            skills_str = ", ".join(skills_list)
            
            exp_years = random.randint(2, 11)
            raw_text = f"""
            {c_name}
            Email: {c_email} | Phone: {c_phone}
            
            SUMMARY:
            Enthusiastic {target_jd.title} with {exp_years} years of hands-on experience building scalable applications, driving technical excellence, and collaborating in fast-paced teams.
            
            EXPERIENCE:
            Senior Tech Lead / Developer ({2026 - exp_years} - Present)
            - Developed enterprise scalable architecture using {skills_list[0]} and {skills_list[1]}.
            - Optimized performance by 35% and mentored junior team members.
            
            SKILLS:
            {skills_str}
            
            EDUCATION:
            B.S. in Computer Science / Information Technology, Class of {2026 - exp_years - 4}
            """
            
            file_path = f"./uploads/sample_resume_{i:03d}_{clean_email_name}.pdf"
            
            # Check if resume with email already exists
            existing_resume = db.query(Resume).filter(Resume.email == c_email).first()
            if not existing_resume:
                resume = Resume(
                    file_path=file_path,
                    candidate_name=c_name,
                    email=c_email,
                    phone=c_phone,
                    education="B.S. in Computer Science",
                    skills=skills_str,
                    experience=f"{exp_years} years of professional experience",
                    raw_text=raw_text
                )
                db.add(resume)
                db.commit()
                db.refresh(resume)
            else:
                resume = existing_resume
                
            # Create Candidate entry if not exists for this JD
            existing_cand = db.query(Candidate).filter(
                Candidate.jd_id == target_jd.id,
                Candidate.resume_id == resume.id
            ).first()
            
            if not existing_cand:
                sim_score = round(random.uniform(62.0, 97.5), 1)
                cand = Candidate(
                    jd_id=target_jd.id,
                    resume_id=resume.id,
                    similarity_score=sim_score,
                    summary=f"Strong match ({sim_score}%) with {exp_years} yrs exp in {skills_list[0]}.",
                    explanation=f"Candidate demonstrates solid expertise in {skills_str}. Alignment with required {target_jd.title} qualifications is high.",
                    interview_questions=f"1. How do you approach designing scalable systems with {skills_list[0]}?\n2. Can you describe a challenging project using {skills_list[1]}?",
                    status="New"
                )
                db.add(cand)
                db.commit()
                inserted_count += 1

        print(f"Successfully seeded {inserted_count} new candidate resumes!")
        total_resumes = db.query(Resume).count()
        total_candidates = db.query(Candidate).count()
        print(f"Total Resumes in DB: {total_resumes}")
        print(f"Total Candidate-JD Mappings in DB: {total_candidates}")

    finally:
        db.close()

if __name__ == "__main__":
    cleanup_duplicates_and_seed()
