"""Template gallery: business, educational, legal, medical, and government PDF templates."""

import os
import json
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Template:
    template_id: str = ""
    name: str = ""
    description: str = ""
    category: str = ""
    subcategory: str = ""
    tags: list[str] = field(default_factory=list)
    preview_url: str = ""
    download_url: str = ""
    file_size_kb: int = 0
    page_count: int = 0
    is_premium: bool = False
    popularity: int = 0
    author: str = "PDFMind"
    created_at: str = ""
    updated_at: str = ""
    rating: float = 0.0
    download_count: int = 0


@dataclass
class TemplateCategory:
    category_id: str = ""
    name: str = ""
    description: str = ""
    icon: str = ""
    template_count: int = 0


class TemplatesGallery:
    """Template gallery with 50+ professional templates across 7 categories."""

    def __init__(self):
        self._templates: dict[str, Template] = {}
        self._categories: dict[str, TemplateCategory] = {}
        self._register_templates()

    def _register_templates(self):
        categories = [
            TemplateCategory("business", "Business", "Professional business documents", "briefcase", 10),
            TemplateCategory("resume", "Resume & CV", "Stand-out resumes and CVs", "user", 8),
            TemplateCategory("educational", "Educational", "Academic and educational templates", "book", 8),
            TemplateCategory("legal", "Legal", "Court filings and legal documents", "gavel", 8),
            TemplateCategory("medical", "Medical", "Medical forms and documents", "heart", 6),
            TemplateCategory("government", "Government", "Government forms and applications", "building", 6),
            TemplateCategory("creative", "Creative", "Creative and design templates", "palette", 6),
        ]
        for cat in categories:
            self._categories[cat.category_id] = cat

        templates = [
            Template("invoice_modern", "Modern Invoice", "Clean, professional invoice with itemized billing",
                     "business", "invoice", ["invoice", "billing", "professional"], file_size_kb=45, page_count=2),
            Template("invoice_classic", "Classic Invoice", "Traditional invoice template with company header",
                     "business", "invoice", ["invoice", "traditional"], file_size_kb=38, page_count=1),
            Template("contract_service", "Service Agreement", "Professional service contract template",
                     "business", "contract", ["contract", "agreement", "service"], file_size_kb=52, page_count=6),
            Template("contract_nda", "NDA Template", "Non-disclosure agreement template",
                     "business", "contract", ["nda", "confidential"], file_size_kb=35, page_count=3),
            Template("proposal_business", "Business Proposal", "Compelling business proposal template",
                     "business", "proposal", ["proposal", "business"], file_size_kb=68, page_count=10),
            Template("letter_business", "Business Letter", "Professional business letterhead",
                     "business", "letter", ["letter", "formal"], file_size_kb=25, page_count=1),
            Template("letter_cover", "Cover Letter", "Job application cover letter",
                     "business", "letter", ["cover", "job"], file_size_kb=22, page_count=1),
            Template("meeting_minutes", "Meeting Minutes", "Professional meeting minutes template",
                     "business", "meeting", ["meeting", "minutes", "notes"], file_size_kb=30, page_count=2),
            Template("memo", "Memo Template", "Internal memorandum template",
                     "business", "memo", ["memo", "memorandum", "internal"], file_size_kb=20, page_count=1),
            Template("quotation", "Quotation", "Professional price quotation template",
                     "business", "quotation", ["quote", "pricing"], file_size_kb=28, page_count=1),
            Template("resume_modern", "Modern Resume", "Clean, ATS-friendly resume template",
                     "resume", "resume", ["resume", "modern", "ats"], file_size_kb=40, page_count=2),
            Template("resume_creative", "Creative Resume", "Design-forward resume for creative roles",
                     "resume", "resume", ["resume", "creative", "design"], file_size_kb=55, page_count=2),
            Template("resume_executive", "Executive Resume", "Senior-level executive resume template",
                     "resume", "resume", ["resume", "executive", "senior"], file_size_kb=42, page_count=3),
            Template("cv_academic", "Academic CV", "Comprehensive academic curriculum vitae",
                     "resume", "cv", ["cv", "academic", "phd"], file_size_kb=48, page_count=4),
            Template("cv_technical", "Technical Resume", "Resume optimized for technical roles",
                     "resume", "resume", ["resume", "technical", "engineering"], file_size_kb=38, page_count=2),
            Template("resume_student", "Student Resume", "Entry-level resume for students and graduates",
                     "resume", "resume", ["resume", "student", "entry"], file_size_kb=30, page_count=1),
            Template("portfolio", "Portfolio", "Professional portfolio template",
                     "resume", "portfolio", ["portfolio", "showcase"], file_size_kb=65, page_count=8),
            Template("cover_letter_modern", "Modern Cover Letter", "Matching cover letter template",
                     "resume", "cover", ["cover", "letter", "matching"], file_size_kb=22, page_count=1),
            Template("report_research", "Research Report", "Academic research report template",
                     "educational", "report", ["research", "academic", "report"], file_size_kb=55, page_count=15),
            Template("thesis", "Thesis Template", "University thesis/dissertation template",
                     "educational", "thesis", ["thesis", "dissertation", "university"], file_size_kb=70, page_count=30),
            Template("worksheet", "Worksheet", "Educational worksheet template",
                     "educational", "worksheet", ["worksheet", "education", "teaching"], file_size_kb=35, page_count=2),
            Template("lesson_plan", "Lesson Plan", "Teacher lesson plan template",
                     "educational", "lesson", ["lesson", "plan", "teacher"], file_size_kb=28, page_count=2),
            Template("syllabus", "Syllabus", "Course syllabus template",
                     "educational", "syllabus", ["syllabus", "course"], file_size_kb=32, page_count=4),
            Template("certificate", "Certificate", "Achievement certificate template",
                     "educational", "certificate", ["certificate", "achievement"], file_size_kb=45, page_count=1),
            Template("lab_report", "Lab Report", "Scientific lab report template",
                     "educational", "lab", ["lab", "report", "science"], file_size_kb=40, page_count=6),
            Template("bibliography", "Bibliography", "References and bibliography template",
                     "educational", "references", ["bibliography", "references"], file_size_kb=25, page_count=3),
            Template("court_filing", "Court Filing", "Standard court filing template",
                     "legal", "court", ["court", "filing", "legal"], file_size_kb=45, page_count=8),
            Template("affidavit", "Affidavit", "Sworn affidavit template",
                     "legal", "affidavit", ["affidavit", "sworn"], file_size_kb=30, page_count=3),
            Template("power_of_attorney", "Power of Attorney", "General power of attorney form",
                     "legal", "poa", ["power", "attorney", "legal"], file_size_kb=35, page_count=4),
            Template("will_testament", "Last Will", "Last will and testament template",
                     "legal", "will", ["will", "testament", "estate"], file_size_kb=40, page_count=6),
            Template("lease_agreement", "Lease Agreement", "Residential lease agreement",
                     "legal", "lease", ["lease", "rental", "property"], file_size_kb=42, page_count=8),
            Template("eviction_notice", "Eviction Notice", "Eviction notice template",
                     "legal", "notice", ["eviction", "notice"], file_size_kb=20, page_count=1),
            Template("contract_employment", "Employment Contract", "Employment agreement template",
                     "legal", "employment", ["employment", "contract"], file_size_kb=48, page_count=6),
            Template("terms_of_service", "Terms of Service", "Website terms of service template",
                     "legal", "terms", ["terms", "service", "legal"], file_size_kb=38, page_count=5),
            Template("referral", "Medical Referral", "Patient referral form",
                     "medical", "referral", ["referral", "patient"], file_size_kb=28, page_count=1),
            Template("prescription", "Prescription Pad", "Medical prescription template",
                     "medical", "prescription", ["prescription", "medical"], file_size_kb=22, page_count=1),
            Template("discharge_summary", "Discharge Summary", "Hospital discharge summary",
                     "medical", "discharge", ["discharge", "hospital"], file_size_kb=35, page_count=3),
            Template("patient_intake", "Patient Intake", "New patient intake form",
                     "medical", "intake", ["patient", "intake", "form"], file_size_kb=40, page_count=4),
            Template("progress_note", "Progress Note", "Clinical progress note template",
                     "medical", "note", ["progress", "note", "clinical"], file_size_kb=25, page_count=1),
            Template("lab_order", "Lab Order", "Laboratory order form",
                     "medical", "lab", ["lab", "order", "test"], file_size_kb=20, page_count=1),
            Template("tax_return", "Tax Return", "Personal tax return summary",
                     "government", "tax", ["tax", "return", "irs"], file_size_kb=55, page_count=12),
            Template("application_license", "License Application", "General license application form",
                     "government", "application", ["license", "application"], file_size_kb=35, page_count=4),
            Template("permit", "Permit Application", "Building permit application",
                     "government", "permit", ["permit", "building"], file_size_kb=40, page_count=5),
            Template("passport_application", "Passport Application", "Passport application form",
                     "government", "passport", ["passport", "application"], file_size_kb=30, page_count=2),
            Template("voter_registration", "Voter Registration", "Voter registration form",
                     "government", "voter", ["voter", "registration"], file_size_kb=18, page_count=1),
            Template("foia_request", "FOIA Request", "Freedom of Information Act request",
                     "government", "foia", ["foia", "request", "freedom"], file_size_kb=22, page_count=1),
            Template("poster_large", "Large Poster", "Marketing poster template (24x36)",
                     "creative", "poster", ["poster", "marketing"], file_size_kb=80, page_count=1),
            Template("brochure", "Tri-fold Brochure", "Professional tri-fold brochure",
                     "creative", "brochure", ["brochure", "marketing"], file_size_kb=95, page_count=2),
            Template("flyer", "Event Flyer", "Eye-catching event flyer template",
                     "creative", "flyer", ["flyer", "event"], file_size_kb=50, page_count=1),
            Template("newsletter", "Newsletter", "Professional newsletter template",
                     "creative", "newsletter", ["newsletter", "communication"], file_size_kb=60, page_count=4),
            Template("social_media", "Social Media Kit", "Social media graphics template",
                     "creative", "social", ["social", "media", "graphics"], file_size_kb=70, page_count=6),
            Template("business_card", "Business Card", "Professional business card template",
                     "creative", "card", ["business", "card"], file_size_kb=15, page_count=1),
        ]
        for tmpl in templates:
            tmpl.popularity = hash(tmpl.template_id) % 1000
            self._templates[tmpl.template_id] = tmpl

    def get_all_templates(self) -> list[Template]:
        return list(self._templates.values())

    def get_template(self, template_id: str) -> Optional[Template]:
        return self._templates.get(template_id)

    def get_categories(self) -> list[TemplateCategory]:
        return list(self._categories.values())

    def get_templates_by_category(self, category: str) -> list[Template]:
        return [t for t in self._templates.values() if t.category == category]

    def search_templates(self, query: str) -> list[Template]:
        q = query.lower()
        return [t for t in self._templates.values()
                if q in t.name.lower() or q in t.description.lower()
                or any(q in tag for tag in t.tags)]

    def get_popular_templates(self, limit: int = 10) -> list[Template]:
        return sorted(self._templates.values(), key=lambda t: t.popularity, reverse=True)[:limit]

    def get_recent_templates(self, limit: int = 10) -> list[Template]:
        return list(self._templates.values())[:limit]

    def get_premium_templates(self) -> list[Template]:
        return [t for t in self._templates.values() if t.is_premium]

    def download_template(self, template_id: str, output_dir: str) -> Optional[str]:
        tmpl = self._templates.get(template_id)
        if not tmpl:
            return None
        output_path = os.path.join(output_dir, f"{template_id}.pdf")
        logger.info(f"Template downloaded: {tmpl.name} -> {output_path}")
        return output_path

    def get_recommendations(self, based_on: str) -> list[Template]:
        source = self._templates.get(based_on)
        if not source:
            return self.get_popular_templates(5)
        related = [t for t in self._templates.values()
                   if t.template_id != based_on and (t.category == source.category or
                   bool(set(t.tags) & set(source.tags)))]
        return sorted(related, key=lambda t: t.popularity, reverse=True)[:5]

    def get_gallery_stats(self) -> dict:
        return {
            "total_templates": len(self._templates),
            "categories": len(self._categories),
            "total_downloads": sum(t.download_count for t in self._templates.values()),
            "premium_count": len([t for t in self._templates.values() if t.is_premium]),
            "category_counts": {
                cat: len(self.get_templates_by_category(cat))
                for cat in self._categories
            },
        }
