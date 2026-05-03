"""Fill LaTeX template and compile to PDF."""
import os
import re
import subprocess
import tempfile
from typing import Optional
from schemas import ResumeStrategy, ResumeDraft, JobExtraction


def draft_resume(
    strategy: ResumeStrategy,
    job_extraction: JobExtraction,
    user_profile: dict,
    latex_template: str,
    output_dir: str = "./output"
) -> ResumeDraft:
    """
    Fill the LaTeX template with tailored content and compile to PDF.
    """
    print("[DRAFTER] Filling LaTeX template...")
    
    draft = ResumeDraft()
    
    # Fill the template
    filled_latex = fill_template(
        latex_template,
        strategy,
        job_extraction,
        user_profile
    )
    
    draft.latex_source = filled_latex
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Write LaTeX file
    tex_path = os.path.join(output_dir, "resume.tex")
    with open(tex_path, 'w', encoding='utf-8') as f:
        f.write(filled_latex)
    
    # Compile to PDF
    pdf_path = compile_latex(tex_path, output_dir)
    
    if pdf_path:
        draft.pdf_path = pdf_path
        draft.compilation_success = True
        print(f"[DRAFTER] PDF compiled: {pdf_path}")
    else:
        draft.compilation_success = False
        draft.compilation_errors.append("Failed to compile LaTeX")
        print("[DRAFTER] LaTeX compilation failed")
    
    return draft


def fill_template(
    template: str,
    strategy: ResumeStrategy,
    job_extraction: JobExtraction,
    user_profile: dict
) -> str:
    """Fill the LaTeX template with resume content."""
    
    filled = template
    
    # Replace personal info
    filled = replace_placeholder(filled, "{{NAME}}", user_profile.get("name", ""))
    filled = replace_placeholder(filled, "{{TITLE}}", user_profile.get("title", ""))
    filled = replace_placeholder(filled, "{{EMAIL}}", user_profile.get("contact", {}).get("email", ""))
    filled = replace_placeholder(filled, "{{PHONE}}", user_profile.get("contact", {}).get("phone", ""))
    
    # Replace summary
    filled = replace_placeholder(filled, "{{SUMMARY}}", strategy.summary_angle)
    
    # Replace skills
    skills = user_profile.get("skills", []) + strategy.suggested_skill_additions
    skills_str = ", ".join(skills[:12])  # Limit to 12 skills
    filled = replace_placeholder(filled, "{{SKILLS}}", skills_str)
    
    # Build experience section
    experience_latex = build_experience_section(strategy.selected_experiences)
    filled = replace_placeholder(filled, "{{EXPERIENCE}}", experience_latex)
    
    # Build projects section (if space permits)
    projects_latex = build_projects_section(strategy.selected_projects)
    filled = replace_placeholder(filled, "{{PROJECTS}}", projects_latex)
    
    # Build education section
    education_latex = build_education_section(user_profile)
    filled = replace_placeholder(filled, "{{EDUCATION}}", education_latex)
    
    # Clean up any remaining placeholders
    filled = remove_empty_placeholders(filled)
    
    return filled


def replace_placeholder(template: str, placeholder: str, value: str) -> str:
    """Safely replace a placeholder with escaped LaTeX content."""
    escaped_value = escape_latex(value)
    return template.replace(placeholder, escaped_value)


def escape_latex(text: str) -> str:
    """Escape special LaTeX characters."""
    if not text:
        return ""
    
    # LaTeX special characters
    special_chars = {
        '\\': '\\textbackslash{}',
        '{': '\\{',
        '}': '\\}',
        '$': '\\$',
        '&': '\\&',
        '#': '\\#',
        '^': '\\textasciicircum{}',
        '_': '\\_',
        '~': '\\textasciitilde{}',
        '%': '\\%',
    }
    
    for char, replacement in special_chars.items():
        text = text.replace(char, replacement)
    
    return text


def build_experience_section(experiences: list) -> str:
    """Build LaTeX for experience section."""
    latex_parts = []
    
    for exp in experiences:
        if not exp.should_include:
            continue
        
        # Entry header
        entry = f"\\resumeSubheading\n"
        entry += f"  {{{escape_latex(exp.title)}}}{{}}\n"
        entry += f"  {{}}{{}}\n"
        
        # Bullet points
        entry += "  \\resumeItemListStart\n"
        for dot in exp.dotjots:
            entry += f"    \\resumeItem{{{escape_latex(dot)}}}\n"
        entry += "  \\resumeItemListEnd\n"
        
        latex_parts.append(entry)
    
    return "\n".join(latex_parts)


def build_projects_section(projects: list) -> str:
    """Build LaTeX for projects section."""
    if not any(p.should_include for p in projects):
        return "% No projects selected"
    
    latex_parts = ["\\section{Projects}"]
    
    for proj in projects:
        if not proj.should_include:
            continue
        
        entry = f"\\resumeSubheading\n"
        entry += f"  {{{escape_latex(proj.title)}}}{{}}\n"
        entry += f"  {{}}{{}}\n"
        
        entry += "  \\resumeItemListStart\n"
        for dot in proj.dotjots:
            entry += f"    \\resumeItem{{{escape_latex(dot)}}}\n"
        entry += "  \\resumeItemListEnd\n"
        
        latex_parts.append(entry)
    
    return "\n".join(latex_parts)


def build_education_section(user_profile: dict) -> str:
    """Build LaTeX for education section."""
    # For now, simple placeholder - expand based on profile structure
    courses = user_profile.get("courses", [])
    
    if not courses:
        return "% Education section"
    
    latex = "\\section{Education}\n"
    latex += "\\resumeSubheading\n"
    latex += "  {Relevant Coursework}{}\n"
    latex += "  {}{}\n"
    latex += "  \\resumeItemListStart\n"
    latex += f"    \\resumeItem{{{escape_latex(', '.join(courses[:5]))}}}\n"
    latex += "  \\resumeItemListEnd\n"
    
    return latex


def remove_empty_placeholders(template: str) -> str:
    """Remove or comment out any remaining placeholders."""
    # Pattern to match {{PLACEHOLDER}} style
    placeholder_pattern = r'\{\{[A-Z_]+\}\}'
    
    def replace_empty(match):
        placeholder = match.group(0)
        return f"% Unused: {placeholder}"
    
    return re.sub(placeholder_pattern, replace_empty, template)


def compile_latex(tex_path: str, output_dir: str) -> Optional[str]:
    """
    Compile LaTeX to PDF using pdflatex.
    Returns path to PDF if successful, None otherwise.
    """
    try:
        # Run pdflatex twice for references
        for _ in range(2):
            result = subprocess.run(
                ['pdflatex', '-interaction=nonstopmode', '-output-directory', output_dir, tex_path],
                capture_output=True,
                text=True,
                timeout=60
            )
        
        # Check if PDF was created
        pdf_path = tex_path.replace('.tex', '.pdf')
        if os.path.exists(pdf_path):
            return pdf_path
        else:
            return None
            
    except subprocess.TimeoutExpired:
        print("[DRAFTER] LaTeX compilation timed out")
        return None
    except FileNotFoundError:
        print("[DRAFTER] pdflatex not found. Is LaTeX installed?")
        return None
    except Exception as e:
        print(f"[DRAFTER] LaTeX compilation error: {e}")
        return None


def estimate_page_count(latex_source: str) -> float:
    """Estimate page count based on content length."""
    # Rough heuristic: ~3000 chars per page for dense resume
    char_count = len(latex_source)
    return char_count / 3000
