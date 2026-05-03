"""Select experiences and generate tailored dotjots using RAG extraction results."""
import os
import sys
from typing import List, Dict
from collections import defaultdict
from schemas import ResumeStrategy, ExperienceSelection, SkillsStrategy, TitleSuggestion
from extractor import KeywordExtractionResult, get_experience_bullets, get_experience_context

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from coverletter.utils import generate_with_retry
from coverletter.provider_config import get_model_for_provider, get_fallback_models


def create_resume_strategy(
    extraction: KeywordExtractionResult,
    user_profile: dict,
    job_description: str,
    api_key: str,
    provider: str = "gemini",
    job_id: str = ""
) -> ResumeStrategy:
    """
    Create strategy from RAG extraction:
    1. Select experiences based on keyword mappings
    2. Build skills section strategy (front-load must-haves)
    3. Suggest title alignment changes
    4. Generate tailored dotjots with full context
    """
    print("[STRATEGIZER] Creating resume strategy from RAG mappings...")
    
    strategy = ResumeStrategy()
    
    # Aggregate keyword mappings by experience
    experience_keywords = aggregate_keywords_by_experience(extraction)
    
    # Build experience selections from aggregated data
    for exp_title, data in experience_keywords.items():
        selection = ExperienceSelection(
            experience_id=f"work_{exp_title}",
            title=exp_title,
            relevance_score=1.0,
            keywords_covered=list(data['keywords']),
            should_include=True
        )
        strategy.selected_experiences.append(selection)
    
    # Sort by keyword count (more keywords = more relevant)
    strategy.selected_experiences.sort(key=lambda x: len(x.keywords_covered), reverse=True)
    
    # Limit selections to fit on 2 pages
    for i, exp in enumerate(strategy.selected_experiences):
        exp.should_include = i < 3
    
    # Build skills section strategy
    strategy.skills_strategy = build_skills_strategy(extraction, user_profile)
    
    # Suggest title alignment (single LLM call)
    strategy.title_suggestions = suggest_title_alignment(
        extraction, user_profile, job_description, api_key, provider
    )
    
    # Generate dotjots for selected experiences
    generate_all_dotjots(strategy, extraction, user_profile, api_key, provider, job_id)
    
    # Report stats
    included_exp = sum(1 for e in strategy.selected_experiences if e.should_include)
    print(f"[STRATEGIZER] Selected {included_exp} experiences")
    print(f"[STRATEGIZER] Skills: {len(strategy.skills_strategy.front_load)} front-loaded, {len(strategy.skills_strategy.add)} to add")
    print(f"[STRATEGIZER] Title suggestions: {len(strategy.title_suggestions)}")
    
    return strategy


def aggregate_keywords_by_experience(
    extraction: KeywordExtractionResult
) -> Dict[str, Dict]:
    """
    Aggregate keyword mappings by experience title.
    Returns dict: {experience_title: {type, keywords}}
    """
    experience_data = defaultdict(lambda: {
        'type': 'work',
        'keywords': set()
    })
    
    # keyword_to_experience maps: keyword -> [experience_titles]
    # Need to reverse it: experience_title -> [keywords]
    for keyword, experience_titles in extraction.keyword_to_experiences.items():
        for title in experience_titles:
            if title == "skills":
                continue  # Skip skills, handle separately
            experience_data[title]['keywords'].add(keyword)
    
    return dict(experience_data)


def build_skills_strategy(
    extraction: KeywordExtractionResult,
    user_profile: dict
) -> SkillsStrategy:
    """
    Build the optimal skills section strategy. Pure logic — no LLM call.
    
    1. Front-load: must-have keywords the user already has
    2. Add: must-have + easy_no_match keywords not in user's skills
    3. Keep: existing skills that are relevant (matched to JD)
    4. Deprioritize: existing skills not mentioned in JD
    """
    raw_skills = user_profile.get("skills", [])
    user_skills = [s for s in raw_skills if isinstance(s, str)]
    user_skills_lower = {s.lower() for s in user_skills}
    
    must_have_list = [k for k in extraction.must_have if isinstance(k, str)]
    nice_to_have_list = [k for k in extraction.nice_to_have if isinstance(k, str)]
    all_jd_keywords = set(must_have_list + nice_to_have_list)
    matched_keywords = set(k for k in extraction.keyword_to_experiences.keys() if isinstance(k, str))
    
    front_load = []
    add = []
    keep = []
    deprioritize = []
    
    # Must-haves the user already has in their skills list → front-load
    # Must-haves NOT in user skills → add (regardless of whether matched to experience)
    for kw in must_have_list:
        if kw.lower() in user_skills_lower:
            front_load.append(kw)
        else:
            add.append(kw)
    
    # Easy_no_match keywords not already in add and not in user skills → add
    add_lower = {k.lower() for k in add}
    for kw in extraction.easy_no_match:
        if kw.lower() not in add_lower and kw.lower() not in user_skills_lower:
            add.append(kw)
    
    # Categorize existing user skills
    # Nice-to-haves or matched → keep (near top)
    # Everything else → keep too, but after nice-to-haves (just reorder, don't drop)
    front_load_lower = {k.lower() for k in front_load}
    nice_matched_lower = {k.lower() for k in all_jd_keywords} | {k.lower() for k in matched_keywords}
    keep_priority = []
    keep_rest = []
    for skill in user_skills:
        if skill.lower() in front_load_lower:
            continue  # Already front-loaded
        elif skill.lower() in nice_matched_lower:
            keep_priority.append(skill)
        else:
            keep_rest.append(skill)
    keep = keep_priority + keep_rest
    
    strategy = SkillsStrategy(
        front_load=front_load,
        add=add,
        keep=keep,
        deprioritize=deprioritize
    )
    
    print(f"[STRATEGIZER] Skills strategy: {len(front_load)} front-load, {len(add)} add, {len(keep)} keep, {len(deprioritize)} deprioritize")
    return strategy


def suggest_title_alignment(
    extraction: KeywordExtractionResult,
    user_profile: dict,
    job_description: str,
    api_key: str,
    provider: str
) -> List[TitleSuggestion]:
    """
    Suggest honest title tweaks that better align with the target role.
    Single LLM call. Only suggests changes that are truthful.
    """
    experiences = user_profile.get("experience", {})
    
    if not experiences:
        return []
    
    titles = list(experiences.keys())
    titles_str = "\n".join([f"- {t}" for t in titles])
    
    # Extract the target role title from the JD (first ~500 chars usually has it)
    jd_snippet = job_description[:500]
    
    prompt = f"""You are a resume consultant. A candidate is applying for a role. Their current work experience titles are listed below. Suggest HONEST title adjustments that better align with the target role.

RULES:
- Only suggest changes where the adjustment is truthful (e.g. "Junior Dev" → "Software Developer" is OK if they did software dev work)
- NEVER inflate seniority (don't turn "Intern" into "Engineer" unless they were truly an engineer)
- NEVER invent titles — the new title must still describe what the person actually did
- Only suggest if there is a clear, meaningful improvement in alignment. If the title is already good, skip it.
- Fewer suggestions is better — only flag titles that genuinely need changing
- Keep suggestions concise

Target role (from JD):
{jd_snippet}

Candidate's current work experience titles:
{titles_str}

For each title that should change, return in this exact format:
ORIGINAL: exact current title
SUGGESTED: new title
REASON: one-line explanation

If no changes are needed, return:
NO CHANGES NEEDED"""

    try:
        model = get_model_for_provider(provider)
        fallback_models = get_fallback_models(provider)
        response = generate_with_retry(model, prompt, max_retries=3, api_key=api_key, provider=provider, fallback_models=fallback_models, step_name="Title Alignment")
        
        if "no changes needed" in response.lower():
            print("[STRATEGIZER] No title changes suggested")
            return []
        
        suggestions = []
        lines = response.strip().split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.upper().startswith('ORIGINAL:'):
                original = line.split(':', 1)[1].strip()
                suggested = ""
                reason = ""
                if i + 1 < len(lines) and lines[i+1].strip().upper().startswith('SUGGESTED:'):
                    suggested = lines[i+1].split(':', 1)[1].strip()
                if i + 2 < len(lines) and lines[i+2].strip().upper().startswith('REASON:'):
                    reason = lines[i+2].split(':', 1)[1].strip()
                
                if original and suggested and original != suggested:
                    suggestions.append(TitleSuggestion(
                        original=original,
                        suggested=suggested,
                        reason=reason
                    ))
                    print(f"[STRATEGIZER] Title: '{original}' → '{suggested}' ({reason})")
                i += 3
            else:
                i += 1
        
        return suggestions
    except Exception as e:
        print(f"[WARNING] Title alignment failed: {e}")
        return []


def generate_all_dotjots(
    strategy: ResumeStrategy,
    extraction: KeywordExtractionResult,
    user_profile: dict,
    api_key: str,
    provider: str,
    job_id: str = ""
):
    """Generate tailored dotjots. Reuses existing ai_bullets if available for this job."""
    experiences = user_profile.get("experience", {})
    projects = user_profile.get("projects", {})
    
    # Collect experiences that need new dotjots
    to_generate = []
    
    all_selections = [
        (s, 'work', experiences) for s in strategy.selected_experiences if s.should_include
    ] + [
        (s, 'project', projects) for s in strategy.selected_projects if s.should_include
    ]
    
    for selection, exp_type, source in all_selections:
        entry = source.get(selection.title, {})
        
        # Check for existing ai_bullets for this job
        if isinstance(entry, dict) and job_id:
            existing_ai = entry.get("ai_bullets", {}).get(job_id, [])
            if existing_ai:
                selection.dotjots = existing_ai
                print(f"[STRATEGIZER] Reusing ai_bullets for {selection.title} (job: {job_id})")
                continue
        
        bullets = get_experience_bullets(entry)
        context = get_experience_context(entry)
        
        to_generate.append({
            'title': selection.title,
            'type': exp_type,
            'original': bullets,
            'context': context,
            'keywords': selection.keywords_covered
        })
    
    # Batch LLM call for experiences that need new dotjots
    if to_generate:
        batch_dotjots = batch_generate_dotjots(to_generate, extraction, api_key, provider)
        
        # Assign to selections and prepare ai_bullets to save back
        ai_bullets_to_save = {}  # {title: [bullets]}
        
        for item in to_generate:
            dotjots = batch_dotjots.get(item['title'], [])
            ai_bullets_to_save[item['title']] = dotjots
            
            for selection in strategy.selected_experiences + strategy.selected_projects:
                if selection.title == item['title']:
                    selection.dotjots = dotjots
                    break
        
        # Store ai_bullets on strategy so caller can save back to profile
        strategy.ai_bullets_to_save = {job_id: ai_bullets_to_save} if job_id else {}


def batch_generate_dotjots(
    experiences: List[Dict],
    extraction: KeywordExtractionResult,
    api_key: str,
    provider: str
) -> Dict[str, List[str]]:
    """Generate dotjots for all experiences in one LLM call."""
    
    # Build context for LLM
    blocks = []
    for item in experiences:
        # Separate must-have vs nice-to-have keywords for this experience
        must_kws = [k for k in item['keywords'] if k in extraction.must_have]
        nice_kws = [k for k in item['keywords'] if k in extraction.nice_to_have]
        other_kws = [k for k in item['keywords'] if k not in must_kws and k not in nice_kws]
        
        block = f"{item['type'].upper()}: {item['title']}\n"
        block += f"ORIGINAL BULLETS:\n" + "\n".join([f"- {a}" for a in item['original']]) + "\n"
        if item.get('context'):
            block += f"ADDITIONAL CONTEXT: {item['context']}\n"
        if must_kws:
            block += f"MUST-HAVE KEYWORDS (weave these in prominently): {', '.join(must_kws)}\n"
        if nice_kws or other_kws:
            block += f"NICE-TO-HAVE KEYWORDS (mention naturally if relevant): {', '.join(nice_kws + other_kws)}"
        blocks.append(block)
    
    exp_context = "\n\n".join(blocks)
    
    # Note which keywords are already in the skills section
    skills_note = ""
    if extraction.must_have:
        skills_note = f"\nNote: These keywords will also appear in the Skills section: {', '.join(extraction.must_have)}. You don't need to force them into every bullet — just use them naturally where the experience genuinely involved them."
    
    prompt = f"""You are a resume writer. Generate 3-4 bullet points for each experience below. The candidate is applying for a role that requires specific skills.

{exp_context}
{skills_note}

RULES:
1. MUST-HAVE keywords should appear naturally in bullets where the experience genuinely used them. Front-load the most important ones.
2. NICE-TO-HAVE keywords should be mentioned where truthful, but don't force them.
3. Start with strong action verbs (Built, Led, Architected, Optimized, Designed, Implemented)
4. Add plausible quantified impact (users, %, scale) grounded in ADDITIONAL CONTEXT if provided
5. Keep numbers believable for the role level and company size — don't fabricate impressive numbers
6. Keep each bullet to 1-2 lines max
7. Don't just list technologies — show what you accomplished WITH them
8. Each bullet should demonstrate a different aspect of the experience

Return in this exact format (use the EXACT title provided):
TITLE:
- bullet 1
- bullet 2
- bullet 3"""

    try:
        model = get_model_for_provider(provider)
        fallback_models = get_fallback_models(provider)
        response = generate_with_retry(model, prompt, api_key=api_key, provider=provider, fallback_models=fallback_models, step_name="Batch Generate Dotjots")
        
        results = {}
        current_title = None
        current_bullets = []
        
        for line in response.strip().split('\n'):
            line = line.strip()
            
            # Check if line is a title (all caps or ends with colon)
            if line.isupper() or (line.endswith(':') and not line.startswith('-')):
                # Save previous
                if current_title and current_bullets:
                    results[current_title] = current_bullets[:4]
                # Start new
                current_title = line.rstrip(':')
                current_bullets = []
            elif line.startswith('- ') or line.startswith('• '):
                current_bullets.append(line[2:])
            elif line and current_title:
                # Bullet without dash
                current_bullets.append(line)
        
        # Save last one
        if current_title and current_bullets:
            results[current_title] = current_bullets[:4]
        
        return results
    except Exception as e:
        print(f"[WARNING] Batch dotjots generation failed: {e}")
        return {}


def identify_skill_additions(
    strategy: ResumeStrategy,
    extraction: KeywordExtractionResult,
    user_profile: dict
):
    """Identify skills to add based on keywords not in skills list."""
    user_skills = {s.lower() for s in user_profile.get("skills", [])}
    
    # Add easy_no_match keywords as suggestions (they're easy to add to skills section)
    for keyword in extraction.easy_no_match:
        if keyword.lower() not in user_skills and len(strategy.suggested_skill_additions) < 5:
            strategy.suggested_skill_additions.append(keyword)
    
    # Keyword gaps are dropped keywords
    strategy.keyword_gaps = extraction.drop


