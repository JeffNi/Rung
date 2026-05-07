"""Simple keyword extractor: Easy vs Hard keyword decisions."""
import os
import sys
import yaml
import re
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass, field

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from coverletter.utils import generate_with_retry
from coverletter.provider_config import get_model_for_provider, get_fallback_models


# Keywords that are EASY to fake (similar tech, can learn quickly)
# These can be added to resume even if not explicitly done
EASY_KEYWORDS = {
    'react', 'vue', 'angular', 'svelte',  # Frontend frameworks
    'javascript', 'typescript', 'html', 'css',  # Frontend basics
    'bootstrap', 'tailwind', 'material-ui',  # CSS frameworks
    'express', 'fastapi', 'flask', 'django',  # Backend frameworks  
    'postgresql', 'mysql', 'sqlite', 'mongodb',  # Databases
    'git', 'github', 'gitlab',  # Version control
    'rest', 'graphql', 'json', 'api',  # API concepts
    'docker',  # Container basics
    'aws', 'gcp', 'azure',  # Cloud (generic usage)
    'python', 'java', 'go', 'rust', 'ruby',  # Languages
}

# Keywords that are HARD to fake (need real experience)
# Only include if there's a strong related experience
HARD_KEYWORDS = {
    'kubernetes', 'k8s',  # Complex orchestration
    'terraform', 'ansible', 'chef', 'puppet',  # Infrastructure as code
    'microservices', 'distributed systems',  # Architecture
    'kafka', 'rabbitmq', 'redis cluster',  # Message queues/clustering
    'machine learning', 'deep learning', 'tensorflow', 'pytorch',  # ML
    'ci/cd', 'jenkins', 'github actions', 'gitlab ci',  # DevOps pipelines
    'prometheus', 'grafana', 'datadog', 'new relic',  # Monitoring
    'load balancing', 'cdn', 'edge computing',  # Infrastructure
    'blockchain', 'smart contracts', 'ethereum',  # Blockchain
    'security', 'penetration testing', 'owasp',  # Security
}


def is_easy_keyword(keyword: str) -> bool:
    """Check if keyword is easy to learn/fake."""
    keyword_lower = keyword.lower()
    
    # Direct match
    if keyword_lower in EASY_KEYWORDS:
        return True
    
    # Check if it contains easy patterns
    easy_patterns = ['frontend', 'backend', 'api', 'database', 'framework', 'library']
    if any(pattern in keyword_lower for pattern in easy_patterns):
        return True
    
    # Check related terms
    related = get_related_terms(keyword_lower)
    if any(term in EASY_KEYWORDS for term in related):
        return True
    
    return False


def is_hard_keyword(keyword: str) -> bool:
    """Check if keyword requires real expertise."""
    keyword_lower = keyword.lower()
    
    # Direct match
    if keyword_lower in HARD_KEYWORDS:
        return True
    
    # Check for hard patterns
    hard_patterns = [
        'architect', 'orchestrat', 'cluster', 'scaling', 
        'infrastructure', 'pipeline', 'monitoring', 'observability',
        'penetration', 'security audit', 'compliance'
    ]
    if any(pattern in keyword_lower for pattern in hard_patterns):
        return True
    
    return False


def get_experience_bullets(entry) -> List[str]:
    """Extract bullets from experience entry (handles old and new format)."""
    if isinstance(entry, list):
        return entry  # Old format: ["bullet1", "bullet2"]
    if isinstance(entry, dict):
        return entry.get("bullets", [])  # New format: {bullets, ai_bullets, context}
    return []


def get_experience_context(entry) -> str:
    """Extract context from experience entry (new format only)."""
    if isinstance(entry, dict):
        return entry.get("context", "")
    return ""


def find_related_experiences(keyword: str, user_profile: dict) -> List[str]:
    """
    Find ALL experiences that relate to this keyword.
    Fast path only: direct string matching + related terms dict.
    Returns exact profile keys (experience/project titles).
    """
    keyword_lower = keyword.lower()
    user_skills = {s.lower() for s in user_profile.get("skills", [])}
    experiences = user_profile.get("experience", {})
    projects = user_profile.get("projects", {})
    related = get_related_terms(keyword_lower)
    
    matches = []
    
    # Check skills
    if keyword_lower in user_skills:
        matches.append("skills")
    else:
        for skill in user_skills:
            if skill in related or any(r in skill for r in related):
                matches.append("skills")
                break
    
    # Check experiences (returns exact profile keys)
    for title, entry in experiences.items():
        bullets = get_experience_bullets(entry)
        context = get_experience_context(entry)
        content = (' '.join(bullets) + ' ' + context).lower()
        if keyword_lower in content or any(term in content for term in related):
            matches.append(title)
    
    # Check projects (returns exact profile keys)
    for title, entry in projects.items():
        bullets = get_experience_bullets(entry)
        context = get_experience_context(entry)
        content = (' '.join(bullets) + ' ' + context).lower()
        if keyword_lower in content or any(term in content for term in related):
            matches.append(title)
    
    return matches


def get_related_terms(keyword: str) -> Set[str]:
    """
    Get related technologies/skills using comprehensive dict (fast path).
    Hybrid: Dict lookup first, simple heuristic for unknowns, LLM only if needed.
    """
    keyword_lower = keyword.lower()
    
    # Comprehensive relationship mapping (fast path)
    relationships = {
        # Frontend
        'react': {'vue', 'angular', 'svelte', 'frontend', 'javascript', 'spa', 'nextjs', 'jsx', 'component'},
        'vue': {'react', 'angular', 'frontend', 'javascript', 'spa', 'vuejs', 'nuxt'},
        'angular': {'react', 'vue', 'frontend', 'typescript', 'spa', 'rxjs', 'component'},
        'svelte': {'react', 'vue', 'frontend', 'javascript', 'spa'},
        'nextjs': {'react', 'frontend', 'javascript', 'ssr', 'framework'},
        'frontend': {'javascript', 'typescript', 'react', 'vue', 'angular', 'html', 'css', 'ui', 'ux', 'web'},
        
        # Backend
        'python': {'django', 'flask', 'fastapi', 'backend', 'scripting', 'pandas', 'numpy', 'data'},
        'django': {'python', 'backend', 'web', 'framework', 'orm'},
        'flask': {'python', 'backend', 'web', 'microframework'},
        'fastapi': {'python', 'backend', 'web', 'api', 'async'},
        'node': {'javascript', 'typescript', 'backend', 'express', 'nestjs', 'server'},
        'express': {'node', 'javascript', 'backend', 'api', 'framework'},
        'nestjs': {'node', 'typescript', 'backend', 'framework'},
        'backend': {'api', 'database', 'server', 'rest', 'graphql', 'python', 'node', 'java', 'go'},
        
        # Languages
        'javascript': {'typescript', 'react', 'vue', 'angular', 'frontend', 'node', 'web', 'es6'},
        'typescript': {'javascript', 'react', 'angular', 'frontend', 'node', 'typed'},
        'java': {'spring', 'backend', 'android', 'kotlin', 'jvm'},
        'kotlin': {'java', 'android', 'backend', 'jvm'},
        'go': {'golang', 'backend', 'microservices', 'cloud'},
        'rust': {'systems', 'backend', 'webassembly', 'performance'},
        'ruby': {'rails', 'backend', 'web', 'scripting'},
        'rails': {'ruby', 'backend', 'web', 'framework'},
        'php': {'laravel', 'backend', 'web', 'wordpress'},
        
        # Cloud
        'aws': {'cloud', 'gcp', 'azure', 'devops', 'infrastructure', 'ec2', 's3', 'lambda', 'rds'},
        'gcp': {'cloud', 'aws', 'azure', 'google cloud', 'devops', 'bigquery', 'gke'},
        'azure': {'cloud', 'aws', 'gcp', 'microsoft', 'devops', 'aks'},
        'cloud': {'aws', 'gcp', 'azure', 'devops', 'infrastructure', 'scalability'},
        
        # DevOps/Infra
        'docker': {'container', 'kubernetes', 'devops', 'deployment', 'image'},
        'kubernetes': {'docker', 'k8s', 'orchestration', 'devops', 'helm', 'cluster'},
        'k8s': {'kubernetes', 'docker', 'orchestration', 'devops'},
        'terraform': {'infrastructure', 'iac', 'aws', 'cloud', 'provisioning'},
        'ansible': {'devops', 'automation', 'configuration', 'deployment'},
        'jenkins': {'ci/cd', 'devops', 'automation', 'pipeline'},
        'github actions': {'ci/cd', 'devops', 'automation', 'github'},
        'gitlab ci': {'ci/cd', 'devops', 'automation', 'gitlab'},
        'ci/cd': {'devops', 'jenkins', 'github actions', 'automation', 'deployment', 'pipeline'},
        'devops': {'docker', 'kubernetes', 'ci/cd', 'aws', 'cloud', 'terraform', 'automation'},
        
        # Databases
        'postgresql': {'postgres', 'sql', 'database', 'relational', 'rds'},
        'postgres': {'postgresql', 'sql', 'database', 'relational'},
        'mysql': {'sql', 'database', 'relational', 'rds'},
        'mongodb': {'nosql', 'database', 'document', 'mongo'},
        'redis': {'cache', 'database', 'nosql', 'key-value', 'session'},
        'elasticsearch': {'search', 'database', 'nosql', 'logging'},
        'cassandra': {'nosql', 'database', 'distributed', 'bigdata'},
        'dynamodb': {'aws', 'database', 'nosql', 'serverless'},
        'sql': {'database', 'postgresql', 'mysql', 'query', 'relational'},
        'nosql': {'mongodb', 'cassandra', 'redis', 'database', 'document'},
        'database': {'sql', 'nosql', 'postgresql', 'mysql', 'mongodb', 'schema'},
        
        # API/Protocols
        'rest': {'api', 'http', 'json', 'backend', 'web services', 'endpoint'},
        'graphql': {'api', 'query', 'backend', 'apollo', 'schema', 'resolver'},
        'api': {'rest', 'graphql', 'json', 'http', 'backend', 'endpoint', 'microservices'},
        'json': {'api', 'rest', 'javascript', 'data', 'serialization'},
        'grpc': {'api', 'microservices', 'protobuf', 'rpc', 'backend'},
        'websocket': {'realtime', 'socket', 'frontend', 'backend', 'events'},
        
        # Architecture
        'microservices': {'distributed', 'services', 'architecture', 'backend', 'scalability', 'kubernetes'},
        'distributed systems': {'microservices', 'scalability', 'backend', 'architecture', 'consistency'},
        'architecture': {'system design', 'microservices', 'scalability', 'backend', 'patterns'},
        'scalability': {'performance', 'distributed', 'caching', 'load balancing', 'architecture'},
        'serverless': {'lambda', 'aws', 'cloud', 'faas', 'api'},
        'event-driven': {'kafka', 'rabbitmq', 'message queue', 'microservices', 'architecture'},
        
        # Message Queues
        'kafka': {'message queue', 'event streaming', 'microservices', 'distributed'},
        'rabbitmq': {'message queue', 'amqp', 'microservices', 'event driven'},
        'sqs': {'aws', 'message queue', 'queue', 'serverless'},
        'message queue': {'kafka', 'rabbitmq', 'sqs', 'async', 'microservices'},
        
        # ML/AI
        'machine learning': {'ml', 'ai', 'tensorflow', 'pytorch', 'scikit', 'model', 'data science'},
        'ml': {'machine learning', 'ai', 'tensorflow', 'pytorch', 'model', 'data'},
        'tensorflow': {'ml', 'ai', 'deep learning', 'neural network', 'python'},
        'pytorch': {'ml', 'ai', 'deep learning', 'neural network', 'python'},
        'deep learning': {'ml', 'ai', 'neural network', 'tensorflow', 'pytorch', 'nlp', 'cv'},
        'nlp': {'natural language processing', 'transformer', 'bert', 'gpt', 'ml'},
        'computer vision': {'cv', 'opencv', 'image processing', 'ml', 'ai'},
        
        # Testing
        'testing': {'unit test', 'integration test', 'e2e', 'jest', 'pytest', 'qa'},
        'jest': {'javascript', 'testing', 'unit test', 'react', 'frontend'},
        'pytest': {'python', 'testing', 'unit test', 'backend'},
        'cypress': {'e2e', 'testing', 'frontend', 'automation'},
        'selenium': {'e2e', 'testing', 'automation', 'browser'},
        
        # Security
        'security': {'authentication', 'authorization', 'oauth', 'jwt', 'encryption'},
        'oauth': {'authentication', 'authorization', 'security', 'sso', 'openid'},
        'jwt': {'authentication', 'security', 'token', 'api'},
        'encryption': {'security', 'cryptography', 'ssl', 'tls', 'https'},
        
        # Misc
        'git': {'version control', 'github', 'gitlab', 'vcs', 'collaboration'},
        'github': {'git', 'version control', 'ci/cd', 'actions', 'collaboration'},
        'agile': {'scrum', 'kanban', 'methodology', 'sprint'},
        'scrum': {'agile', 'methodology', 'sprint'},
        'documentation': {'docs', 'readme', 'wiki', 'technical writing'},
    }
    
    # Fast path: direct lookup
    if keyword_lower in relationships:
        return relationships[keyword_lower]
    
    # Hybrid fallback: simple heuristics for unknown keywords (no LLM)
    # Check if keyword is substring of known keys or vice versa
    related = set()
    for known_key, known_related in relationships.items():
        if keyword_lower in known_key or known_key in keyword_lower:
            related.update(known_related)
            related.add(known_key)
    
    # Pattern matching for common suffixes/prefixes
    if 'db' in keyword_lower or 'database' in keyword_lower:
        related.update({'database', 'sql', 'storage', 'data'})
    if 'test' in keyword_lower:
        related.update({'testing', 'qa', 'automation'})
    if 'api' in keyword_lower:
        related.update({'api', 'backend', 'endpoint', 'rest', 'graphql'})
    if 'js' in keyword_lower or 'script' in keyword_lower:
        related.update({'javascript', 'typescript', 'frontend', 'backend'})
    if 'css' in keyword_lower or 'style' in keyword_lower:
        related.update({'css', 'frontend', 'html', 'ui'})
    if 'cloud' in keyword_lower:
        related.update({'cloud', 'aws', 'gcp', 'azure', 'devops'})
    if 'container' in keyword_lower or 'docker' in keyword_lower:
        related.update({'docker', 'kubernetes', 'container', 'devops'})
    
    return related


def categorize_keywords(
    keywords: List[str],
    user_profile: dict,
    api_key: str = None,
    provider: str = "gemini"
) -> Dict:
    """
    Categorize keywords and map to exact profile keys.
    
    Returns:
    - keyword_to_experiences: Dict[str, List[str]] - keyword -> exact profile keys
    - easy_no_match: List[str] - easy keywords with no match
    - drop: List[str] - hard keywords with no match
    """
    result = {
        "keyword_to_experiences": {},
        "easy_no_match": [],
        "drop": []
    }
    
    # First pass: fast matching (no LLM)
    unmatched_keywords = []
    for keyword in keywords:
        matches = find_related_experiences(keyword, user_profile)
        hard = is_hard_keyword(keyword)
        
        if matches:
            result["keyword_to_experiences"][keyword] = matches
        elif not hard:
            unmatched_keywords.append(keyword)
        else:
            result["drop"].append(keyword)
    
    # Second pass: batch LLM for all unmatched (single API call)
    if unmatched_keywords and api_key:
        llm_matches = batch_llm_plausibility(unmatched_keywords, user_profile, api_key, provider)
        for keyword in unmatched_keywords:
            matches = llm_matches.get(keyword, [])
            if matches:
                result["keyword_to_experiences"][keyword] = matches
            else:
                hard = is_hard_keyword(keyword)
                if not hard:
                    result["easy_no_match"].append(keyword)
                else:
                    result["drop"].append(keyword)
    else:
        for keyword in unmatched_keywords:
            hard = is_hard_keyword(keyword)
            if not hard:
                result["easy_no_match"].append(keyword)
            else:
                result["drop"].append(keyword)
    
    return result


def batch_llm_plausibility(
    keywords: List[str],
    user_profile: dict,
    api_key: str,
    provider: str
) -> Dict[str, List[str]]:
    """
    Batch check plausibility for multiple keywords in one LLM call.
    LLM must pick from exact experience/project titles.
    Returns: {keyword: [experience_titles]}
    """
    experiences = user_profile.get("experience", {})
    projects = user_profile.get("projects", {})
    
    # Build numbered list so LLM uses exact titles
    titles = list(experiences.keys()) + list(projects.keys())
    title_list = "\n".join([f"  {i+1}. {t}" for i, t in enumerate(titles)])
    
    experience_context = "\n".join([
        f"- {title}: {' '.join(get_experience_bullets(entry)[:3])}"
        for title, entry in {**experiences, **projects}.items()
    ])
    
    keywords_list = ", ".join(keywords)
    
    prompt = f"""For each skill, which experiences COULD plausibly have used it (or something very similar)?

Skills: {keywords_list}

Experiences:
{experience_context}

VALID TITLES (you MUST use these exact names):
{title_list}

Rules:
1. Only mark if the role realistically could have involved this skill
2. Don't hallucinate - if the role was simple/entry-level, don't claim they used complex skills
3. You MUST use the exact title from the VALID TITLES list above

Return in this exact format:
skill1: Exact Title 1, Exact Title 2
skill2: Exact Title 3
skill3: NONE"""

    try:
        model = get_model_for_provider(provider)
        fallback_models = get_fallback_models(provider)
        response = generate_with_retry(model, prompt, max_retries=3, api_key=api_key, provider=provider, fallback_models=fallback_models, step_name="Batch LLM Plausibility")
        
        title_set = set(titles)  # For validation
        results = {}
        for line in response.strip().split('\n'):
            if ':' in line:
                skill, exps = line.split(':', 1)
                skill = skill.strip().lower()
                exps = exps.strip()
                
                if exps.upper() == "NONE":
                    results[skill] = []
                else:
                    # Only keep titles that exactly match profile keys
                    exp_list = [e.strip() for e in exps.split(',') if e.strip() in title_set]
                    results[skill] = exp_list
        
        return results
    except Exception as e:
        print(f"[WARNING] Batch LLM check failed: {e}")
        return {k: [] for k in keywords}


def extract_keywords_from_jd(
    job_description: str,
    api_key: str,
    provider: str
) -> List[str]:
    """Extract ATS keywords from job description."""
    
    prompt = f"""You are a hiring manager who just posted this job. You're now setting up ATS (Applicant Tracking System) filters to screen incoming resumes. You need to decide what keywords to search for.

You will set up two lists:

MUST-HAVE: Keywords you will type into the ATS to filter out unqualified candidates. These are hard requirements — if a resume doesn't contain these words, you reject it. Only include specific, named technologies, tools, languages, platforms, or certifications that are explicitly required in the job posting. Each keyword should be 1-3 words max.

NICE-TO-HAVE: Keywords that would make a candidate stand out but aren't dealbreakers. These are specific technical terms mentioned in the job description that show deeper fit. Still must be concrete and named — not vague descriptions. Each keyword should be 1-3 words max.

NEVER include:
- Soft skills or personality traits
- Job responsibilities rephrased as keywords
- Vague categories like "cloud platforms" or "databases" (use the specific names instead)
- Anything longer than 3 words

Return in this exact format:
MUST-HAVE:
- keyword
- keyword

NICE-TO-HAVE:
- keyword
- keyword

Job Description:
{job_description}"""

    model = get_model_for_provider(provider)
    fallback_models = get_fallback_models(provider)
    response = generate_with_retry(model, prompt, max_retries=3, api_key=api_key, provider=provider, fallback_models=fallback_models, step_name="Extract Keywords from JD")
    
    must_have = []
    nice_to_have = []
    current_section = None
    
    for line in response.strip().split('\n'):
        line_lower = line.strip().lower()
        if 'must-have' in line_lower or 'must have' in line_lower:
            current_section = 'must'
            continue
        elif 'nice-to-have' in line_lower or 'nice to have' in line_lower:
            current_section = 'nice'
            continue
        
        if line_lower.startswith('- '):
            kw = line_lower[2:].strip()
            # Post-filter: drop anything over 3 words (not a real keyword)
            if kw and len(kw.split()) <= 3:
                if current_section == 'nice':
                    nice_to_have.append(kw)
                else:
                    must_have.append(kw)
    
    must_have = list(set(must_have))
    nice_to_have = list(set(nice_to_have))
    print(f"[EXTRACTOR] Must-have: {len(must_have)} — {must_have}")
    print(f"[EXTRACTOR] Nice-to-have: {len(nice_to_have)} — {nice_to_have}")
    
    return {"must_have": must_have, "nice_to_have": nice_to_have, "all": must_have + nice_to_have}


def export_to_yaml(result: Dict) -> str:
    """Export categorized keywords to YAML."""
    return yaml.dump(result, default_flow_style=False, sort_keys=False)


@dataclass
class KeywordExtractionResult:
    """Keyword extraction result with mappings to exact profile keys."""
    keyword_to_experiences: Dict[str, List[str]] = field(default_factory=dict)  # keyword -> [exact profile keys]
    easy_no_match: List[str] = field(default_factory=list)  # easy keywords, no match yet
    drop: List[str] = field(default_factory=list)  # hard keywords, no match
    must_have: List[str] = field(default_factory=list)  # ATS hard filter keywords
    nice_to_have: List[str] = field(default_factory=list)  # bonus keywords for phrasing
    
    @property
    def all_keywords_to_include(self) -> List[str]:
        """All keywords that should be included (mapped + easy no match)."""
        return list(self.keyword_to_experiences.keys()) + self.easy_no_match


def extract_keywords_with_rag(
    job_description: str,
    user_profile: dict,
    api_key: str,
    provider: str = "gemini"
) -> KeywordExtractionResult:
    """
    Extract keywords from JD and map to exact profile keys.
    
    Hybrid approach:
    1. Fast: direct string matching + related terms dict
    2. Fallback: LLM plausibility check (batch, single call)
    
    Returns keyword -> [exact profile keys].
    Strategizer fetches bullets directly via profile[key].
    """
    print("[EXTRACTOR] Starting keyword extraction...")
    
    # Step 1: Extract keywords from JD (with must-have / nice-to-have tiers)
    keyword_tiers = extract_keywords_from_jd(job_description, api_key, provider)
    all_keywords = keyword_tiers["all"]
    print(f"[EXTRACTOR] Found {len(all_keywords)} keywords ({len(keyword_tiers['must_have'])} must-have, {len(keyword_tiers['nice_to_have'])} nice-to-have)")
    
    # Step 2: Map keywords to exact profile keys (with LLM fallback)
    categorized = categorize_keywords(all_keywords, user_profile, api_key, provider)
    
    print(f"[EXTRACTOR] Mapped: {len(categorized['keyword_to_experiences'])}, Easy no match: {len(categorized['easy_no_match'])}, Drop: {len(categorized['drop'])}")
    
    return KeywordExtractionResult(
        keyword_to_experiences=categorized["keyword_to_experiences"],
        easy_no_match=categorized["easy_no_match"],
        drop=categorized["drop"],
        must_have=keyword_tiers["must_have"],
        nice_to_have=keyword_tiers["nice_to_have"]
    )
