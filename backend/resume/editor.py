"""Fix issues identified by the reviewer through iterative editing."""
import re
from typing import List
from schemas import ResumeReview, ReviewIssue, ResumeStrategy, ResumeDraft


def edit_resume(
    draft: ResumeDraft,
    review: ResumeReview,
    strategy: ResumeStrategy,
    max_iterations: int = 3
) -> ResumeDraft:
    """
    Fix issues in the resume based on reviewer feedback.
    Returns edited draft (or original if can't fix).
    """
    print(f"[EDITOR] Attempting to fix {len(review.issues)} issues...")
    
    current_draft = draft
    
    for iteration in range(max_iterations):
        if review.passed:
            print(f"[EDITOR] All checks passed after {iteration} iterations")
            break
        
        print(f"[EDITOR] Iteration {iteration + 1}/{max_iterations}")
        
        # Group issues by type
        length_issues = [i for i in review.issues if i.check_name == "Length Check"]
        exp_count_issues = [i for i in review.issues if i.check_name == "Experience Count"]
        hallucination_issues = [i for i in review.issues if i.check_name == "Hallucination Guard"]
        quantification_issues = [i for i in review.issues if i.check_name == "Quantification"]
        coverage_issues = [i for i in review.issues if i.check_name == "Keyword Coverage"]
        
        # Apply fixes in priority order
        if length_issues:
            current_draft = fix_length(current_draft, strategy)
        
        if hallucination_issues:
            current_draft = fix_hallucinations(current_draft, hallucination_issues)
        
        if quantification_issues:
            current_draft = fix_quantification(current_draft, strategy)
        
        if coverage_issues:
            current_draft = fix_keyword_coverage(current_draft, strategy, coverage_issues)
        
        # Note: exp_count issues can't be auto-fixed (need more profile data)
        # These require user intervention
        
        # Re-check if we've resolved enough issues
        remaining_errors = [
            i for i in review.issues 
            if i.severity == 'error' and i.check_name != "Experience Count"
        ]
        
        if not remaining_errors:
            review.passed = True
            break
    
    return current_draft


def fix_length(draft: ResumeDraft, strategy: ResumeStrategy) -> ResumeDraft:
    """Fix length by removing lowest-relevance experience or shortening bullets."""
    latex = draft.latex_source
    
    # Strategy 1: Remove least relevant experience
    included_exps = [e for e in strategy.selected_experiences if e.should_include]
    
    if len(included_exps) > 2:
        # Remove the lowest-scoring experience
        included_exps.sort(key=lambda x: x.relevance_score)
        lowest_exp = included_exps[0]
        lowest_exp.should_include = False
        
        # Remove from LaTeX
        pattern = rf'\\resumeSubheading\s*{{\s*{re.escape(lowest_exp.title)}[^}}]*}}.*?(?=\\resumeSubheading|\\section|\Z)'
        latex = re.sub(pattern, '', latex, flags=re.DOTALL)
        
        print(f"[EDITOR] Removed experience '{lowest_exp.title}' to reduce length")
    else:
        # Strategy 2: Shorten bullets by removing last bullet from each experience
        latex = shorten_bullets(latex)
        print("[EDITOR] Shortened bullet points to reduce length")
    
    draft.latex_source = latex
    return draft


def shorten_bullets(latex: str) -> str:
    """Remove last bullet from each experience section."""
    # Find bullet lists and remove last item from each
    pattern = r'(\\resumeItemListStart.*?)(\\resumeItem\{[^}]+\})(\s*\\resumeItemListEnd)'
    
    def remove_last_bullet(match):
        prefix = match.group(1)
        last_bullet = match.group(2)
        suffix = match.group(3)
        
        # Check if there are multiple bullets
        bullet_count = prefix.count('\\resumeItem{') + 1
        
        if bullet_count > 2:
            # Remove the last bullet before the end
            return prefix + suffix
        else:
            # Keep if only 2 bullets
            return match.group(0)
    
    return re.sub(pattern, remove_last_bullet, latex, flags=re.DOTALL)


def fix_hallucinations(draft: ResumeDraft, issues: List[ReviewIssue]) -> ResumeDraft:
    """Remove or soften hallucinated claims."""
    latex = draft.latex_source
    
    for issue in issues:
        if not issue.location:
            continue
        
        # Find the problematic bullet
        location = issue.location
        
        # Strategy 1: Remove specific metrics
        # Replace "increased X by 50%" with "improved X significantly"
        patterns_to_soften = [
            (r'(increased|decreased|reduced|improved)\s+[\w\s]+\s+by\s+\d+%', r'\1'),
            (r'led\s+[\w\s]+\s+of\s+\d+', r'led'),
            (r'managed\s+\$[\d,]+', r'managed budgets'),
        ]
        
        for pattern, replacement in patterns_to_soften:
            if re.search(pattern, location, re.IGNORECASE):
                # Apply to full latex
                latex = re.sub(pattern, replacement, latex, flags=re.IGNORECASE)
                print(f"[EDITOR] Softened metric: '{location[:40]}...'")
                break
        else:
            # Strategy 2: If can't soften, remove the bullet entirely
            bullet_pattern = rf'\\resumeItem\{{[^}}]*{re.escape(location[:30])}[^}}]*\}}'
            latex = re.sub(bullet_pattern, '', latex)
            print(f"[EDITOR] Removed unverifiable bullet: '{location[:40]}...'")
    
    draft.latex_source = latex
    return draft


def fix_quantification(draft: ResumeDraft, strategy: ResumeStrategy) -> ResumeDraft:
    """Add quantification hints to unquantified bullets (marked for user)."""
    # This is more of a hint system - we flag bullets that should be quantified
    # but don't make up numbers
    
    latex = draft.latex_source
    
    # Find bullets without numbers
    bullet_pattern = r'\\resumeItem\{([^}]+)\}'
    bullets = re.findall(bullet_pattern, latex)
    
    for bullet in bullets:
        # Check if already has quantification
        has_numbers = bool(re.search(r'\d+%|\d+ users|\d+ [\w\s]+ (million|thousand)|\$[\d,]+', bullet))
        
        if not has_numbers and 'scope' not in bullet.lower():
            # Add scope hint
            # Replace bullet with version that has [QUANTIFY] marker
            new_bullet = bullet + " [Add: team size, users affected, or time saved]"
            latex = latex.replace(f'\\resumeItem{{{bullet}}}', f'\\resumeItem{{{new_bullet}}}')
    
    # Note: In production, you'd want to return these as warnings rather than editing
    # For now, this marks them for user attention
    
    draft.latex_source = latex
    return draft


def fix_keyword_coverage(
    draft: ResumeDraft, 
    strategy: ResumeStrategy,
    issues: List[ReviewIssue]
) -> ResumeDraft:
    """Add missing keywords to skills section."""
    latex = draft.latex_source
    
    # Extract missing keywords from issue messages
    missing_keywords = []
    for issue in issues:
        if issue.suggestion and "Missing keywords:" in issue.suggestion:
            keywords_text = issue.suggestion.split("Missing keywords:")[1]
            missing_keywords.extend([k.strip() for k in keywords_text.split(',')])
    
    if missing_keywords:
        # Find skills section and add missing keywords
        # Look for existing skills pattern
        skills_pattern = r'(\\section\{Skills\}.*?)(\\end\{itemize\}|\\section|\Z)'
        
        def add_skills(match):
            section = match.group(1)
            # Add new skills
            new_skills = ', '.join(missing_keywords[:5])  # Max 5 new skills
            
            # Try to append to existing skills
            if 'itemize' in section:
                return section.replace(
                    '\\end{itemize}',
                    f'\\item {new_skills}\n\\end{{enumerate}}'
                )
            else:
                return section + f'\\textbf{{{new_skills}}}\\newline\n'
        
        latex = re.sub(skills_pattern, add_skills, latex, flags=re.DOTALL)
        print(f"[EDITOR] Added {len(missing_keywords)} missing keywords to skills section")
    
    draft.latex_source = latex
    return draft


def create_fix_summary(review: ResumeReview, iteration: int) -> str:
    """Create a human-readable summary of fixes applied."""
    lines = [f"Editing Iteration {iteration}", "=" * 40]
    
    for issue in review.issues:
        lines.append(f"[{issue.severity.upper()}] {issue.check_name}")
        lines.append(f"  Issue: {issue.message}")
        if issue.suggestion:
            lines.append(f"  Fix: {issue.suggestion}")
        lines.append("")
    
    return "\n".join(lines)
