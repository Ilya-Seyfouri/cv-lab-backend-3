from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Request, status
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

import json
from generations import (
    save_generation,
    get_user_generations,
    get_generation_by_id,
    delete_generation,
    get_generation_stats
)
from typing import Optional


import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

load_dotenv()


def log_tokens(endpoint_name: str, response):
    """Log token usage for API calls"""
    tokens = response.usage.total_tokens
    logging.info(f"🔢 {endpoint_name}: {tokens} tokens")
    return tokens

CORPORATE_LATEX_CV_TEMPLATE = r"""
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
\fancyhf{} % clear all header and footer fields
\fancyfoot{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}

% Adjust margins
\addtolength{\oddsidemargin}{-0.15in}
 \addtolength{\textwidth}{0.3in}

\urlstyle{same}

\raggedbottom
\raggedright
\setlength{\tabcolsep}{0in}

% Sections formatting
\titleformat{\section}{
  \vspace{-4pt}\scshape\raggedright\large\bfseries
}{}{0em}{}[\color{black}\titlerule \vspace{-5pt}]

% Ensure that generate pdf is machine readable/ATS parsable
\pdfgentounicode=1

%-------------------------
% Custom commands
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
    {\Large \scshape Alexander J. Morgan} \\[2mm]
    \footnotesize \raisebox{-0.1\height}
    \faPhone\ \underline{07715278065} ~ 
    {\faEnvelope\  \underline{alex.morgan@email.com}} ~ 
    {\faLinkedin\ \underline{\href{https://www.linkedin.com/in/alexjmorgan}{linkedin.com/in/alexjmorgan}}
    \vspace{-8pt}
\end{center}

 %-----------EDUCATION-----------
\section{Education} \\[1mm]
  \resumeSubHeadingListStart
    \resumeSubheading
      {University of Newcastle}{Expected Graduation: May 2026}
      {Bachelor of Economics}
      {Newcastle Upon Tyne}
  \resumeSubHeadingListEnd
    \resumeItemListStart
        \resumeItem {\textbf{GPA: 2:1}}
        \vspace{-7pt}
        \resumeItem {Courses: Linear algebra, Calculus and Analysis, Probability, Statistics, Business Microeconomics, Business Macroeconomics}
    \resumeItemListEnd
    \vspace{-12pt}
%-----------Experience---------------
\section{Work Experience}
    \resumeSubHeadingListStart
                \resumeSubheading{Golden Goose Capital}{Jun 2025 -- Aug 2025}{Summer Sales Internship}{} 
                \resumeItemListStart
                    \resumeItem{Achieved Top Sales Representivative status within the first three weeks, exceeding sales targets.}
                    \resumeItem{Trained and mentored new interns, making my skills teachable and replaceable for long-term team success.}
                    \resumeItem{Developed resilience by overcoming rejection and adapting sales strategies to different customer profiles.}
                    \resumeItem{Strengthened effective communication and the ability to articulate complex ideas clearly to diverse clients.}
                    \resumeItem{Gained adaptability by responding dynmically to different customer needs and market changes.}
                    \resumeItem{Played a key role in expanding client campaigns, driving \textbf{20\%} revenue growth through strategic customer acquisition.}
                    
                      
                    \resumeItemListEnd
            \resumeSubheading{Harborview Strategic Advisors}{Jan 2025 -- May 2025}{Global Markets Intern}{} 
                \resumeItemListStart
                    \resumeItem{Completed a live simulation as a sales trader working with a group of asset managers.}
                    \resumeItem{Executed superior bids and offers for buy-side clients, consistently outperforming exchange prices.}
                    \resumeItem{Effectively managed risk while multitasking and executing multiple client trades.}
                    \resumeItem{Generated \textbf{\$150,000} in commission and achieved a P&L exceeding \textbf{\$3 million} in under 15 minutes during the simulation.}
                    \resumeItemListEnd
                    
            \resumeSubheading{Pacific Ridge Technologies}{Aug 2024 -- Dec 2024}{Banking Intern}{}
                \resumeItemListStart
                    \resumeItem{Analysed transaction data to develop a summary of debt capital markets (DBM) activity.}
                    \resumeItem{Matched financial products with various clients}
                    \resumeItem{Defined the strategic rationale for M&A and filtered target}
                    \resumeItemListEnd
    \resumeSubHeadingListEnd
    \vspace{-12pt}
%-----------LEADERSHIP-----------
\section{Leadership}
\resumeSubHeadingListStart

    \resumeSubheading
  {Newcastle Investment Society}{Aug 2025 -- Present}
  {Vice President}{}
\resumeItemListStart
  \resumeItem{Led and coordinated workshops on equity valuation, portfolio construction, and macroeconomic analysis for society members}
  \resumeItem{Organised speaker events and training sessions with industry professionals to improve members’ practical investment skills}
  \resumeItem{Mentored junior members in financial markets fundamentals and investment research techniques}
\resumeItemListEnd

    \resumeSubheading
      {Akuna Capital}{Jan 2024 -- May 2024}
      {101 Course}{}
    \resumeItemListStart
        \resumeItem{Gained foundational knowledge of options trading, including calls,puts and market-making strategies.}
        \resumeItem{Participated in trading quiz's, applying theoretical knowledge to real-world scenarios.}
        \resumeItem{Engaged in real life trading simulations for apple, equities, FX and commodities.}
    \resumeItemListEnd

   

\resumeSubHeadingListEnd
\vspace{-12pt}
  %-----------PROGRAMMING SKILLS-----------
\section{Technical Skills}
 \begin{itemize}[leftmargin=0.15in, label={}]
    \small{\item{   
     \textbf{Soft}{: Collaboration, Communication, Analytical Thinking, Organisation, Problem Solving, Teamwork, Resilience, Adapatability} \\[1mm]
     \textbf{Technical}}{: Python, R Studio, Microsoft Excel, Microsoft Word, Microsoft PowerPoint} \\[1mm]
     \textbf{Interests}}{: YouTube content creation, yoga (certified instructor), international travel (22 countries), Music (Learning Guitar)}
     \\ [1mm]
    }}
 \end{itemize}
 \vspace{-16pt}
 \vspace{3pt}
\vspace{10pt}

\vspace{-15pt}



\end{document}


"""

TECH_LATEX_CV_TEMPLATE = r"""

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
      {[DEGREE]
      }{[LOCATION]}
  \resumeSubHeadingListEnd
    \resumeItemListStart
        \resumeItem {[HONORS] | \textbf{GPA: [GPA]}}
        \resumeItem {Courses: [RELEVANT_COURSES]}
    \resumeItemListEnd

%-----------Experience---------------
\section{Work Experience}
    \resumeSubHeadingListStart
        \resumeSubheading{[COMPANY_1]}{[START_DATE_1] -- [END_DATE_1]}{[JOB_TITLE_1]}{}
            \resumeItemListStart
                \resumeItem{[ACHIEVEMENT_1_1]}
                \resumeItem{[ACHIEVEMENT_1_2]}
                \resumeItem{[ACHIEVEMENT_1_3]}
            \resumeItemListEnd
        \resumeSubheading{[COMPANY_2]}{[START_DATE_2] -- [END_DATE_2]}{[JOB_TITLE_2]}{}
            \resumeItemListStart
                \resumeItem{[ACHIEVEMENT_2_1]}
                \resumeItem{[ACHIEVEMENT_2_2]}
                \resumeItem{[ACHIEVEMENT_2_3]}
            \resumeItemListEnd
        \resumeSubheading{[COMPANY_3]}{[START_DATE_3] -- [END_DATE_3]}{[JOB_TITLE_3]}{}
            \resumeItemListStart
                \resumeItem{[ACHIEVEMENT_3_1]}
                \resumeItem{[ACHIEVEMENT_3_2]}
            \resumeItemListEnd
    \resumeSubHeadingListEnd

%-----------PROJECTS-----------
\section{Projects} 
    \resumeSubHeadingListStart

        \resumeProjectHeading
            {\textbf{[PROJECT_1_NAME]}}
            {{[PROJECT_1_TECH]}}
            \\[5mm]
            \resumeItemListStart
                \resumeItem{[PROJECT_1_DESC_1]}
                \resumeItem{[PROJECT_1_DESC_2]}
            \resumeItemListEnd
            \vspace{-10pt}

         \resumeProjectHeading
            {\textbf{[PROJECT_2_NAME]}}
            {{[PROJECT_2_TECH]}}
            \\[5mm]
            \resumeItemListStart
                \resumeItem{[PROJECT_2_DESC_1]}
            \resumeItemListEnd
            \vspace{-10pt}

         \resumeProjectHeading
            {\textbf{[PROJECT_3_NAME]}}
            {{[PROJECT_3_TECH]}}
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

%-----------SKILLS-----------
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



LAW_LATEX_CV_TEMPLATE = r"""
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
\fancyhf{} % clear all header and footer fields
\fancyfoot{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}

% Adjust margins
\addtolength{\oddsidemargin}{-0.15in}
 \addtolength{\textwidth}{0.3in}

\urlstyle{same}

\raggedbottom
\raggedright
\setlength{\tabcolsep}{0in}

% Sections formatting
\titleformat{\section}{
  \vspace{-4pt}\scshape\raggedright\large\bfseries
}{}{0em}{}[\color{black}\titlerule \vspace{-5pt}]

% Ensure that generate pdf is machine readable/ATS parsable
\pdfgentounicode=1

%-------------------------
% Custom commands
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
    {\Large \scshape Sarah Martinez} \\[2mm]
    \footnotesize \raisebox{-0.1\height}
    \faPhone\ \underline{07715278067} ~ 
    {\faEnvelope\  \underline{sarah.martinez@email.com}} ~ 
    {\faLinkedin\ \underline{\href{https://www.linkedin.com/in/sarahmartinez}{linkedin.com/in/sarahmartinez}}  ~
    \vspace{-8pt}
\end{center}


%-----------PROFESSIONAL SUMMARY-----------
\section{Professional Summary}
\small{
A driven, inquisitive, and ambitious law graduate with First-Class Honours, aiming to begin a career within the legal field. I bring a keen attention to detail and strong research skills from assisting lawyers in conducting legal research and drafting key contract documents in a fast-paced environment
}
\vspace{-4pt}


  %-----------EDUCATION-----------
\section{Education} \\[1mm]
  \resumeSubHeadingListStart
    \resumeSubheading
      {SOAS University of London}{Graduated: May 2019}
      {LLB Law - First Class Honours
      }{London}
  \resumeSubHeadingListEnd
    \resumeItemListStart
        \vspace{-7pt}
        \resumeItem {Courses: Contract Law, Advance Administrative Law, Property Law, Law Terror, State and Power}
    \resumeItemListEnd
    \vspace{-8pt}


%-----------Experience---------------
\section{Work Experience}
    \resumeSubHeadingListStart
                \resumeSubheading{Milbank LLP}{Jan 2022 -- Present}{Legal Internship}{}
                \resumeItemListStart
                    \resumeItem{Completed a tax case study prepared by a Havard Law Professor, where I provided recommendations on settlement actions, utilising analytical skills to undertake due diligence, which informed my reccomendations}
                    \resumeItem{Demostrated communication skills in presented my case analysis, findings and recommendations}
                    
                    \resumeItemListEnd
            \resumeSubheading{Paradigm Solicitors}{Jun 2020 -- Dec 2021}{Legal Internship}{} 
                \resumeItemListStart
                    \resumeItem{Interned across multiple departments including conveyancing, immigration, family and property law where I participated in client meetings by taking detailed meeting notes, providing summaries for lawyers, and undertaking legal research on findings to support lawyers with the next steps.}
                    \resumeItem{Reviewed and drafted legal documents, such as leases and contracts, utilising keen attention to detail to accurately represent client interests.}
                    \resumeItemListEnd
            \resumeSubheading{Nova Solicitors}{May 2019 -- May 2020}{Legal Internship}{}
                \resumeItemListStart
                    \resumeItem{Delivered thorough case summaries for client cases under demanding time constraints, showcasing efficient organisation and an unwavering attention to detail.}
                    \resumeItem{Conducted client comms on behalf of the company, developing my communication skills in taking client calls to gather key documentation and provide updates on ongoing cases.}
                    \resumeItemListEnd
                    
    \resumeSubHeadingListEnd
    \vspace{-12pt}


    
  %-----------SKILLS-----------
\section{Skills}
 \begin{itemize}[leftmargin=0.15in, label={}]
    \small{\item{   
        \textbf{Hard Skills}{: Word, PowerPoint, Excel} \\[1mm]
        \textbf{Soft Skills}{: Legal Research, Attention to Detail, Time Management, Problem Solving} \\[1mm]
    }}
 \end{itemize}
 \vspace{-16pt}
 \vspace{3pt}
\vspace{10pt}


%-----------ADDITIONAL INFORMATION-----------
\section{Extracurricular Activities} 
    \vspace{-3pt}
    \resumeSubHeadingListStart
                   \resumeProjectHeading
            {\textbf{{Founder - Clothing Boutique}}}
            
            \\[5mm]
          \resumeItemListStart
            \resumeItem{Leveraged strong multitasking skills to manage the end-to-end daily operations of my own clothing brand, including supplier coordination, client dress sourcing, and expense management.}
        
          \resumeItemListEnd
          \resumeSubHeadingListEnd
 \vspace{-12pt}

    

\vspace{-15pt}





\end{document}





"""

MEDICAL_LATEX_CV_TEMPLATE = r"""
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
\fancyhf{} % clear all header and footer fields
\fancyfoot{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}

% Adjust margins
\addtolength{\oddsidemargin}{-0.15in}
 \addtolength{\textwidth}{0.3in}

\urlstyle{same}

\raggedbottom
\raggedright
\setlength{\tabcolsep}{0in}

% Sections formatting
\titleformat{\section}{
  \vspace{-4pt}\scshape\raggedright\large\bfseries
}{}{0em}{}[\color{black}\titlerule \vspace{-5pt}]

% Ensure that generate pdf is machine readable/ATS parsable
\pdfgentounicode=1

%-------------------------
% Custom commands
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
    {\Large \scshape Sarah Martinez} \\[2mm]
    \footnotesize \raisebox{-0.1\height}
    \faPhone\ \underline{07715278067} ~ 
    {\faEnvelope\  \underline{sarah.martinez@email.com}} ~ 
    {\faLinkedin\ \underline{\href{https://www.linkedin.com/in/sarahmartinez}{linkedin.com/in/sarahmartinez}}  ~
    \vspace{-8pt}
\end{center}


%-----------PROFESSIONAL SUMMARY-----------
\section{Professional Summary}
\small{
An innovative biomedical science graduate with significant internship experience and a strong background in data analysis and interpretation. Specializing in microbiology with demonstrated expertise in optimizing data/sample collection procedures to improve accuracy. Experienced in conducting experiments and writing reports.
}
\vspace{-4pt}


  %-----------EDUCATION-----------
\section{Education} \\[1mm]
  \resumeSubHeadingListStart
    \resumeSubheading
      {Newcastle University}{Graduated: May 2019}
      {BSc Biomedical Science - 2:1
      }{Newcastle}
  \resumeSubHeadingListEnd
    \resumeItemListStart
        \vspace{-7pt}
        \resumeItem {Eukaroytic Gene Expression, Cellular Immunology, Medical Biotechnology, Bioethic, Epidemiology, Microbioata and Pathogens}
    \resumeItemListEnd
    \vspace{-8pt}


%-----------Experience---------------
\section{Work Experience}
    \resumeSubHeadingListStart
                \resumeSubheading{Sampson Laboratories}{Jan 2022 -- Present}{Research Intern}{} 
                \resumeItemListStart
                    \resumeItem{Completed a 3-month research internship in the R&D department}
                    \resumeItem{Analysed data using statistical methods and programming code, R and SAS}
                    \resumeItem{Contributed to the development and optimisation of experimental protocols}
                    \resumeItem{Wrote scientific reports, including experimental design, results and conclusions.}
                    \resumeItem{Conducted in vitro experiments to research and evaluate the efficacy of novel cell-based therapies for cancer treatment.}
                    
                    \resumeItemListEnd
            \resumeSubheading{NHS Trust}{Jun 2020 -- Dec 2021}{Clinical Research Intern}{} 
                \resumeItemListStart
                    \resumeItem{Conducted diagnostic tests, including PCR and ELISA, for infectious diseases.}
                    \resumeItem{Assisted with the analysis of clinical data and interpretation of laboratory results.}
                    \resumeItem{Maintained laboratory records, including test results and specimen tracking}
                     \resumeItem{Diagnosed and treated several cases of antibiotic - resistant infections.}
                    \resumeItemListEnd
            
                    
    \resumeSubHeadingListEnd
    \vspace{-12pt}


    
  %-----------SKILLS-----------
\section{Core Skills}
 \begin{itemize}[leftmargin=0.15in, label={}]
    \small{\item{   
        {Data Analysis Interpretation, Laboratory Techniques, Scientific Writing, Cellular Biology, Project Management, Data Analysis & Modelling}} \\[1mm]
        
    }}
 \end{itemize}
 \vspace{-16pt}
 \vspace{3pt}
\vspace{10pt}


%-----------ADDITIONAL INFORMATION-----------
\section{Extracurricular Activities} 
    \vspace{-3pt}
    \resumeSubHeadingListStart
                   \resumeProjectHeading
            {\textbf{{Founder - Clothing Boutique}}}
            
            \\[5mm]
          \resumeItemListStart
            \resumeItem{Leveraged strong multitasking skills to manage the end-to-end daily operations of my own clothing brand, including supplier coordination, client dress sourcing, and expense management.}
        
          \resumeItemListEnd
          \resumeSubHeadingListEnd
 \vspace{-12pt}

    

\vspace{-15pt}





\end{document}
"""


GENERIC_LATEX_CV_TEMPLATE = r"""
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
\fancyhf{} % clear all header and footer fields
\fancyfoot{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}

% Adjust margins
\addtolength{\oddsidemargin}{-0.15in}
 \addtolength{\textwidth}{0.3in}

\urlstyle{same}

\raggedbottom
\raggedright
\setlength{\tabcolsep}{0in}

% Sections formatting
\titleformat{\section}{
  \vspace{-4pt}\scshape\raggedright\large\bfseries
}{}{0em}{}[\color{black}\titlerule \vspace{-5pt}]

% Ensure that generate pdf is machine readable/ATS parsable
\pdfgentounicode=1

%-------------------------
% Custom commands
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
    {\Large \scshape Sarah Martinez} \\[2mm]
    \footnotesize \raisebox{-0.1\height}
    \faPhone\ \underline{07715278067} ~ 
    {\faEnvelope\  \underline{sarah.martinez@email.com}} ~ 
    {\faLinkedin\ \underline{\href{https://www.linkedin.com/in/sarahmartinez}{linkedin.com/in/sarahmartinez}}  ~
    \vspace{-8pt}
\end{center}


%-----------PROFESSIONAL SUMMARY-----------
\section{Professional Summary}
\small{
Dynamic and results-oriented professional with 5+ years of experience in project management and business operations. Proven track record of leading cross-functional teams, optimizing processes, and delivering projects on time and within budget. Strong analytical skills combined with excellent communication abilities and a commitment to driving organizational success through strategic planning and effective stakeholder management.
}
\vspace{-4pt}

%-----------Experience---------------
\section{Work Experience}
    \resumeSubHeadingListStart
                \resumeSubheading{Horizon Global Solutions}{Jan 2022 -- Present}{Senior Project Manager}{} 
                \resumeItemListStart
                    \resumeItem{Led \textbf{15+ cross-functional projects} with budgets up to \textbf{\$2M}, consistently delivering on time and achieving a \textbf{95\% client satisfaction rate}}
                    \resumeItem{Implemented new project management methodologies that improved team efficiency by \textbf{40\%} and reduced project delivery time by \textbf{25\%}}
                    \resumeItem{Managed a team of \textbf{12 professionals}, providing mentorship and conducting performance reviews that resulted in \textbf{3 team promotions} within one year}
                    \resumeItem{Coordinated with C-suite executives and external stakeholders to align project objectives with business strategy, contributing to \textbf{\$5M in annual revenue growth}}
                    \resumeItemListEnd
            \resumeSubheading{TechVenture Consulting}{Jun 2020 -- Dec 2021}{Project Coordinator}{} 
                \resumeItemListStart
                    \resumeItem{Coordinated \textbf{8 concurrent projects} across marketing, operations, and technology departments, ensuring seamless communication and timely deliverables}
                    \resumeItem{Developed comprehensive project documentation and reporting systems that improved transparency and reduced meeting time by \textbf{30\%}}
                    \resumeItem{Facilitated stakeholder meetings and presentations, effectively communicating project status, risks, and mitigation strategies to senior leadership}
                    \resumeItem{Assisted in budget planning and resource allocation, contributing to a \textbf{15\% reduction in operational costs}}
                    \resumeItemListEnd
            \resumeSubheading{Global Innovations Inc.}{May 2019 -- May 2020}{Business Analyst}{}
                \resumeItemListStart
                    \resumeItem{Analyzed business processes and identified opportunities for improvement, leading to the implementation of \textbf{5 efficiency initiatives} that saved \textbf{\$200K annually}}
                    \resumeItem{Created detailed reports and dashboards for executive leadership, providing actionable insights that informed strategic decision-making}
                    \resumeItem{Collaborated with IT and operations teams to streamline workflows, reducing process completion time by \textbf{35\%}}
                    \resumeItemListEnd
                    
    \resumeSubHeadingListEnd
    \vspace{-12pt}



  %-----------EDUCATION-----------
\section{Education} \\[1mm]
  \resumeSubHeadingListStart
    \resumeSubheading
      {University Of London}{Graduated: May 2019}
      {Bachelor of Business Administration | Concentration in Management
      }{London}
  \resumeSubHeadingListEnd
    \resumeItemListStart
        \resumeItem {\textbf{GPA: 1st Class Honours}}
        \vspace{-7pt}
        \resumeItem {Courses: Strategic Management, Operations Management, Financial Analysis, Marketing Strategy, Business Analytics, Organizational Behavior}
    \resumeItemListEnd
    \vspace{-8pt}


%-----------ADDITIONAL INFORMATION-----------
\section{Additional Information} 
    \vspace{-3pt}
    \resumeSubHeadingListStart
                   \resumeProjectHeading
            {\textbf{{Professional Development \& Certifications}}}
            
            \\[5mm]
          \resumeItemListStart
            \resumeItem{Certified Project Management Professional (PMP) -- Project Management Institute, 2021}
            \resumeItem{Agile Certified Practitioner (PMI-ACP) -- Project Management Institute, 2022}
            \resumeItem{Active volunteer with Boston Professional Women's Network, mentoring \textbf{15+ early-career professionals}}
          \resumeItemListEnd
          \resumeSubHeadingListEnd
 \vspace{-12pt}

    
  %-----------SKILLS-----------
\section{Skills}
 \begin{itemize}[leftmargin=0.15in, label={}]
    \small{\item{   
        \textbf{Hard Skills}{: Project Management, Data Analysis, Budgeting \& Forecasting, Process Improvement, Microsoft Office Suite, Salesforce, Tableau, Asana, Jira, Agile/Scrum Methodologies} \\[1mm]
        \textbf{Soft Skills}{: Leadership, Strategic Thinking, Communication, Stakeholder Management, Problem Solving, Team Building, Negotiation, Adaptability} \\[1mm]
    }}
 \end{itemize}
 \vspace{-16pt}
 \vspace{3pt}
\vspace{10pt}

\vspace{-15pt}



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

class SaveGenerationRequest(BaseModel):
    role_title: str
    company_name: Optional[str] = None
    ats_score: Optional[int] = None
    match_score: Optional[float] = None
    cv_pdf_base64: Optional[str] = None
    cover_letter_pdf_base64: Optional[str] = None
    cv_template: Optional[str] = None


@app.get("/credits")
async def get_credits(current_user=Depends(get_current_user)):
    user_data = await get_user_credits(current_user.id)

    return {
        "credits_remaining": user_data['credits_remaining'],
        "is_subscribed": user_data.get('is_subscribed', False),
        "subscription_status": user_data.get('subscription_status', 'free')
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
            model="gpt-4.1-mini",  # Fast and cost-effective
            temperature=0,  # Deterministic output
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            max_tokens=2000
        )


        json_cv = response.choices[0].message.content
        log_tokens("parse_cv", response)  # ← ADD THIS LINE

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
The Visa Technology Team is  looking for a Backend Engineer with 3+ years experience in Python and Django. 
Experience with PostgreSQL is required. Knowledge of Docker and AWS is a plus. 
You will be building and maintaining REST APIs and collaborating closely with the frontend team. 
Excellent communication and teamwork skills are required.
Output JSON:
{{
    "role_title": "Backend Engineer at Visa",
  "required_skills": ["Python", "Django", "PostgreSQL"],
  "nice_to_have": ["Docker", "AWS"],
  "experience_level": "mid",
  "responsibilities": ["Build and maintain REST APIs", "Collaborate with frontend team"],
  "soft_skills": ["communication", "teamwork"]
}}

Example 2:
Job Description:
J.P Morgan Technology team is Looking for a Junior Frontend Developer proficient in React and JavaScript. 
Knowledge of CSS frameworks is a bonus. Must be comfortable working in Agile teams.
Output JSON:
{{
    "role_title": "Junior Frontend Developer at Goldman Sachs",
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
            model="gpt-4.1-mini",  # Fast and cost-effective
            temperature=0,  # Deterministic output
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            max_tokens=2000
        )

        json_job_desc = response.choices[0].message.content
        log_tokens("extract_job", response)  # ← ADD THIS LINE

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
        log_tokens("analyse_skills", response)  # ← ADD THIS LINE

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



@app.post("/generate-tech-cv")
@limiter.limit("25/minute")
async def generate_tech_cv(request: Request, data: dict, current_user=Depends(get_current_user)):
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
    9. Follow the single-column structure and item positioning of the template cv defined in {TECH_LATEX_CV_TEMPLATE}.


    NEVER:
    1. Fabricate companies, dates, titles, technologies, or achievements
    2. Remove existing relevant coursework from Education section
    3. Remove existing technologies from skills section
    4. Use corporate jargon: "leveraged", "utilized", "synergy", "cutting-edge", "robust"
    5. Add keywords in parentheses like "(Agile)" or "(TDD practices)"
    6. Tack keywords onto bullet ends like ", demonstrating X skill"
    7. Add a keyword without at least 1 piece of related or transferable evidence in CV
    8. Include "(inferred)" or any diagnostic labels in the visible CV output
    9. Include "N/A", "Not Provided", "None", blank values like "(GPA: )" - remove the field entirely if data is missing
    10. Replicate the structural layout, columns, or item positioning of the input CV. 


    # OUTPUT FORMAT
    {TECH_LATEX_CV_TEMPLATE}

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
        log_tokens("generate_tech_cv", response)  # ← ADD THIS LINE

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


@app.post("/generate-medical-cv")
@limiter.limit("25/minute")
async def generate_medical_cv(request: Request, data: dict, current_user=Depends(get_current_user)):
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
    # SYSTEM MESSAGE: Identity + Instructions + Rules
    system_message = f"""You are an expert CV tailoring specialist for medical sciences roles.

    # YOUR IDENTITY
    Transform existing CVs to maximize relevance for specific jobs while maintaining 
    complete authenticity and professional presentation.

    # YOUR PROCESS (Structured Chain-of-Thought)

    STEP 1 - JOB KEYWORD EXTRACTION:
    Extract and categorize from job description:
    - Must-Have Keywords: Scientific skills/techniques mentioned 3+ times or in requirements section
      (e.g., "PCR", "ELISA", "Data analysis", "In vitro experiments", "Clinical research")
    - Important Keywords: Mentioned 2 times or in "nice to have"
    - Role Context: Level (intern/junior/research assistant), lab environment, responsibilities
    - Soft Skills: Communication, leadership, collaboration, analytical abilities

    STEP 2 - CV EVIDENCE ANALYSIS:
    For each Must-Have keyword, identify:
    - EXPLICIT: Keyword appears verbatim (e.g., "PCR" in experience or skills)
    - IMPLICIT-STRONG: 2+ bullets show clear evidence
      Example: "Conducted diagnostic tests" + "analysed laboratory results" = Clinical diagnostics
    - IMPLICIT with WEAK evidence: 1 bullet or indirect connection
    - RELATED/TRANSFERABLE: Adjacent technique, relevant coursework, or methodological foundation
      Example: Job needs "ELISA" → CV has "Immunology laboratory experiments"
    - ABSENT: No evidence or logical connection at all


    STEP 3 - EVIDENCE-BASED INTEGRATION RULES:
    - EXPLICIT keywords → Emphasize and expand naturally in relevant bullets
    - IMPLICIT with STRONG evidence → Add keyword using job's terminology
    - IMPLICIT with WEAK evidence → Reframe using bridging language
    - RELATED/TRANSFERABLE → Emphasize the connection in context using bridging language
    - ABSENT keywords → DO NOT add

    STEP 4 - CONTENT PRESERVATION:
    BEFORE making any changes, identify:
    - Existing relevant coursework (Immunology, Microbiology, Epidemiology, etc.)
    - Laboratory techniques/tools already listed (PCR, ELISA, R, SAS, etc.)
    - Concrete experimental results, analyses, and reports
    Rule: NEVER remove these. If they match job keywords, emphasize them more and move to top bullets.

    STEP 5 - NATURAL REWRITING:
    Rewrite each bullet so that keywords are naturally integrated into the action (not added as afterthoughts).

    ✅ GOOD INTEGRATION (keyword is the subject/action):
    "Analysed data" → "Analysed experimental and clinical data using statistical methods to support research findings"
    "Conducted experiments" → "Conducted in vitro experiments to evaluate the efficacy of cell-based therapies"
    "Wrote reports" → "Authored structured scientific reports detailing experimental design, results, and conclusions"

    ❌ BAD INTEGRATION (keyword tacked on):
    "Analysed data, demonstrating data analysis skills"
    "Conducted experiments, showing laboratory experience"
    "Wrote reports, gaining experience in scientific writing"

    STEP 6 - SKILLS SECTION ORGANIZATION:
    Format as clean, professional categories:
    Laboratory Techniques: [All mentioned in original cv, put job-required first]
    Data Analysis & Tools: [All mentioned in original cv]
    Scientific Competencies: [Include if strong evidence exists]
      Example: "PCR, ELISA, In vitro experimentation, Data analysis, Scientific writing"

    NEVER include:
    - "(inferred)" labels in visible output
    - Soft skills like "collaboration" or "communication" (these go in experience bullets)
    - Techniques or methods with no evidence

    # CRITICAL RULES


     ALWAYS:
    1. Preserve all existing relevant coursework in Education section
    2. Preserve all existing techniques/tools in Skills section
    3. Use evidence-based integration: 2+ points for direct addition, 1+ for bridging language
    4. Integrate keywords naturally INTO the action/achievement, not as metadata
    5. Use strong action verbs: "analysed", "conducted", "designed", "evaluated", "authored"
    6. EMPHASIZE and EXPAND skills and achievements, especially those relevant to job.
    7. Output ONLY raw LaTeX code (no markdown, no wrapped code blocks)
    8. Remove any placeholders with missing data rather than using "N/A", "Not Provided", "None"
    9. Follow the single-column structure and item positioning of the template cv defined in {MEDICAL_LATEX_CV_TEMPLATE}.


    NEVER:
    1. Fabricate institutions, experiments, results, techniques, or achievements
    2. Remove existing relevant coursework from Education section
    3. Remove existing techniques/tools from skills section
    4. Use corporate jargon: "leveraged", "utilized", "synergy", "cutting-edge", "robust"
    5. Add keywords in parentheses like "(PCR)" or "(ELISA)"
    6. Tack keywords onto bullet ends like ", demonstrating X skill"
    7. Add a keyword without at least 1 piece of related or transferable evidence in CV
    8. Include "(inferred)" or any diagnostic labels in the visible CV output
    9. Include "N/A", "Not Provided", "None" or blank values like "(Grade: )" - remove the field entirely if data is missing
    10. Replicate the structural layout, columns, or item positioning of the input CV.


    # OUTPUT FORMAT
    {MEDICAL_LATEX_CV_TEMPLATE}

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
    CV shows: "Conducted diagnostic laboratory tests and analysed clinical samples, 
    recording results and supporting ongoing studies"
    Job requires: "Clinical diagnostics"
    Evidence: "diagnostic tests" + "analysed clinical samples" = 2 pieces
    ✅ Integration: "Conducted clinical diagnostic testing and analysed patient samples 
    to support accurate interpretation of laboratory results"

    Example 2 - Weak Evidence (1 piece, use bridging):
    CV shows: "Completed laboratory coursework involving immunology experiments"
    Job requires: "ELISA"
    Evidence: Immunology lab exposure suggests assay familiarity (weak evidence)
    ✅ Bridge: "Applied immunology laboratory techniques with foundational exposure 
    relevant to ELISA-based assays"
    ❌ Don't claim: "Performed ELISA independently" or list "ELISA" without evidence

    Example 3 - Related/Transferable (use bridging):
    CV shows: "Analysed experimental data using R"
    Job requires: "SAS"
    Evidence: R and SAS are transferable statistical tools
    ✅ Bridge: "Analysed experimental datasets using R (directly applicable to SAS-based statistical analysis)"

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
        log_tokens("generate_tech_cv", response)  # ← ADD THIS LINE

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


@app.post("/generate-law-cv")
@limiter.limit("25/minute")
async def generate_law_cv(request: Request, data: dict, current_user=Depends(get_current_user)):
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
    system_message = f"""You are an expert CV tailoring specialist for law roles.

    # YOUR IDENTITY
    Transform existing CVs to maximize relevance for specific jobs while maintaining 
    complete authenticity and professional presentation.

    # YOUR PROCESS (Structured Chain-of-Thought)

    STEP 1 - JOB KEYWORD EXTRACTION:
    Extract and categorize from job description:
    - Must-Have Keywords: Legal skills/practice areas mentioned 3+ times or in requirements section
      (e.g., "Legal research", "Contract drafting", "Due diligence", "Case analysis")
    - Important Keywords: Mentioned 2 times or in "nice to have"
    - Role Context: Level (vacation scheme/paralegal/trainee solicitor), team culture, responsibilities
    - Soft Skills: Communication, leadership, collaboration, analytical abilities

    STEP 2 - CV EVIDENCE ANALYSIS:
    For each Must-Have keyword, identify:
    - EXPLICIT: Keyword appears verbatim (e.g., "Legal research" in skills list)
    - IMPLICIT-STRONG: 2+ bullets show clear evidence
      Example: "Reviewed case law" + "Prepared legal memoranda" = Legal research
    - IMPLICIT with WEAK evidence: 1 bullet or indirect connection
    - RELATED/TRANSFERABLE: Adjacent skill, relevant coursework, or foundational knowledge
      Example: Job needs "Contract drafting" → CV has "Reviewed leases and agreements"
    - ABSENT: No evidence or logical connection at all


    STEP 3 - EVIDENCE-BASED INTEGRATION RULES:
    - EXPLICIT keywords → Emphasize and expand naturally in relevant bullets
    - IMPLICIT with STRONG evidence → Add keyword using job's terminology
    - IMPLICIT with WEAK evidence → Reframe using bridging language
    - RELATED/TRANSFERABLE → Emphasize the connection in context using bridging language
    - ABSENT keywords → DO NOT add

    STEP 4 - CONTENT PRESERVATION:
    BEFORE making any changes, identify:
    - Existing relevant coursework (Contract Law, Property Law, Administrative Law, etc.)
    - Tools/skills already listed (Legal research, drafting, MS Word, etc.)
    - Concrete metrics and achievements
    Rule: NEVER remove these. If they match job keywords, emphasize them more and move to top bullets.

    STEP 5 - NATURAL REWRITING:
    Rewrite each bullet so that keywords are naturally integrated into the action (not added as afterthoughts).

    ✅ GOOD INTEGRATION (keyword is the subject/action):
    "Reviewed case materials" → "Conducted detailed legal research and case analysis to support solicitors"
    "Drafted notes" → "Prepared structured legal memoranda and case summaries"
    "Client meetings" → "Attended client meetings and produced accurate attendance notes"

    ❌ BAD INTEGRATION (keyword tacked on):
    "Reviewed case materials, demonstrating legal research skills"
    "Drafted notes, showing attention to detail"
    "Client meetings, gaining experience in legal practice"

    STEP 6 - SKILLS SECTION ORGANIZATION:
    Format as clean, professional categories:
    Legal Skills: [All mentioned in original cv, put job-required first]
    Practice Areas: [All mentioned in original cv]
    Professional Tools: [Include if strong evidence exists]
      Example: "Legal research, Contract drafting, Case analysis, Due diligence"

    NEVER include:
    - "(inferred)" labels in visible output
    - Soft skills like "collaboration" or "communication" (these go in experience bullets)
    - Legal skills with no evidence

    # CRITICAL RULES

    ALWAYS:
    1. Preserve all existing relevant coursework in Education section
    2. Preserve all existing skills/tools in Skills section
    3. Use evidence-based integration: 2+ points for direct addition, 1+ for bridging language
    4. Integrate keywords naturally INTO the action/achievement, not as metadata
    5. Use strong action verbs: "drafted", "reviewed", "analysed", "researched", "prepared"
    6. EMPHASIZE and EXPAND skills and achievements, especially those relevant to job.
    7. Output ONLY raw LaTeX code (no markdown, no wrapped code blocks)
    8. Remove any placeholders with missing data rather than using "N/A", "Not Provided", "None"
    9. Follow the single-column structure and item positioning of the template cv defined in {LAW_LATEX_CV_TEMPLATE}.


    NEVER:
    1. Fabricate companies, dates, titles, skills, or achievements
    2. Remove existing relevant coursework from Education section
    3. Remove existing skills from skills section
    4. Use corporate jargon: "leveraged", "utilized", "synergy", "cutting-edge", "robust"
    5. Add keywords in parentheses like "(Legal research)" or "(Due diligence)"
    6. Tack keywords onto bullet ends like ", demonstrating X skill"
    7. Add a keyword without at least 1 piece of related or transferable evidence in CV
    8. Include "(inferred)" or any diagnostic labels in the visible CV output
    9. Include "N/A", "Not Provided", "None" or blank values like "(GPA: )" - remove the field entirely if data is missing
    10. Replicate the structural layout, columns, or item positioning of the input CV.


    # OUTPUT FORMAT
    {LAW_LATEX_CV_TEMPLATE}

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
    CV shows: "Attended client meetings and prepared detailed case notes, 
    summarising findings and next steps for solicitors"
    Job requires: "Legal research"
    Evidence: "case notes" + "summarising findings" = 2 pieces
    ✅ Integration: "Conducted legal research and prepared structured case summaries 
    to support solicitors with ongoing matters"

    Example 2 - Weak Evidence (1 piece, use bridging):
    CV shows: "Reviewed contracts for accuracy and consistency"
    Job requires: "Contract drafting"
    Evidence: "reviewed contracts" suggests drafting exposure (weak evidence)
    ✅ Bridge: "Reviewed and supported contract drafting processes, ensuring accuracy 
    and consistency in legal documentation"
    ❌ Don't claim: "Drafted contracts independently" or list "Contract drafting" without evidence

    Example 3 - Related/Transferable (use bridging):
    CV shows: "Completed coursework in Contract Law"
    Job requires: "Commercial contracts"
    Evidence: Academic foundation is transferable
    ✅ Bridge: "Applied Contract Law principles from academic coursework to support 
    commercial contract analysis"

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


@app.post("/generate-finance-cv")
@limiter.limit("25/minute")
async def generate_finance_cv(request: Request, data: dict, current_user=Depends(get_current_user)):
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
    system_message = f"""You are an expert CV tailoring specialist for corporate/finance roles.

        # YOUR IDENTITY
        Transform existing CVs to maximize relevance for specific jobs while maintaining 
        complete authenticity and professional presentation.

        # YOUR PROCESS (Structured Chain-of-Thought)

        STEP 1 - JOB KEYWORD EXTRACTION:
        Extract and categorize from job description:
        - Must-Have Keywords: Skills/Words mentioned 3+ times or in requirements section
          (e.g., "Financial Modeling", "DCF", "Excel VBA", "M&A", "Valuation")
        - Important Keywords: Mentioned 2 times or in "nice to have"
        - Role Context: Level (intern/analyst/associate), team culture, responsibilities
        - Soft Skills: Communication, leadership, collaboration, analytical abilities

        STEP 2 - CV EVIDENCE ANALYSIS:
        For each Must-Have keyword, identify:
        - EXPLICIT: Keyword appears verbatim (e.g., "Financial Modeling" in experience)
        - IMPLICIT-STRONG: 2+ bullets show clear evidence
          Example: "Built DCF model" + "performed sensitivity analysis" = Valuation expertise
        - IMPLICIT with WEAK evidence: 1 bullet or indirect connection
        - RELATED/TRANSFERABLE: Adjacent skill, relevant experiences, or foundational knowledge
          Example: Job needs "LBO modeling" → CV has "DCF valuation experience"
        - ABSENT: No evidence or logical connection at all


        STEP 3 - EVIDENCE-BASED INTEGRATION RULES:
        - EXPLICIT keywords → Emphasize and expand naturally in relevant bullets
        - IMPLICIT with STRONG evidence → Add keyword using job's terminology
        - IMPLICIT with WEAK evidence → Reframe using bridging language
        - RELATED/TRANSFERABLE → Emphasize the connection in context using bridging language
        - ABSENT keywords → DO NOT add

        STEP 4 - CONTENT PRESERVATION:
        BEFORE making any changes, identify:
        - Existing relevant experiences
        - Skills already listed 
        - Concrete metrics and achievements
        Rule: NEVER remove these. If they match job keywords, emphasize them more and move to top bullets.

        STEP 5 - NATURAL REWRITING:
        Rewrite each bullet so that keywords are naturally integrated into the action (not added as afterthoughts).

        ✅ GOOD INTEGRATION (keyword is the subject/action):
        "Built financial model" → "Developed comprehensive DCF valuation models across three sectors"
        "Weekly reports to management" → "Prepared weekly P&L reports with variance analysis for senior leadership"
        "Used Excel" → "Automated financial reporting workflows using Excel VBA macros"

        ❌ BAD INTEGRATION (keyword tacked on):
        "Built financial model, demonstrating DCF knowledge"
        "Weekly reports, showing P&L experience"
        "Used Excel, gaining experience with automation"

        STEP 6 - SKILLS SECTION ORGANIZATION:
        Format as clean, professional categories:
        Technical: [All Skills/Tools mentioned in original cv, put job-required first]
        Languages: [If applicable]
        Certifications: [CFA, Series licenses, etc. if applicable]
          Example: "Excel (VBA, PivotTables, VLOOKUP), Bloomberg Terminal, FactSet, SQL, Python (pandas, NumPy)"

        NEVER include:
        - "(inferred)" labels in visible output
        - Soft skills like "collaboration" or "communication" (these go in experience bullets)
        - Tools/software with no evidence

        # CRITICAL RULES


         ALWAYS:
        1. Preserve all existing relevant coursework in Education section
        2. Preserve all existing tools/software in Skills section
        3. Use evidence-based integration: 2+ points for direct addition, 1+ for bridging language
        4. Integrate keywords naturally INTO the action/achievement, not as metadata
        5. Use strong action verbs: "built", "developed", "analyzed", "executed", "structured"
        6. EMPHASIZE and EXPAND skills and achievements, especially those relevant to job.
        7. Output ONLY raw LaTeX code (no markdown, no wrapped code blocks)
        8. Remove any placeholders with missing data rather than using "N/A", "Not Provided", "None"
        9. Follow the single-column structure and item positioning of the template cv defined in {CORPORATE_LATEX_CV_TEMPLATE}.


        NEVER:
        1. Fabricate companies, dates, titles, transactions, or achievements
        2. Remove existing skills/experiences
        3. Use corporate jargon: "leveraged", "utilized", "synergy", "cutting-edge", "robust"
        4. Add keywords in parentheses like "(M&A)" or "(LBO modeling)"
        5. Tack keywords onto bullet ends like ", demonstrating X skill"
        6. Add a keyword without at least 1 piece of related or transferable evidence in CV
        7. Include "(inferred)" or any diagnostic labels in the visible CV output
        8. Include "N/A", "Not Provided", "None" or blank values like "(GPA: )" - remove the field entirely if data is missing
        9. Replicate the structural layout, columns, or item positioning of the input CV. 


        # OUTPUT FORMAT
        {CORPORATE_LATEX_CV_TEMPLATE}

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
        CV shows: "Prepared weekly financial reports for senior management" + "Analyzed variance 
        between actual and forecasted results"
        Job requires: "P&L analysis"
        Evidence: "financial reports" + "variance analysis" = 2 pieces
        ✅ Integration: "Prepared weekly P&L reports with variance analysis, identifying cost 
        drivers and presenting actionable insights to senior management"

        Example 2 - Weak Evidence (1 piece, use bridging):
        CV shows: "Built financial models to support investment recommendations"
        Job requires: "LBO modeling"
        Evidence: "financial models" suggests modeling capability (weak evidence for LBOs specifically)
        ✅ Bridge: "Developed detailed financial models for investment analysis 
        (foundation for leveraged buyout scenarios)"
        ❌ Don't claim: "Built LBO models" or list "LBO modeling" in skills section

        Example 3 - Related/Transferable (use bridging):
        CV shows: "Performed DCF valuations using three-statement modeling"
        Job requires: "Comparable company analysis"
        Evidence: DCF valuation is transferable to comps (same valuation category)
        ✅ Bridge: "Executed DCF valuations with integrated three-statement models 
        (directly applicable to comparable company analysis frameworks)"

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


@app.post("/generate-generic-cv")
@limiter.limit("25/minute")
async def generate_generic_cv(request: Request, data: dict, current_user=Depends(get_current_user)):
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
    system_message = f"""You are an expert CV tailoring specialist for professional/business roles.

        # YOUR IDENTITY
        Transform existing CVs to maximize relevance for specific jobs while maintaining 
        complete authenticity and professional presentation.

        # YOUR PROCESS (Structured Chain-of-Thought)

        STEP 1 - JOB KEYWORD EXTRACTION:
        Extract and categorize from job description:
        - Must-Have Keywords: Skills/competencies mentioned 3+ times or in requirements section
          (e.g., "Project Management", "Stakeholder Management", "Process Improvement", "Budget Management", "Cross-functional Leadership")
        - Important Keywords: Mentioned 2 times or in "nice to have"
        - Role Context: Level (coordinator/manager/director), team culture, responsibilities
        - Soft Skills: Communication, leadership, collaboration, analytical abilities
        - Tools/Certifications: PMP, Agile, Six Sigma, Salesforce, specific software

        STEP 2 - CV EVIDENCE ANALYSIS:
        For each Must-Have keyword, identify:
        - EXPLICIT: Keyword appears verbatim (e.g., "Project Management" in experience)
        - IMPLICIT-STRONG: 2+ bullets show clear evidence
          Example: "Coordinated 8 projects across departments" + "facilitated stakeholder meetings" = Cross-functional leadership
        - IMPLICIT with WEAK evidence: 1 bullet or indirect connection
        - RELATED/TRANSFERABLE: Adjacent skill, relevant experience, or foundational knowledge
          Example: Job needs "Change Management" → CV has "Led process improvement initiatives"
        - ABSENT: No evidence or logical connection at all


        STEP 3 - EVIDENCE-BASED INTEGRATION RULES:
        - EXPLICIT keywords → Emphasize and expand naturally in relevant bullets
        - IMPLICIT with STRONG evidence → Add keyword using job's terminology
        - IMPLICIT with WEAK evidence → Reframe using bridging language
        - RELATED/TRANSFERABLE → Emphasize the connection in context using bridging language
        - ABSENT keywords → DO NOT add

        STEP 4 - CONTENT PRESERVATION:
        BEFORE making any changes, identify:
        - Existing certifications (PMP, PMI-ACP, Six Sigma, etc.)
        - Existing relevant coursework or training
        - Tools/software already listed (Salesforce, Jira, Asana, Tableau, etc.)
        - Concrete metrics and achievements (budget sizes, team sizes, efficiency gains, cost savings)
        Rule: NEVER remove these. If they match job keywords, emphasize them more and move to top bullets.

        STEP 5 - NATURAL REWRITING:
        Rewrite each bullet so that keywords are naturally integrated into the action (not added as afterthoughts).

        ✅ GOOD INTEGRATION (keyword is the subject/action):
        "Managed team projects" → "Led 15+ cross-functional projects with budgets up to $2M, consistently delivering on time"
        "Weekly meetings with leadership" → "Conducted weekly stakeholder presentations to C-suite executives, aligning project objectives with business strategy"
        "Improved team processes" → "Implemented new project management methodologies that improved efficiency by 40%"

        ❌ BAD INTEGRATION (keyword tacked on):
        "Managed projects, demonstrating project management skills"
        "Weekly meetings, showing stakeholder management"
        "Improved processes, gaining experience with process improvement"

        STEP 6 - SKILLS SECTION ORGANIZATION:
        Format as clean, professional categories:
        Hard Skills: [Key competencies and tools - project management software, CRM systems, analytics tools]
        Certifications: [Professional certifications like PMP, Agile, Six Sigma]
        Technical: [Software proficiency if relevant]
          Example: "Project Management, Data Analysis, Budgeting & Forecasting, Process Improvement, Microsoft Office Suite, Salesforce, Tableau, Asana, Jira, Agile/Scrum Methodologies"

        For generic/professional CVs, soft skills can be included in a separate line if they are core job requirements:
          Soft Skills: [Leadership, Strategic Thinking, Communication, Stakeholder Management]

        NEVER include:
        - "(inferred)" labels in visible output
        - Tools/methodologies with no evidence
        - Generic buzzwords without supporting experience

        # CRITICAL RULES


         ALWAYS:
        1. Preserve all existing certifications and training
        2. Preserve all existing tools/software in Skills section
        3. Use evidence-based integration: 2+ points for direct addition, 1+ for bridging language
        4. Integrate keywords naturally INTO the action/achievement, not as metadata
        5. Use strong action verbs: "led", "managed", "coordinated", "implemented", "optimized", "facilitated"
        6. EMPHASIZE and EXPAND skills and achievements, especially those relevant to job
        7. Output ONLY raw LaTeX code (no markdown, no wrapped code blocks)
        8. Remove any placeholders with missing data rather than using "N/A", "Not Provided", "None"
        9. Follow the single-column structure and item positioning of the template cv defined in {GENERIC_LATEX_CV_TEMPLATE}


        NEVER:
        1. Fabricate companies, dates, titles, certifications, or achievements
        2. Remove existing certifications or professional development
        3. Remove existing tools/software from skills section
        4. Use corporate jargon: "leveraged", "utilized", "synergy", "cutting-edge", "robust"
        5. Add keywords in parentheses like "(PMP)" or "(Stakeholder Management)"
        6. Tack keywords onto bullet ends like ", demonstrating X skill"
        7. Add a keyword without at least 1 piece of related or transferable evidence in CV
        8. Include "(inferred)" or any diagnostic labels in the visible CV output
        9. Include "N/A", "Not Provided", "None" or blank values like "(GPA: )" - remove the field entirely if data is missing
        10. Replicate the structural layout, columns, or item positioning of the input CV


        # OUTPUT FORMAT
        {GENERIC_LATEX_CV_TEMPLATE}

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
        CV shows: "Coordinated 8 concurrent projects across marketing, operations, and technology departments" + "Facilitated stakeholder meetings and presentations to senior leadership"
        Job requires: "Cross-functional leadership"
        Evidence: "coordinated projects across departments" + "facilitated stakeholder meetings" = 2 pieces
        ✅ Integration: "Led cross-functional teams across 8 concurrent projects spanning marketing, operations, and technology, facilitating stakeholder alignment and executive presentations"

        Example 2 - Weak Evidence (1 piece, use bridging):
        CV shows: "Analyzed business processes and identified opportunities for improvement"
        Job requires: "Change Management"
        Evidence: "identified opportunities for improvement" suggests change capability (weak evidence)
        ✅ Bridge: "Analyzed business processes and championed improvement initiatives 
        (foundation for organizational change management)"
        ❌ Don't claim: "Led change management initiatives" or list "Change Management" in skills section

        Example 3 - Related/Transferable (use bridging):
        CV shows: "Managed a team of 12 professionals, providing mentorship and conducting performance reviews"
        Job requires: "Talent Development"
        Evidence: "mentorship" + "performance reviews" is transferable to talent development
        ✅ Bridge: "Managed and mentored a team of 12 professionals through performance reviews and career development 
        (directly applicable to talent development programs)"

        Example 4 - Professional Summary (if present in template):
        If the template includes a Professional Summary section, tailor it to emphasize:
        - Years of experience in the relevant domain
        - Top 2-3 competencies that match the job description
        - Key achievement metrics that align with role requirements
        Keep it concise (2-4 sentences) and results-focused.

        Example 5 - Certifications & Additional Information:
        If CV contains professional development, certifications, or volunteer work:
        - Prioritize certifications that match job requirements
        - Include relevant professional affiliations
        - Highlight volunteer leadership roles that demonstrate transferable skills
        These sections add credibility and demonstrate ongoing professional growth.

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
You craft authentic, evidence-based cover letters that sound like they were written by a real human, sounding professional, natural, confident, and specific. Your writing never feels generic, repetitive, or AI-generated.
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

- Tone: professional but conversational — write like a confident human writing directly to another human.
- Do not end paragraphs on vague motivation; end on a concrete action, result, or learning.
- Prefer plain, natural sentence structures over formal or inflated phrasing.
- Avoid buzzwords, clichés, or filler ("innovative", "cutting-edge", "fast-paced").
- Prefer direct, active verbs: built, led, delivered, improved.
- Show enthusiasm through specific achievements or outcomes, not adjectives.
- Do not use corporate filler words like leverage, utilize, facilitate, cutting-edge, etc.
- Avoid passive or apologetic phrasing.
- NEVER use: '—', ASCII characters only.
- Do NOT jump between unrelated points or mix multiple projects/experiences without a clear connection.




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
        log_tokens("generate_cover_letter", response)  # ← ADD THIS LINE

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

    # Check credits (but don't deduct - CV endpoint already deducted)
    profile = await get_user_credits(current_user.id)
    if profile.get('credits_remaining', 0) < 0:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "no_credits",
                "message": "You've used all your credits. Purchase more tokens or subscribe to continue.",
                "credits_remaining": 0
            }
        )

    # ✅ Initialize job_info with default value FIRST
    job_info = {"role_title": ""}

    try:
        # STEP 1: Parse CV → JSON
        parsed_cv = await parse_cv(user_cv)

        # STEP 2: Extract Job Description → JSON
        parsed_job = await extract_job(job_description)

        # ✅ Parse job_info - clean up markdown if present
        try:
            # Remove markdown code blocks if present
            clean_job = parsed_job.strip()
            if clean_job.startswith("```"):
                clean_job = re.sub(r'^```[a-zA-Z]*\n?', '', clean_job)
                clean_job = re.sub(r'\n?```$', '', clean_job)
            job_info = json.loads(clean_job)
            print(f"✅ Parsed job_info: {job_info.get('role_title', 'N/A')}")
        except Exception as parse_error:
            print(f"⚠️ Failed to parse job_info: {parse_error}")
            job_info = {"role_title": ""}

        # STEP 3: Analyze Skills
        skills_analysis = await analyse_skills(
            json_job_desc=parsed_job,
            json_cv=parsed_cv
        )

        # STEP 4: Generate tailored cover letter
        tailored_cover = await generate_tailored_cover_letter(
            user_cv=user_cv,
            job_desc=job_description,
            skills_analysis=skills_analysis
        )

        return {
            "cover_letter": tailored_cover["cover_letter"],
            "skills_report": skills_analysis,
            "job_info": job_info
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
        # Clean Unicode characters
        replacements = {
            '\u2014': '-', '\u2013': '-',
            '\u2018': "'", '\u2019': "'",
            '\u201c': '"', '\u201d': '"',
            '\u2026': '...', '\u00a0': ' ', '\u2022': '-'
        }
        for old, new in replacements.items():
            cover_letter_text = cover_letter_text.replace(old, new)

        cover_letter_text = cover_letter_text.encode('latin-1', errors='ignore').decode('latin-1')

        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        lines = cover_letter_text.split('\n')

        # Find where body starts
        body_start_index = 0
        for i, line in enumerate(lines):
            if line.strip().lower().startswith("dear"):
                body_start_index = i
                break

        # Header lines (before "Dear")
        header_lines = [l.strip() for l in lines[:body_start_index] if l.strip()]

        if header_lines:
            # Name = left, bold
            pdf.set_font("Times", size=14)
            pdf.cell(0, 6, header_lines[0], ln=True, align='R')

            # Phone, Email, Date = right aligned
            pdf.set_font("Times", size=14)
            for line in header_lines[1:]:
                pdf.cell(0, 6, line, ln=True, align='R')

        pdf.ln(8)

        # Body
        pdf.set_font("Times", size=14)
        for line in lines[body_start_index:]:
            if line.strip():
                pdf.multi_cell(0, 6, line.strip())
            else:
                pdf.ln(4)

        pdf_output = pdf.output(dest='S').encode('latin-1')
        pdf_base64 = base64.b64encode(pdf_output).decode('utf-8')

        return {"success": True, "pdf": pdf_base64}

    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/save-generation")
async def save_generation_endpoint(
        request: Request,
        data: SaveGenerationRequest,
        current_user=Depends(get_current_user)
):
    """
    Save a CV/Cover Letter generation to the database.
    Called after successful generation on the frontend.
    """

    print(f"=== SAVE GENERATION for user: {current_user.id} ===")

    try:
        result = await save_generation(
            user_id=current_user.id,
            role_title=data.role_title,
            company_name=data.company_name,
            ats_score=data.ats_score,
            match_score=data.match_score,
            cv_pdf_base64=data.cv_pdf_base64,
            cover_letter_pdf_base64=data.cover_letter_pdf_base64,
            cv_template=data.cv_template
        )

        return {
            "success": True,
            "generation_id": result.get("id"),
            "message": "Generation saved successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error saving generation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/generations")
async def get_generations_endpoint(
        request: Request,
        limit: int = 20,
        current_user=Depends(get_current_user)
):
    """
    Get all generations for the current user (non-expired only).
    """

    print(f"=== GET GENERATIONS for user: {current_user.id} ===")

    try:
        generations = await get_user_generations(
            user_id=current_user.id,
            limit=limit
        )

        stats = await get_generation_stats(current_user.id)

        return {
            "success": True,
            "generations": generations,
            "stats": stats
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching generations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/generations/{generation_id}")
async def get_generation_endpoint(
        request: Request,
        generation_id: str,
        current_user=Depends(get_current_user)
):
    """
    Get a specific generation with signed URLs for downloading PDFs.
    """

    print(f"=== GET GENERATION {generation_id} for user: {current_user.id} ===")

    try:
        generation = await get_generation_by_id(
            user_id=current_user.id,
            generation_id=generation_id
        )

        return {
            "success": True,
            "generation": generation
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching generation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/generations/{generation_id}")
async def delete_generation_endpoint(
        request: Request,
        generation_id: str,
        current_user=Depends(get_current_user)
):
    """
    Delete a specific generation and its associated files.
    """

    print(f"=== DELETE GENERATION {generation_id} for user: {current_user.id} ===")

    try:
        await delete_generation(
            user_id=current_user.id,
            generation_id=generation_id
        )

        return {
            "success": True,
            "message": "Generation deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error deleting generation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
