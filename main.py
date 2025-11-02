
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
    \faPhone\ \underline{[PHONE]} ~ 
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
async def get_credits(current_user = Depends(get_current_user)):
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


@app.post("/analyze-skills")
async def analyze_skills(request: dict):
    """
    Analyzes skill gaps between CV and job description.
    Returns only truly missing technical skills.
    """
    job_description = request.get("job_description", "")
    user_cv = request.get("user_cv", "")

    if not job_description or not user_cv:
        raise HTTPException(status_code=400, detail="Missing required fields")

    # SYSTEM MESSAGE: Identity + Process + Rules
    system_message = """You are a technical skill gap analyzer for tech job applications.

# YOUR IDENTITY
You identify missing technical skills, methodologies, and processes with precision and categorization.

# YOUR PROCESS

STEP 1 - EXTRACT JOB REQUIREMENTS:

A) CRITICAL TECHNICAL:
   - Programming languages, frameworks, databases, tools
   - Example: "Docker", "Go", "PostgreSQL", "Kubernetes"

B) METHODOLOGIES & PROCESSES (look for these specifically):
   - API Design: "REST", "RESTful APIs", "GraphQL", "API development"
   - Architecture: "Microservices", "Event-driven", "Serverless"
   - DevOps: "CI/CD", "Docker", "Kubernetes", "Terraform"
   - Testing: "TDD", "Unit testing", "Integration testing", "QA"
   - Development: "Agile", "Scrum", "Version control"
   - Security: "Security practices", "Authentication", "Authorization"

C) NICE-TO-HAVE (mentioned 1-2 times OR in "Nice to have" section):
   - Secondary tools or technologies

STEP 2 - CHECK CV EVIDENCE:
For each requirement:
- EXPLICIT: Appears by name (e.g., "Docker" in skills)
- IMPLICIT-STRONG: 2+ pieces of evidence
  * "built REST endpoints" + "JSON APIs" = REST experience
  * "automated deployment" + "containerized apps" = CI/CD knowledge
- TRANSFERABLE: Related technology (MySQL → PostgreSQL, Git → Bitbucket)
- ABSENT: No evidence whatsoever

# CRITICAL RULES
- Accept implicit evidence (don't require exact keywords)
- Be generous with transferable skills
- Flag methodologies even if not explicitly listed as "skills"
- DON'T flag soft skills

#OUTPUT FORMAT
NO explanations. NO additional text. Just the list."""

    # USER MESSAGE: Context + Examples
    user_message = f"""Analyze this CV against the job description.

JOB DESCRIPTION:
{job_description}

CANDIDATE'S CV:
{user_cv}

EXAMPLES OF EVIDENCE EVALUATION:

Example 1 - NOT Missing (Implicit Evidence):
Job requires: "Agile methodology"
CV shows: "weekly sprint reviews" + "iterative development"
Decision: NOT missing (clear Agile evidence)

Example 2 - NOT Missing (Related Technology):
Job requires: "PostgreSQL"
CV shows: "MySQL database design"
Decision: NOT missing (transferable SQL experience)

Example 3 - Missing (No Evidence):
Job requires: "Docker"
CV shows: No containerization, deployment, or DevOps experience
Decision: Missing

Example 4 - NOT Missing (Different Terminology):
Job requires: "RESTful API design"
CV shows: "built HTTP endpoints" + "JSON responses"

Now analyze and output only truly missing skills as comma-separated list."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Fast and cost-effective
            temperature=0,  # Deterministic output
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            max_tokens=150
        )

        result = response.choices[0].message.content.strip()

        # Parse output
        if result.lower() == 'none' or not result:
            missing_skills = []
        else:
            missing_skills = [s.strip() for s in result.split(',') if s.strip()]

        return {"missing_skills": missing_skills}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Skill analysis failed: {str(e)}"
        )


@app.post("/generate-cv")
@limiter.limit("25/minute")
async def generate_cv(request: Request, data: dict, current_user = Depends(get_current_user)):
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
    - RELATED/TRANSFERABLE → Emphasize the connection in context using bridging language    - ABSENT keywords → DO NOT add

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

    Follow the evidence rules strictly. When in doubt, DON'T add the keyword.
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

@app.post("/generate-cover-letter")
@limiter.limit("20/minute")
async def generate_cover_letter(request: Request, data: dict, current_user = Depends(get_current_user)):
    """
    Generates a tailored cover letter following strict requirements.
    Implements: RAG, Constraint Enforcement, Few-Shot Learning patterns.
    """

    await check_and_use_credit(current_user.id)

    job_description = data.get("job_description", "")
    user_cv = data.get("user_cv", "")

    if not job_description:
        return {"error": "Job description is required"}

    if not user_cv:
        return {"error": "CV is required"}

    # SYSTEM MESSAGE: Identity + Rules + Constraints
    system_message = """You are an expert cover letter writer specializing in tech roles.

# IDENTITY
You craft authentic, compelling cover letters that connect candidate experience to job requirements without sounding generic or AI-generated.

# RULES YOU MUST FOLLOW

FORBIDDEN PHRASES - NEVER use these:
- "Dear Sir or Madam"
- "cutting-edge"
- "leveraged"
- "utilized"
- "facilitated"
- "robust"
- "innovative company" (without specifics)

FORBIDDEN CHARACTERS - NEVER use these:
- Em dashes (—) - use regular dash (-) instead
- En dashes (–) - use regular dash (-) instead  
- Curly quotes (" " ' ') - use straight quotes (" ') instead
- Ellipsis (…) - use three periods (...) instead
- Any Unicode characters - use only standard ASCII

REQUIRED STRUCTURE (4 paragraphs max):

PARAGRAPH 1 - Strong Opening:
- State position and connection to company
- Include ONE standout achievement with numbers/impact
Example: "With a Master's in Computer Science from CMU and 2nd place finish in 
the international CLEF competition, I'm excited to apply for..."

PARAGRAPH 2 - Relevant Experience:
- 2-3 specific examples connecting CV to job requirements
- Use job's terminology, quantify impact
- Focus on transferable qualities (systems thinking, collaboration, scale)

PARAGRAPH 3 - Company-Specific Research:
- Reference specific products/initiatives by name
- Show why their mission resonates (be genuine, not generic)

PARAGRAPH 4 - Confident Close:
- ONE sentence max on skill gaps (if critical): "While I'm eager to expand into 
[specific tech], my track record of [specific achievement] shows I adapt quickly"
- Strong value proposition
- Call to action

PARAGRAPH 4 EXAMPLES:

Strong Confidence:
"I'm excited to bring my [specific technical strength] and [specific quality] to 
[company]'s mission of [specific goal]. I'd welcome the opportunity to discuss how 
my experience in [relevant area] aligns with your team's needs."

Achievement-Focused:
"Having [specific achievement], I'm ready to contribute to [company initiative] 
from day one. I look forward to discussing how my background in [technical area] 
can support your team's goals."

Research-Driven:
"[Company product]'s approach to [specific feature] aligns perfectly with my passion 
for [technical area]. I'm eager to discuss how my experience building [relevant system] 
can contribute to your team's success."

NEVER use:
- "Thank you for considering my application" (passive)
- "I hope to hear from you" (weak)
- "I would be grateful for the opportunity" (submissive)

WRITING RULES:
- Achievements > Gaps (80% strengths, max 20% gaps)
- Quantify everything possible (numbers, rankings, scale)
- Never apologize or deflate
- If they lack a critical skill, frame as "eager to expand" not "unfortunately lacking"


OUTPUT FORMAT:
[Candidate Full Name]
[Phone Number]
[Email]

[Current Date]

["Hiring Team at [Company Name]"]

[Cover letter body - 4 paragraphs maximum]

WRITING STYLE:
- Use simple, direct language: "built", "created", "developed", "used", "new"
- Be specific and concrete, never generic
- Show genuine research about the company
- Keep each paragraph to 2-3 sentences maximum

"""

    # USER MESSAGE: Task + Context (RAG pattern)
    user_message = f"""Write a cover letter for this job application.

TARGET JOB DESCRIPTION:
{job_description}

CANDIDATE'S CV:
{user_cv}

EXAMPLES OF STRONG PARAGRAPHS:

Example 1 - Achievement Opening:
"As a Carnegie Mellon graduate who architected a fault-tolerant MapReduce engine 
processing 15,000+ images and achieved 2nd place internationally in the CLEF NLP 
competition, I'm excited to bring my distributed systems expertise to Visa's mission 
of building next-generation payment infrastructure."

Example 2 - Experience Connection with Scale:
"At Yahoo's cloud services team, I contributed to backend systems processing millions 
of user records daily - experience directly applicable to Visa's transaction volumes. 
My MapReduce engine project demonstrated proficiency in building resilient, 
fault-tolerant systems critical for payment processing."

Example 3 - Gap Framing (one sentence only):
"While I'm eager to expand into Go and Docker, my track record of independently 
building production-ready systems in Java and Python demonstrates I quickly master 
new technologies."

Now write the cover letter following all rules and using these patterns."""

    response = client.chat.completions.create(
        model="gpt-4.1",
        temperature=0.3,  # Low temperature for consistency
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ],
        max_tokens=1500
    )

    cover_letter = response.choices[0].message.content
    return {"cover_letter": cover_letter}


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