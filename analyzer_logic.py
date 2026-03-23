import re

def analyze_resume(resume_text, job_description=None):
    score = 0
    missing_skills = []
    improvement_tips = []

    if not resume_text or len(resume_text.strip()) == 0:
        return 0, ["No text detected"], ["Please provide your resume content or upload a valid PDF."]

    resume_lower = resume_text.lower()
    
    # Comprehensive stopword filtering so only meaningful keywords remain
    stopwords = {
        "and", "the", "for", "with", "from", "that", "this", "your", "will", "have", "are", 
        "you", "our", "their", "about", "which", "would", "could", "should", "ability", 
        "experience", "skills", "years", "work", "team", "strong", "excellent", "good", 
        "knowledge", "understanding", "working", "environment", "related", "field", "must"
    }

    # If Job Description is provided, calculate pure Match Percentage
    if job_description and len(job_description.strip()) > 0:
        jd_words = set(re.findall(r'\b[a-z]{4,}\b', job_description.lower()))
        jd_keywords = jd_words - stopwords
        
        res_words = set(re.findall(r'\b[a-z]{4,}\b', resume_lower))
        
        if len(jd_keywords) == 0:
            improvement_tips.append("The Job Description provided doesn't contain enough identifiable technical keywords.")
            score = 50
        else:
            # Find intersections matching exact keywords
            matched_keywords = jd_keywords.intersection(res_words)
            missing_keywords = jd_keywords - res_words
            
            # Match Percentage formula
            score = int((len(matched_keywords) / len(jd_keywords)) * 100)
            
            for kw in missing_keywords:
                missing_skills.append(kw.title())
                
            improvement_tips.append(f"ATS Match Logic: We found {len(matched_keywords)} matching keywords out of {len(jd_keywords)} parsed terms from your Job Description.")
            improvement_tips.append("Tip: Integrate the highlighted Missing Keywords naturally into your project or experience bullet points.")
            
    else:
        # Fallback Industry Generic scoring if no JD is provided
        essential_keywords = ["python", "machine learning", "sql", "projects", "agile", "cloud", "api", "data"]
        for kw in essential_keywords:
            if kw in resume_lower:
                score += 15
            else:
                missing_skills.append(kw.title() + " (Recommended)")

        if "project" in resume_lower or "projects" in resume_lower:
            score += 10
        else:
            improvement_tips.append("Create a dedicated 'Projects' section to showcase practical applications.")

        improvement_tips.append("For a highly accurate Match Percentage, please paste a Target Job Description so we can compare the exact keywords.")

    # General feedback modifiers
    if len(resume_lower) < 300:
        improvement_tips.append("Your overall resume is very short. Elaborate on your quantifiable achievements using STAR format.")
    elif len(resume_lower) > 4000:
        improvement_tips.append("Your resume is dense and might be too long to parse efficiently. Consider condensing your bullet points.")

    # Cap Score boundaries
    if score > 100:
        score = 100
        
    # Baseline for empty matches but existing content
    if score == 0 and len(resume_lower) > 50:
        score = 15

    # Clean missing skills
    missing_skills = list(set(missing_skills))
    missing_skills.sort()

    return score, missing_skills, improvement_tips
