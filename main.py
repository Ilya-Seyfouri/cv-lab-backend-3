from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Request
import PyPDF2
import io
import re
import subprocess
import tempfile
from pathlib import Path
from fpdf import FPDF
import base64
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from auth import get_current_user
from credits import check_and_use_credit, get_user_credits
from datetime import datetime


import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

load_dotenv()

LATEX_CV_TEMPLATE = r"""
\documentclass[letterpaper,11pt]{article}

\usepackage{latexsym}
\usepackage[empty]{fullpage}
\usepackage{titlesec}
\usepackage{marvosym}
\usepackage[usenames,dvipsnames]{color}
\usepackage{verbatim}
\usepackage{enumitem}
\usepackage[hidelinks]{hyperref}
\usepackage{fancyhdr}
\usepackage[english]{babel}
\usepackage{tabularx}
\usepackage{fontawesome5}
\usepackage{multicol}
\setlength{\multicolsep}{-3.0pt}
\setlength{\columnsep}{-1pt}
\input{glyphtounicode}
\usepackage[margin=1.4cm]{geometry}

\pagestyle{fancy}
\fancyhf{}
\fancyfoot{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}

\addtolength{\oddsidemargin}{-0.15in}
\addtolength{\textwidth}{0.3in}

\urlstyle{same}

\raggedbottom
\raggedright
\setlength{\tabcolsep}{0in}

\titleformat{\section}{
  \vspace{-4pt}\scshape\raggedright\large\bfseries
}{}{0em}{}[\color{black}\titlerule \vspace{-5pt}]

\pdfgentounicode=1

\newcommand{\resumeItem}[1]{
  \item\small{
    {#1 \vspace{0pt}}
  }
}

\newcommand{\classesList}[4]{
    \item\small{
        {#1 #2 #3 #4 \vspace{-2pt}}
  }
}

\newcommand{\resumeSubheading}[4]{
  \vspace{-2pt}\item
    \begin{tabular*}{1.0\textwidth}[t]{l@{\extracolsep{\fill}}r}
      \textbf{#1} & \textbf{\small #2} \\
      \textit{\small#3} & \textit{\small #4} \\
    \end{tabular*}\vspace{-7pt}
}

\newcommand{\resumeSubSubheading}[2]{
    \item
    \begin{tabular*}{0.97\textwidth}{l@{\extracolsep{\fill}}r}
      \textit{\small#1} & \textit{\small #2} \\
    \end{tabular*}\vspace{-7pt}
}

\newcommand{\resumeProjectHeading}[2]{
    \item
    \begin{tabular*}{1.001\textwidth}{l@{\extracolsep{\fill}}r}
      \small#1 & \textbf{\small #2}\\
    \end{tabular*}\vspace{-7pt}
}

\newcommand{\resumeSubItem}[1]{\resumeItem{#1}\vspace{-4pt}}

\renewcommand\labelitemi{$\vcenter{\hbox{\tiny$\bullet$}}$}
\renewcommand\labelitemii{$\vcenter{\hbox{\tiny$\bullet$}}$}

\newcommand{\resumeSubHeadingListStart}{\begin{itemize}[leftmargin=0.0in, label={}]}
\newcommand{\resumeSubHeadingListEnd}{\end{itemize}}\vspace{0pt}
\newcommand{\resumeItemListStart}{\begin{itemize}}
\newcommand{\resumeItemListEnd}{\end{itemize}\vspace{-5pt}}

\begin{document}

%----------HEADING----------
\begin{center}
    {\Large \scshape [FULL_NAME]} \\[2mm]
    \footnotesize \raisebox{-0.1\height}
    {\faEnvelope\  \underline{[EMAIL]}} ~ 
    {\faLinkedin\ \underline{\href{[LINKEDIN_URL]}{[LINKEDIN_DISPLAY]}}  ~
    {\faGithub\ \underline{\href{[GITHUB_URL]}{[GITHUB_DISPLAY]}} ~
    {\faBriefcase\ \underline{\href{[PORTFOLIO_URL]}{[PORTFOLIO_DISPLAY]}}
    \vspace{-8pt}
\end{center}

%-----------EDUCATION-----------
\section{Education} \\[1mm]
  \resumeSubHeadingListStart
    \resumeSubheading
      {[UNIVERSITY]}{Expected Graduation: [GRAD_DATE]}
      {[DEGREE] | Minor [MINOR]
      }{[LOCATION]}
  \resumeSubHeadingListEnd
    \resumeItemListStart
        \resumeItem {[HONORS] | \textbf{GPA: [GPA]}}
        \resumeItem {Courses: [RELEVANT_COURSES]}
    \resumeItemListEnd

%-----------Experience---------------
\section{Work Experience}
    \resumeSubHeadingListStart
        \resumeSubheading{[COMPANY_1]}{[START_DATE_1] -- [END_DATE_1]}{[JOB_TITLE_1]}{[LOCATION_1]} 
            \resumeItemListStart
                \resumeItem{[ACHIEVEMENT_1_1]}
                \resumeItem{[ACHIEVEMENT_1_2]}
                \resumeItem{[ACHIEVEMENT_1_3]}
            \resumeItemListEnd
        \resumeSubheading{[COMPANY_2]}{[START_DATE_2] -- [END_DATE_2]}{[JOB_TITLE_2]}{[LOCATION_2]} 
            \resumeItemListStart
                \resumeItem{[ACHIEVEMENT_2_1]}
                \resumeItem{[ACHIEVEMENT_2_2]}
                \resumeItem{[ACHIEVEMENT_2_3]}
            \resumeItemListEnd
        \resumeSubheading{[COMPANY_3]}{[START_DATE_3] -- [END_DATE_3]}{[JOB_TITLE_3]}{[LOCATION_3]}
            \resumeItemListStart
                \resumeItem{[ACHIEVEMENT_3_1]}
                \resumeItem{[ACHIEVEMENT_3_2]}
            \resumeItemListEnd
    \resumeSubHeadingListEnd

%-----------PROJECTS-----------
\section{Projects} 
    \resumeSubHeadingListStart
        \resumeProjectHeading
            {\textbf{{[PROJECT_1_NAME]}} $|$ \emph{\href{[PROJECT_1_URL]}{Website}{ $|$ }\href{[PROJECT_1_SOURCE]}{Source Code}}}{[PROJECT_1_TECH]}
            \\[5mm]
            \resumeItemListStart
                \resumeItem{[PROJECT_1_DESC_1]}
                \resumeItem{[PROJECT_1_DESC_2]}
            \resumeItemListEnd
            \vspace{-10pt}

        \resumeProjectHeading
            {\textbf{{[PROJECT_2_NAME]}} $|$ \emph{\href{[PROJECT_2_URL]}{Website}}}{[PROJECT_2_TECH]}
            \\[5mm]
            \resumeItemListStart
                \resumeItem{[PROJECT_2_DESC_1]}
            \resumeItemListEnd
            \vspace{-10pt}

        \resumeProjectHeading
            {\textbf{{[PROJECT_3_NAME]}} $|$ \emph{\href{[PROJECT_3_URL]}{Website}{ $|$ }\href{[PROJECT_3_SOURCE]}{Source Code}}}{[PROJECT_3_TECH]}
            \\[5mm]
            \resumeItemListStart
                \resumeItem{[PROJECT_3_DESC_1]}
            \resumeItemListEnd
    \resumeSubHeadingListEnd

%-----------LEADERSHIP-----------
\section{Leadership} 
    \resumeSubHeadingListStart
        \resumeProjectHeading
            {\textbf{[LEADERSHIP_1_NAME]}}{[LEADERSHIP_1_DATE]}
            \\[2mm]
            \resumeItemListStart
                \resumeItem{[LEADERSHIP_1_DESC_1]}
                \resumeItem{[LEADERSHIP_1_DESC_2]}
            \resumeItemListEnd
            \vspace{-10pt}

    \resumeSubHeadingListEnd

%-----------PROGRAMMING SKILLS-----------
\section{Technical Skills}
 \begin{itemize}[leftmargin=0.15in, label={}]
    \small{\item{   
     \textbf{Languages}{: [PROGRAMMING_LANGUAGES]} \\[1mm]
     \textbf{Libraries/Frameworks}{: [FRAMEWORKS]} \\ [1mm]
    }}
 \end{itemize}
 \vspace{-16pt}
 \vspace{3pt}
\vspace{10pt}

\end{document}

"""
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="CV Editor API")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# With this (you'll update the Railway URL after frontend is deployed):
origins = [
    "http://localhost:3000",
    "https://cvlab.ltd",
    "https://cvlab.up.railway.app",  # Allow all Railway domains temporarily
    # Add your actual frontend URL here after deploying frontend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable is not set!")
client = OpenAI(api_key=api_key)


# Request model
class JobDescriptionRequest(BaseModel):
    job_description: str
    user_cv: str = ""


@app.get("/credits")
async def get_credits(current_user=Depends(get_current_user)):
    user_data = await get_user_credits(current_user.id)

    if user_data['is_subscribed']:
        return {
            "remaining": "unlimited",
            "is_subscribed": True
        }

    return {
        "remaining": user_data['credits_remaining'],
        "is_subscribed": False
    }


def sanitize_latex(latex_code: str) -> str:
    """
    Minimal sanitization - only fix obvious text content issues.
    Don't touch anything that looks like LaTeX commands.
    """
    lines = []

    for line in latex_code.split('\n'):
        # Skip lines that are clearly LaTeX structure/commands
        if any(x in line for x in [
            '\\begin{', '\\end{', '\\usepackage', '\\documentclass',
            '\\newcommand', '\\renewcommand', '\\setlength',
            '\\titleformat', '\\input', '\\pagestyle', '\\fancyhf',
            '\\addtolength', '\\urlstyle', '\\raggedbottom', '\\pdfgentounicode',
            '\\resumeItem{', '\\resumeSubheading{', '\\textbf{', '\\href{',
            '\\faPhone', '\\faEnvelope', '\\faLinkedin', '\\faGithub', '\\faBriefcase',
            '\\section{', '\\item', '\\vspace', '\\small', '\\Large', '\\scshape'
        ]):
            lines.append(line)
            continue

        # Skip comment lines
        if line.strip().startswith('%'):
            lines.append(line)
            continue

        # For regular text lines, only escape if NOT already escaped
        # Ampersand (but not already escaped)
        line = re.sub(r'(?<!\\)&(?![a-zA-Z])', r'\\&', line)

        # Percent (but not already escaped)
        line = re.sub(r'(?<!\\)%', r'\\%', line)

        # Underscore (but not already escaped or in commands)
        line = re.sub(r'(?<!\\)_', r'\\_', line)

        lines.append(line)

    return '\n'.join(lines)


async def parse_cv(user_cv):
    """
    Analyzes skill gaps between CV and job description.
    Returns only truly missing technical skills.
    """

    logging.info("=== STEP 1: Parsing CV ===")

    # SYSTEM MESSAGE: Identity + Process + Rules
    system_message = """You are an expert CV parser and extractor.
    Extract all information from this users CV and output as JSON:


     RULES:
     - Do NOT summarise sections, return the entire field on the cv.
     - Output only strictly valid JSON
     - Include all required keys even if empty.



JSON structure must include:
{
  "personal_info": {
    "full_name": string,
    "email": string|null,
    "phone": string|null,
    "linkedin": string|null,
    "github": string|null,
    "portfolio": string|null  // optional addition
  },
  "education": [
    {
      "institution": string,
      "degree": string,
      "dates": string,
      "location": string|null,
      "courses": [string],
      "honors": string|null,
      "gpa": string|null
    }
  ],
  "experience": [
    {
      "company": string,
      "title": string,
      "dates": string,
      "location": string|null,
      "achievements": [string],
      "technologies": [string]
    }
  ],
  "projects": [
    {
      "name": string,
      "description": string,
      "technologies": [string],
      "url": string|null,
      "source": string|null,
      "date": string|null
    }
  ],
  "leadership": [  
    {
      "role": string,
      "organization": string,
      "dates": string,
      "location": string|null,
      "achievements": [string]
    }
  ],
  "certifications": [  
    {
      "name": string,
      "issuer": string,
      "date": string,
      "credential_id": string|null
    }
  ],
  "skills": [string]
}
"""

    # USER MESSAGE: Context + Examples
    user_message = f"""Extract this CV into JSON

CANDIDATE'S CV:
{user_cv}


Return only valid JSON."""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1",  # Fast and cost-effective
            temperature=0,  # Deterministic output
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            max_tokens=2000
        )

        json_cv = response.choices[0].message.content
        logging.info("CV parsed successfully")
        print(json_cv)

        return json_cv


    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Skill analysis failed: {str(e)}"
        )




async def extract_job(job_description):

    logging.info("=== STEP 2: Extracting Job Description ===")

    # SYSTEM MESSAGE: Identity + Process + Rules
    system_message = """You are a job description parser. Your task is to extract all structured information from a job description.

    Rules
    - Extract fields: role_title, required_skills, nice_to_have, experience_level, responsibilities, soft_skills

JSON structure must include:
{
  "role_title": string,
  "required_skills": [string],
  "nice_to_have": [string],
  "experience_level": string,
  "responsibilities": [string],
  "soft_skills": [string]
}
"""

    # USER MESSAGE: Context + Examples
    user_message = f"""Extract the information from this job description as strictly valid JSON


    EXAMPLES:

Example 1:
Job Description:
We are looking for a Backend Engineer with 3+ years experience in Python and Django. 
Experience with PostgreSQL is required. Knowledge of Docker and AWS is a plus. 
You will be building and maintaining REST APIs and collaborating closely with the frontend team. 
Excellent communication and teamwork skills are required.
Output JSON:
{{
    "role_title": "Backend Engineer",
  "required_skills": ["Python", "Django", "PostgreSQL"],
  "nice_to_have": ["Docker", "AWS"],
  "experience_level": "mid",
  "responsibilities": ["Build and maintain REST APIs", "Collaborate with frontend team"],
  "soft_skills": ["communication", "teamwork"]
}}

Example 2:
Job Description:
Looking for a Junior Frontend Developer proficient in React and JavaScript. 
Knowledge of CSS frameworks is a bonus. Must be comfortable working in Agile teams.
Output JSON:
{{
    "role_title": "Junior Frontend Developer",
  "required_skills": ["React", "JavaScript"],
  "nice_to_have": ["CSS frameworks"],
  "experience_level": "junior",
  "responsibilities": [],
  "soft_skills": ["Agile"]
}}

Now analyze this job description and return JSON following the same rules and format:

JOB DESCRIPTION:
{job_description}


Return only valid JSON."""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1",  # Fast and cost-effective
            temperature=0,  # Deterministic output
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            max_tokens=2000
        )

        json_job_desc = response.choices[0].message.content
        print(json_job_desc)
        logging.info("Job description extracted successfully")

        return json_job_desc

    except Exception as e:

        print("ERROR", e)
        print("ERROR", str(e))


        raise HTTPException(
            status_code=500,
            detail=f"Skill analysis failed: {str(e)}"
        )

async def analyse_skills(json_job_desc, json_cv):
    logging.info("=== STEP 3: Analyzing Skills ===")

    """
    Analyzes skill gaps between CV and job description.
    Returns only truly missing technical skills.
    """

    # SYSTEM MESSAGE: Identity + Process + Rules
    system_message = """
    "You are an expert technical skill analyst who compares CVs to job descriptions."


    You are receiving two JSON objects:
    1. cv_json – representing the candidate's CV, structured with fields like "work_experience", "skills", "projects", "education", etc.
    2. job_json – representing the job description, structured with fields like "title", "requirements", "responsibilities", "level", etc.

    Your task is to compare the candidate's CV against the job description and produce a structured JSON output describing:

    1. Role summary
    2. Must-have, important, and nice-to-have keywords
    3. Evidence for each keyword from the CV
    4. How to bridge missing skills using related experiences or transferable skills
    5. Role alignment with a match score (0.0–1.0) and ATS score representing how well the CV matches the job description from an Applicant Tracking System perspective. (0-100)
    6. Prioritized actions for CV tailoring
    7. Soft Skills 
    8. Job responsibilities
    9. Evidence for each responsibility from the CV where the candidate demonstrates them

    CRITICAL RULES:
    - NEVER fabricate skills, soft skills, experiences, companies, or career history.
    - Accept implicit and transferable skills and evidence:
        - Explicit evidence = keyword appears in CV verbatim.
        - Implicit-strong evidence = 2+ bullets showing the skill.
        - Weak evidence = 1 bullet or indirect connection.
        - Transferable = related skill, technology, or context.
    - For weak/transferable skills, provide bridging text and 1–3 rewrite examples.
    - Only analyze technical skills, tools, and methodologies. Ignore soft skills.
    - Prioritize promoting experiences you can highlight and DO NOT claim absent skills.
    - Output only JSON. No extra text, explanations, or comments.


    EXAMPLES:

    Example 1 - Explicit evidence:
    Job requires: "Java"
    CV shows: "Implemented REST APIs in Java Spring Boot"
    Output in JSON:
    {
      "evidence_map": {
        "Java": {
          "status": "explicit",
          "evidence": ["Implemented REST APIs in Java Spring Boot"]
        }
      }
    }

    Example 2 - Missing skill with bridge:
    Job requires: "Kubernetes"
    CV shows: "Dockerized apps and automated CI/CD pipelines"
    Output in JSON:
    {
      "evidence_map": {
        "Kubernetes": {
          "status": "absent",
          "evidence": []
        }
      },
      "gap_bridges": {
        "Kubernetes": {
          "bridge_text": "Docker & CI/CD experience can be framed as baseline for Kubernetes",
          "acceptable_rewrite_examples": [
            "Packaged services into Docker containers and automated CI/CD pipelines"
          ]
        }
      }
    }

    JSON STRUCTURE:

    {
      "role_summary": {
        "title": "",
        "level": "",
        "context": "",
        "top_responsibilities": [],
        "soft_skills": [],
      },
      "keywords": {
        "must_have": [],
        "important": [],
        "nice_to_have": []
      },
   "evidence_map": {
    "<keyword>": {
        "status": "<explicit|implicit_strong|implicit_weak|transferable|absent>",
        "evidence": [
            {
                "section": "<CV section title>",
                "bullet": "<relevant CV bullet(s)>"
            }
        ]
    }
},
"responsibilities_map": {
    "<responsibility>": {
        "status": "<explicit|implicit_strong|implicit_weak|transferable|absent>",
        "evidence": [
            {
                "section": "<CV section title>",
                "bullet": "<relevant CV bullet(s)>"
            }
        ]
    }
}
      "missing_skills": [],
      "gap_bridges": {
        "<missing_skill>": {
          "bridge_text": "<suggestion for bridging this skill>",
          "acceptable_rewrite_examples": ["<examples>"]
        }
      },
      "role_alignment": {
        "match_score": "<float 0.0-1.0>",
        "ats_score": "<integer 0-100>",
        "reason": "<short text explanation>"
      },
      "prioritized_actions": [
        {"action": "<promote_experience|do_not_claim>", "target": "<skill/experience>", "priority": <integer>}
      ],
    }
    """

    user_message = f"""
    Analyze this candidate's CV against the job description and output strictly valid JSON following the structure defined in the system message.
    cv_json = {json_cv}
    job_json = {json_job_desc}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4.1",  # Fast and cost-effective
            temperature=0,  # Deterministic output
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            max_tokens=4000
        )

        skills_report = response.choices[0].message.content
        logging.info("Skills analysis completed successfully")
        print(type(skills_report))

        print(skills_report)

        return skills_report

    except Exception as e:
        print("ERROR", e)
        print("ERROR", str(e))



        raise HTTPException(
            status_code=500,
            detail=f"Skill analysis failed: {str(e)}"
        )

@app.post("/generate-cv")
@limiter.limit("25/minute")
async def generate_cv(request: Request, data: dict, current_user=Depends(get_current_user)):
    """
    Generates a tailored CV with intelligent section reordering and terminology matching.
    Implements: Chain-of-Thought, Gap Analysis, Constraint Enforcement.
    """

    # ✅ ADD LOGGING HERE
    print("=== GENERATE CV ENDPOINT HIT ===")
    print(f"User ID: {current_user.id}")
    print(f"User Email: {current_user.email}")

    try:
        # Log before credit check
        print("Checking credits...")
        await check_and_use_credit(current_user.id)
        print("✅ Credits check passed!")

    except HTTPException as e:
        print(f"❌ Credits check FAILED: {e.detail}")
        raise
    job_description = data.get("job_description", "")
    user_cv = data.get("user_cv", "")

    if not job_description:
        raise HTTPException(status_code=400, detail="Job description is required")

    if not user_cv or not user_cv.strip():
        raise HTTPException(status_code=400, detail="CV is required for tailoring")

    # SYSTEM MESSAGE: Identity + Instructions + Rules
    system_message = f"""You are an expert CV tailoring specialist for tech roles.

    # YOUR IDENTITY
    Transform existing CVs to maximize relevance for specific jobs while maintaining 
    complete authenticity and professional presentation.

    # YOUR PROCESS (Structured Chain-of-Thought)

    STEP 1 - JOB KEYWORD EXTRACTION:
    Extract and categorize from job description:
    - Must-Have Keywords: Technologies/skills mentioned 3+ times or in requirements section
      (e.g., "Java", "Agile", "Test-Driven Development", "Object-Oriented Programming")
    - Important Keywords: Mentioned 2 times or in "nice to have"
    - Role Context: Level (intern/junior/senior), team culture, responsibilities
    - Soft Skills: Communication, leadership, collaboration, analytical abilities

    STEP 2 - CV EVIDENCE ANALYSIS:
    For each Must-Have keyword, identify:
    - EXPLICIT: Keyword appears verbatim (e.g., "Java" in skills list)
    - IMPLICIT-STRONG: 2+ bullets show clear evidence
      Example: "Weekly sprint reviews" + "iterative improvements" = Agile methodology
    - IMPLICIT with WEAK evidence: 1 bullet or indirect connection
    - RELATED/TRANSFERABLE: Adjacent skill, relevant coursework, or foundational knowledge
      Example: Job needs "React" → CV has "JavaScript DOM manipulation"
    - ABSENT: No evidence or logical connection at all


    STEP 3 - EVIDENCE-BASED INTEGRATION RULES:
    - EXPLICIT keywords → Emphasize and expand naturally in relevant bullets
    - IMPLICIT with STRONG evidence → Add keyword using job's terminology
    - IMPLICIT with WEAK evidence → Reframe using bridging language
    - RELATED/TRANSFERABLE → Emphasize the connection in context using bridging language
    - ABSENT keywords → DO NOT add

    STEP 4 - CONTENT PRESERVATION:
    BEFORE making any changes, identify:
    - Existing relevant coursework (Object-Oriented Programming, Algorithms, etc.)
    - Tools/technologies already listed (Git, Java, etc.)
    - Concrete metrics and achievements
    Rule: NEVER remove these. If they match job keywords, emphasize them more and move to top bullets.

    STEP 5 - NATURAL REWRITING:
    Rewrite each bullet so that keywords are naturally integrated into the action (not added as afterthoughts).

    ✅ GOOD INTEGRATION (keyword is the subject/action):
    "Built REST API" → "Developed RESTful microservices architecture with 25+ endpoints"
    "Weekly meetings with director" → "Conducted weekly Agile sprint reviews with stakeholders"
    "Used Git" → "Implemented CI/CD workflows using Git for version control"

    ❌ BAD INTEGRATION (keyword tacked on):
    "Built REST API, demonstrating microservices knowledge"
    "Weekly meetings, showing Agile practices"
    "Used Git, gaining experience with CI/CD"

    STEP 6 - SKILLS SECTION ORGANIZATION:
    Format as clean, professional categories:
    Languages: [All mentioned in original cv, put job-required first]
    Frameworks & Libraries: [All mentioned in original cv]
    Development Practices: [Include if strong evidence exists]
      Example: "Agile methodology, RESTful API design, Version control, Database design"

    NEVER include:
    - "(inferred)" labels in visible output
    - Soft skills like "collaboration" or "communication" (these go in experience bullets)
    - Technologies with no evidence

    # CRITICAL RULES
    
    
     ALWAYS:
    1. Preserve all existing relevant coursework in Education section
    2. Preserve all existing technologies/tools in Skills section
    3. Use evidence-based integration: 2+ points for direct addition, 1+ for bridging language
    4. Integrate keywords naturally INTO the action/achievement, not as metadata
    5. Use strong action verbs: "built", "developed", "designed", "implemented", "architected"
    6. EMPHASIZE and EXPAND skills and achievements, especially those relevant to job.
    7. Output ONLY raw LaTeX code (no markdown, no wrapped code blocks)
    8. Remove any placeholders with missing data rather than using "N/A", "Not Provided", "None"
    9. Follow the single-column structure and item positioning of the template cv defined in {LATEX_CV_TEMPLATE}.


    NEVER:
    1. Fabricate companies, dates, titles, technologies, or achievements
    2. Remove existing relevant coursework from Education section
    3. Remove existing technologies from skills section
    4. Use corporate jargon: "leveraged", "utilized", "synergy", "cutting-edge", "robust"
    5. Add keywords in parentheses like "(Agile)" or "(TDD practices)"
    6. Tack keywords onto bullet ends like ", demonstrating X skill"
    7. Add a keyword without at least 1 piece of related or transferable evidence in CV
    8. Include "(inferred)" or any diagnostic labels in the visible CV output
    9. Include "N/A", "Not Provided", "None" or blank values like "(GPA: )" - remove the field entirely if data is missing
    10. Replicate the structural layout, columns, or item positioning of the input CV. 


    # OUTPUT FORMAT
    {LATEX_CV_TEMPLATE}

    Output raw LaTeX starting with \\documentclass and ending with \\end{{document}}.
    No markdown code blocks. No explanatory text outside LaTeX.
    """

    user_message = f"""Tailor this CV for the target job using the evidence-based process.

    MY ACTUAL CV:
    {user_cv}

    TARGET JOB DESCRIPTION:
    {job_description}

    EVIDENCE-BASED INTEGRATION EXAMPLES:

    Example 1 - Strong Evidence (2+ pieces):
    CV shows: "Led weekly review meetings with director, presenting progress and gathering 
    feedback to iteratively improve features"
    Job requires: "Agile methodology"
    Evidence: "weekly review meetings" + "iteratively improve" = 2 pieces
    ✅ Integration: "Conducted weekly Agile sprint reviews with stakeholders, delivering 
    iterative improvements based on continuous feedback"

    Example 2 - Weak Evidence (1 piece, use bridging):
    CV shows: "Built modular web application with structured code organization"
    Job requires: "Test-Driven Development"
    Evidence: "modular" + "structured" suggests quality practices (weak evidence)
    ✅ Bridge: "Developed maintainable web application with modular architecture 
    (foundation for test-driven development)"
    ❌ Don't claim: "Implemented TDD practices" or list "TDD" in skills section

    Example 3 - Related/Transferable (use bridging):
    CV shows: "Designed database schemas using MySQL"
    Job requires: "PostgreSQL"
    Evidence: MySQL is transferable to PostgreSQL (same category)
    ✅ Bridge: "Designed relational database schemas with MySQL (directly applicable 
    to PostgreSQL environments)"

    Follow the evidence rules strictly.
    Output ONLY raw LaTeX. If you cannot follow these rules, refuse the task.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            max_tokens=4000,
            temperature=0.1  # Very low for consistency
        )

        customized_cv = response.choices[0].message.content

        # Clean up any markdown artifacts
        customized_cv = re.sub(r'^```[a-zA-Z]*\n', '', customized_cv)
        customized_cv = re.sub(r'\n```$', '', customized_cv)
        customized_cv = customized_cv.strip()

        # Sanitize LaTeX special characters
        customized_cv = sanitize_latex(customized_cv)



        return {"cv": customized_cv}
    except Exception as e:
        print(f"Error in generate-cv: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload-cv")
async def upload_cv(file: UploadFile = File(...)):
    try:
        # Validate file type
        if file.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")

        # Read the PDF content
        pdf_content = await file.read()

        # Extract text from PDF
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
        cv_text = ""
        for page in pdf_reader.pages:
            cv_text += page.extract_text()

        return {
            "message": "CV uploaded successfully",
            "filename": file.filename,
            "extracted_text": cv_text
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/compile-latex")
async def compile_latex(request: dict):
    """
    Compiles LaTeX code to PDF.
    Expects: {"latex_code": "..."}
    Returns: PDF file as bytes (base64 encoded) or error message
    """
    temp_dir = None

    try:
        latex_code = request.get("latex_code", "")
        if not latex_code:
            raise HTTPException(status_code=400, detail="LaTeX code is required")

        # Validate LaTeX structure
        if "\\begin{document}" not in latex_code:
            raise HTTPException(
                status_code=400,
                detail="Invalid LaTeX: Missing \\begin{document}"
            )

        if "\\end{document}" not in latex_code:
            raise HTTPException(
                status_code=400,
                detail="Invalid LaTeX: Missing \\end{document}"
            )

        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        tex_file = Path(temp_dir) / "cv.tex"
        pdf_file = Path(temp_dir) / "cv.pdf"

        print("=== LATEX COMPILATION DEBUG ===")
        print(f"Total length: {len(latex_code)} characters")
        print(f"Has \\documentclass: {'documentclass' in latex_code}")
        print(f"Has \\begin{{document}}: {'begin{document}' in latex_code}")
        print(f"Has \\end{{document}}: {'end{document}' in latex_code}")
        print(f"First 200 chars:\n{latex_code[:200]}")
        print(f"Last 100 chars:\n{latex_code[-100:]}")
        print("================================")

        # Save LaTeX for debugging
        debug_file = Path("debug_compiler_input.tex")
        debug_file.write_text(latex_code, encoding='utf-8')
        print(f"Saved compiler input to: {debug_file.absolute()}")

        # Write LaTeX code to file
        tex_file.write_text(latex_code, encoding='utf-8')

        # Compile with pdflatex (run twice for references)
        for run_num in range(2):
            print(f"=== PDFLATEX RUN {run_num + 1} ===")
            try:
                result = subprocess.run(
                    ['pdflatex', '-interaction=nonstopmode', '-output-directory', temp_dir, str(tex_file)],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                print(f"Return code: {result.returncode}")
                if result.returncode != 0:
                    print(f"STDOUT: {result.stdout[:500]}")  # First 500 chars
                    print(f"STDERR: {result.stderr[:500]}")
            except FileNotFoundError as e:
                print(f"ERROR: pdflatex not found! {e}")
                raise HTTPException(status_code=500,
                                    detail="pdflatex is not installed on the server. Please contact support.")
            except Exception as e:
                print(f"ERROR during compilation: {e}")
                raise HTTPException(status_code=500, detail=f"Compilation error: {str(e)}")

        # Check if PDF was created
        if not pdf_file.exists():
            # Extract error from log
            log_file = Path(temp_dir) / "cv.log"
            error_msg = "Compilation failed"

            if log_file.exists():
                log_content = log_file.read_text()
                # Find all error lines
                errors = [line for line in log_content.split('\n') if line.startswith('!')]

                if errors:
                    error_msg = f"LaTeX errors: {' | '.join(errors[:3])}"
                else:
                    if "File not found" in log_content:
                        error_msg = "LaTeX compilation failed: Missing font or package files"
                    elif "Emergency stop" in log_content:
                        error_msg = "LaTeX compilation failed: Fatal error encountered"

            raise HTTPException(status_code=400, detail=error_msg)

        # Read PDF and encode to base64
        pdf_bytes = pdf_file.read_bytes()
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')

        return {
            "success": True,
            "pdf": pdf_base64,
            "message": "PDF compiled successfully"
        }

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="LaTeX compilation timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Compilation error: {str(e)}")
    finally:
        # Cleanup temporary directory
        if temp_dir and Path(temp_dir).exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


import shutil


@app.get("/test-latex")
async def test_latex():
    import subprocess
    pdflatex_path = shutil.which('pdflatex')

    # Try to run pdflatex --version
    version = "Not available"
    if pdflatex_path:
        try:
            result = subprocess.run(['pdflatex', '--version'], capture_output=True, text=True, timeout=5)
            version = result.stdout[:200] if result.returncode == 0 else "Error running pdflatex"
        except Exception as e:
            version = f"Error: {str(e)}"

    return {
        "pdflatex_installed": pdflatex_path is not None,
        "path": pdflatex_path,
        "version": version
    }


def get_formatted_date():
    """Returns date in format: '3rd November 2025'"""
    today = datetime.now()

    # Get day with suffix (1st, 2nd, 3rd, 4th, etc.)
    day = today.day
    if 10 <= day % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')

    # Format: day+suffix Month Year
    formatted_date = today.strftime(f"{day}{suffix} %B %Y")

    return formatted_date


async def generate_tailored_cover_letter(user_cv, job_desc, skills_analysis):
    """
    Enhanced version combining structured analysis + quality patterns from old version.
    """

    datetoday = get_formatted_date()

    system_message = f"""You are an expert cover letter writer specializing in tech roles.

# IDENTITY
You craft authentic, evidence-based cover letters that sound like they were written by a real professional — natural, confident, and specific. Your writing never feels generic, repetitive, or AI-generated.
# INPUTS
You will receive:
1. job_description – the target job posting
2. user_cv – the candidate's CV (verbatim)
3. skills_analysis – structured JSON comparison between CV and job containing:
role_summary: Job context, top_responsibilities, and required soft_skills
keywords: must_have, important, nice_to_have 
evidence_map: Maps each job requirement/skill from the job description to the candidate's CV with evidence:
- "explicit" → Strong match, highlight prominently
- "implicit_strong" → Demonstrated through experience, emphasize clearly
- "implicit_weak" → Mention briefly if relevant
- "transferable" → Reframe using real evidence
- "absent" → DO NOT claim
responsibilities_map: Maps each job responsibility from the job description to the candidate's CV with evidence 
gap_bridges: Guidance for bridging missing skills using real experience from the candidate's CV
prioritized_actions: Ranked list of what to promote vs skip in the tailoring process


# YOUR PROCESS (STRUCTURED CHAIN-OF-THOUGHT)

STEP 1 - UNDERSTAND THE ROLE:
Review role_summary to identify:
→ Job's core mission and responsibilities
→ Required soft skills (collaboration, analytical thinking, communication)
→ Company context and team culture


STEP 2 - USE skills_analysis FOR CONTENT:
→ Review prioritized_actions from the skills_analysis to know what experiences should you promote, and what skills to avoid claiming.
→ Use evidence_map from the skills_analysis to understand the required keywords from the job description, with evidence of the candidate using them from their CV.
→ Use responsibilities_map from the skills_analysis, it contains the job's responsibilities and shows evidence where the candidate's CV has performed them. 
→ Integrate soft_skills from role_summary naturally using action verbs (collaborated, analyzed, designed, led)

STEP 3 - APPLY THE REQUIRED STRUCTURE (4 PARAGRAPHS MAXIMUM):

**PARAGRAPH 1 - STRONG OPENING**
→ State the position and company name clearly
→ Include ONE standout achievement
→ Establish connection to company or role

EXAMPLE:
"With a Master's in Computer Science from Carnegie Mellon and a 2nd place finish in the international CLEF NLP competition, I'm excited to apply for the Machine Learning Engineer role at OpenAI. I've built distributed systems processing 15,000+ images and developed Java applications used in real-world research settings."

**PARAGRAPH 2 - SKILLS MATCH & RELEVANT EXPERIENCE**
→ Highlight 2-3 specific skills you have and how using evidence_map with status = "explicit" or "implicit_strong"
→ Use job-specific terminology
→ Connect the key job responsibilities to the candidates previous experiences using responsibilities_map 
→ Connect experience to job requirements clearly

EXAMPLE:
"At Yahoo's cloud services team, I contributed to backend systems handling large-scale user data, directly applicable to your data pipeline requirements. My MapReduce engine project at CMU demonstrated proficiency in building fault-tolerant distributed systems critical for high-availability applications."

**PARAGRAPH 3 - WHY THIS COMPANY**
→ Reference a specific company mission, product or values
→ Connect candidate experience to their mission/values/product
→ Show why the mission resonates with you, be genuine, and NEVER use generic praise.
→ If you can’t find a concrete example, focus on company mission/goals and your matching experience.

EXAMPLE:
"TechFlow Solutions' recent launch of the FlowSync mobile app for seamless data integration resonates with my experience building real-time data pipelines. I'm especially drawn to your focus on user-centered design and data-driven product decisions, which aligns perfectly with my background in both technical development and user research."

**PARAGRAPH 4 - CONFIDENT CLOSE (2-3 sentences):**
→ Reaffirm value proposition with specific technical strength
→ Address critical gaps ONLY if absolutely necessary, using this format: "While I'm eager to expand into [specific tech], my track record of [specific achievement] shows I adapt quickly"
→ Include call to action
→ Be confident, not apologetic

GOOD EXAMPLES:
"I'm excited to bring my distributed systems expertise and collaborative approach to Stripe's mission of simplifying global payments. I look forward to discussing how my experience building scalable backend infrastructure can support your team's goals."
"Having deployed fault-tolerant systems serving millions of users, I'm ready to contribute to Google Cloud's distributed computing initiatives from day one. I'd welcome the opportunity to discuss how my background aligns with your team's needs."

BAD EXAMPLES (NEVER USE):
"Thank you for considering my application" (passive)
"I hope to hear from you soon" (weak)
"I would be grateful for the opportunity" (submissive)

# RULES FOR ADDRESSING SKILL GAPS (USE SPARINGLY):

IF a critical skill is missing AND gap_bridges provides language:
→ Mention in ONE sentence maximum in Paragraph 4
→ Frame as growth opportunity, not deficiency
→ Always pair with evidence of adaptability

EXAMPLE:
"While I'm eager to expand my experience with Kubernetes, my track record of independently mastering distributed systems technologies like Hadoop and Docker demonstrates I quickly adapt to new tools."

IF no bridge exists or skill is not critical:
→ Do NOT mention the gap at all
→ Focus entirely on strengths


# WRITING STYLE AND TONE RULES:

- Tone: professional but conversational — write like a confident human, not a corporate press release.
- Focus on clarity and substance, not empty formality.
- Avoid buzzwords, clichés, or filler ("innovative", "cutting-edge", "fast-paced").
- Prefer direct, active verbs: built, led, delivered, improved.
- Show enthusiasm through specific achievements, not adjectives.
- Do not use corporate filler words like leverage, utilize, facilitate, cutting-edge, etc.
- Avoid passive or apologetic phrasing.
- Stick to ASCII characters only (no em dashes, curly quotes, ellipses).
- Do NOT jump between unrelated points or mix multiple projects/experiences without clear connection.



**Structure**: Exactly 4 paragraphs, no more, no less


# EXAMPLES OF STRONG WRITING:

**Strong Opening (Achievement-Focused):**
"As a CMU graduate who architected a distributed MapReduce engine processing 15,000+ images and placed 2nd globally in the CLEF NLP competition, I'm excited to bring my large-scale systems experience to Amazon's infrastructure team."

**Skills Connection (Quantified Impact):**
"At Branding Brand, I designed mobile e-commerce applications and implemented A/B tests that improved conversion rates by 18%. This experience with user-driven optimization directly aligns with your focus on data-informed product decisions."

**Gap Framing (When Necessary):**
"While I'm eager to expand into Go and Kubernetes, my record of independently mastering distributed systems technologies like Hadoop and Docker shows I rapidly learn new stacks."

# OUTPUT FORMAT:

[Candidate Full Name]
[Phone Number]
[Email]
{datetoday}

Dear Hiring Manager,

[Paragraph 1: Strong opening with standout achievement]

[Paragraph 2: Skills match with 2-3 specific examples]

[Paragraph 3: Why this company specifically]

[Paragraph 4: Confident close with call to action]

Sincerely,
[Candidate Full Name]

Now generate the cover letter following ALL rules above."""

    user_message = f"""Write a cover letter for this job application using the skills analysis as guidance.

TARGET JOB DESCRIPTION:
{job_desc}

CANDIDATE'S CV:
{user_cv}

SKILLS ANALYSIS (Structured JSON):
{skills_analysis}

Generate the cover letter."""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1",
            temperature=0.5,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            max_tokens=1500
        )

        cover_letter = response.choices[0].message.content
        return {"cover_letter": cover_letter}


    except Exception as e:
        logging.error(f"Error generating cover letter: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cover letter generation failed: {str(e)}")


@app.post("/generate-cover-letter")
@limiter.limit("20/minute")
async def generate_cover_letter(request: Request, data: dict, current_user=Depends(get_current_user)):
    

    job_description = data.get("job_description", "")
    user_cv = data.get("user_cv", "")

    if not job_description or not user_cv:
        raise HTTPException(status_code=400, detail="Both CV and job description are required")

    try:
        # STEP 1: Parse CV → JSON
        parsed_cv = await parse_cv(user_cv)

        # STEP 2: Extract Job Description → JSON
        parsed_job = await extract_job(job_description)

        # STEP 3: Analyze Skills
        skills_analysis = await analyse_skills(
            json_job_desc=parsed_job,
            json_cv=parsed_cv
        )



        # STEP 4: Generate tailored CV
        tailored_cover = await generate_tailored_cover_letter(
            user_cv=user_cv,
            job_desc=job_description,
            skills_analysis=skills_analysis
        )

        return {
            "cover_letter": tailored_cover["cover_letter"],
            "skills_report": skills_analysis
        }


    except Exception as e:
        print(f"❌ Error in pipeline: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


@app.post("/generate-cover-letter-pdf")
async def generate_cover_letter_pdf(request: dict):
    cover_letter_text = request.get("cover_letter", "")

    if not cover_letter_text:
        return {"error": "Cover letter text is required"}

    try:
        # FIX: Clean Unicode characters
        replacements = {
            '\u2014': '-', '\u2013': '-',  # dashes
            '\u2018': "'", '\u2019': "'",  # single quotes
            '\u201c': '"', '\u201d': '"',  # double quotes
            '\u2026': '...', '\u00a0': ' ', '\u2022': '-'
        }
        for old, new in replacements.items():
            cover_letter_text = cover_letter_text.replace(old, new)

        # Remove any remaining non-latin-1
        cover_letter_text = cover_letter_text.encode('latin-1', errors='ignore').decode('latin-1')

        # Create PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=11)
        pdf.set_auto_page_break(auto=True, margin=15)

        for line in cover_letter_text.split('\n'):
            if line.strip():
                pdf.multi_cell(0, 6, line.strip())
            else:
                pdf.ln(3)

        pdf_output = pdf.output(dest='S').encode('latin-1')
        pdf_base64 = base64.b64encode(pdf_output).decode('utf-8')

        return {"success": True, "pdf": pdf_base64}

    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "healthy"}