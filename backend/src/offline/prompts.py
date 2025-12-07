"""LLM prompts for offline analysis."""

EXTRACT_SKILLS = """Read this resume. Output ONLY valid JSON (no markdown, no explanation) - a list of skill keywords that this candidate claims expertise in.

For each skill, output a dict with:
- "keyword": the skill name (e.g., "JAX", "LLM post-training", "distributed systems")
- "resume_sources": list of exact quotes from resume that demonstrate this skill (bullet points, skills section entries, etc.)

Focus on technical skills relevant to ML/AI/systems engineering. Be specific - "JAX" not "programming".

Output format: [{"keyword": "...", "resume_sources": ["...", "..."]}, ...]"""

FILTER_SKILLS = """Given these skills extracted from a resume and a job description, select the TOP {top_n} most relevant skills for this job.

Skills from resume:
{skills_json}

Job description:
{job_description}

Output ONLY valid JSON (no markdown) - the top {top_n} skills in order of relevance to the job.
Format: ["skill1", "skill2", ..., "skill{top_n}"]

Prioritize skills explicitly mentioned in job requirements."""

SEARCH_X = """Search @{handle}'s X/Twitter posts for any content related to: {skill}

For each relevant post you find, classify it:
- "yes": Post demonstrates real expertise/deep knowledge (detailed technical insights, original work, teaching others)
- "could_be": Post shows interest but unclear depth (sharing articles, asking questions, surface-level comments)
- "no": Post suggests lack of knowledge (asking basic questions, admitting unfamiliarity)

Output ONLY valid JSON (no markdown):
{{"posts": [{{"url": "tweet URL", "content": "tweet text summary", "label": "yes/could_be/no"}}]}}

If no relevant posts found, output: {{"posts": []}}"""
