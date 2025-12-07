"""Offline analysis pipeline: resume → skills → X search → flags."""
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from src.common.grok import analyze_pdf, search_x, chat_completion
from src.common.save_session import reset_session
from src.common.utils import parse_json_response
from .prompts import EXTRACT_SKILLS, FILTER_SKILLS, SEARCH_X
from .types import SkillAnalysis, XPost

log = logging.getLogger(__name__)


def extract_skills_from_resume(pdf_path: str | Path) -> list[dict]:
    """Extract skills with sources from resume PDF."""
    log.info(f"Extracting skills from resume: {pdf_path}")
    response = analyze_pdf(pdf_path, EXTRACT_SKILLS)
    if not response:
        log.warning("No response from PDF analysis, returning empty skills")
        return []
    skills = parse_json_response(response)
    log.info(f"Extracted {len(skills)} skills")
    return skills


def filter_top_skills(skills: list[dict], job_description: str, top_n: int = 10) -> list[str]:
    """Filter and rank skills by job relevance."""
    if not skills:
        return []
    log.info(f"Filtering {len(skills)} skills to top {top_n}")
    prompt = FILTER_SKILLS.format(
        skills_json=json.dumps([s["keyword"] for s in skills]),
        job_description=job_description,
        top_n=top_n,
    )
    response = chat_completion(prompt, step="filter_top_skills")
    if not response:
        log.warning("No response from filter, returning first N skills")
        return [s["keyword"] for s in skills[:top_n]]
    return parse_json_response(response)[:top_n]


def search_skill_on_x(handle: str, skill: str) -> list[XPost]:
    """Search X profile for posts about a specific skill."""
    prompt = SEARCH_X.format(handle=handle, skill=skill)
    response = search_x(handle, prompt)
    if not response:
        log.warning(f"No response from X search for '{skill}', returning empty posts")
        return []
    try:
        data = parse_json_response(response)
        return [XPost(url=p["url"], content=p["content"], label=p["label"]) for p in data.get("posts", [])]
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        log.warning(f"Failed to parse X response for '{skill}': {e}")
        return []


def compute_flag(resume_sources: list[str], x_posts: list[XPost]) -> str:
    """Compute flag based on resume claims vs X evidence."""
    if not x_posts:
        return "no_data"
    labels = [p.label for p in x_posts]
    yes, no, maybe = labels.count("yes"), labels.count("no"), labels.count("could_be")
    strong_claim = len(resume_sources) >= 2 or any(len(s) > 100 for s in resume_sources)

    if no > 0 and yes == 0:
        return "highly_suspect"
    if strong_claim and yes == 0 and maybe > 0:
        return "suspect"
    if yes > 0:
        return "verified"
    return "no_data"


def run_full_analysis(
    resume_path: str | Path,
    job_description: str,
    x_handle: str,
    top_n: int = 10,
) -> list[SkillAnalysis]:
    """Run the full offline analysis pipeline."""
    reset_session()  # Start fresh session for this analysis
    log.info("[Step 1/3] Extracting skills from resume...")
    all_skills = extract_skills_from_resume(resume_path)
    if not all_skills:
        log.error("Failed to extract skills from resume")
        return []
    skills_map = {s["keyword"]: s["resume_sources"] for s in all_skills}

    log.info("[Step 2/3] Filtering to top skills for job...")
    top_skills = filter_top_skills(all_skills, job_description, top_n)
    if not top_skills:
        log.error("Failed to filter skills")
        return []

    log.info(f"[Step 3/3] Searching X for {len(top_skills)} skills...")

    def process_skill(rank: int, skill: str) -> SkillAnalysis:
        log.info(f"  [{rank}/{len(top_skills)}] Searching: {skill}")
        resume_sources = skills_map.get(skill, [])
        x_posts = search_skill_on_x(x_handle, skill)  # Already handles errors internally
        flag = compute_flag(resume_sources, x_posts)
        log.info(f"  Done: {skill} -> {flag}")
        return SkillAnalysis(keyword=skill, priority_rank=rank, resume_sources=resume_sources, x_posts=x_posts, flag=flag)

    with ThreadPoolExecutor(max_workers=len(top_skills)) as executor:
        results = list(executor.map(process_skill, *zip(*enumerate(top_skills, 1))))

    results.sort(key=lambda x: x.priority_rank)
    log.info("Analysis complete!")
    return results
