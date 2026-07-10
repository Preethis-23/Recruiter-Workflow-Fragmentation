CREATE TABLE jd (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL
);

CREATE TABLE resume (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,
    name TEXT,
    email TEXT,
    education TEXT,
    skills TEXT,
    projects TEXT,
    experience TEXT,
    certifications TEXT
);

CREATE TABLE candidate (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    jd_id INTEGER,
    resume_id INTEGER,
    similarity_score REAL,
    summary TEXT,
    FOREIGN KEY (jd_id) REFERENCES jd(id),
    FOREIGN KEY (resume_id) REFERENCES resume(id)
);

CREATE TABLE recruitment_stage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER,
    stage TEXT NOT NULL,
    date TEXT NOT NULL,
    notes TEXT,
    FOREIGN KEY (candidate_id) REFERENCES candidate(id)
);
