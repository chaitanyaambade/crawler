from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, HttpUrl


class CrawlRequest(BaseModel):
    url: HttpUrl
    client_name: str
    industry: str = ""


class StepStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    complete = "complete"
    failed = "failed"


class StepInfo(BaseModel):
    status: StepStatus = StepStatus.pending
    detail: str = ""
    started_at: datetime | None = None
    finished_at: datetime | None = None


STEP_NAMES = [
    "discovering",
    "crawling",
    "extracting",
    "colors",
    "images",
    "complete",
]


class CrawlJob(BaseModel):
    job_id: str = Field(default_factory=lambda: uuid4().hex[:12])
    url: str
    client_name: str
    industry: str = ""
    status: str = "discovering"
    steps: dict[str, StepInfo] = Field(
        default_factory=lambda: {name: StepInfo() for name in STEP_NAMES}
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    result: dict[str, Any] | None = None


class BrandInfo(BaseModel):
    dominant_color: str = ""
    palette: list[str] = []
    fonts: list[str] = []
    logo_url: str = ""
    favicon_url: str = ""
    og_image: str = ""


class ContactInfo(BaseModel):
    emails: list[str] = []
    phones: list[str] = []
    addresses: list[str] = []


class SocialLinks(BaseModel):
    instagram: str = ""
    twitter: str = ""
    linkedin: str = ""
    facebook: str = ""
    youtube: str = ""
    github: str = ""
    tiktok: str = ""
    pinterest: str = ""
    medium: str = ""
    discord: str = ""
    slack: str = ""
    telegram: str = ""


class ProductItem(BaseModel):
    name: str
    description: str = ""
    image_url: str = ""
    price: str = ""
    category: str = ""


class CategoryItem(BaseModel):
    name: str
    url: str = ""
    subcategories: list["CategoryItem"] = []


class MetadataInfo(BaseModel):
    title: str = ""
    description: str = ""
    keywords: list[str] = []
    structured_data: dict[str, Any] = {}


class TeamMember(BaseModel):
    name: str
    role: str = ""
    photo_url: str = ""
    linkedin_url: str = ""


class PricingPlan(BaseModel):
    name: str
    price: str = ""
    billing_period: str = ""
    features: list[str] = []
    is_highlighted: bool = False


class Testimonial(BaseModel):
    quote: str
    author_name: str = ""
    author_company: str = ""
    author_role: str = ""
    rating: float | None = None


class TechStack(BaseModel):
    frameworks: list[str] = []
    cms: list[str] = []
    analytics: list[str] = []
    cdn: list[str] = []
    other: list[str] = []


class BrandVoice(BaseModel):
    tone: str = ""
    formality: str = ""
    person: str = ""
    personality: list[str] = []


class ClientLogo(BaseModel):
    name: str
    logo_url: str = ""


class CaseStudy(BaseModel):
    title: str
    summary: str = ""
    client_name: str = ""
    url: str = ""
    metrics: list[str] = []


class MediaMention(BaseModel):
    title: str
    source: str = ""
    url: str = ""
    date: str = ""


class CTAButton(BaseModel):
    text: str
    url: str = ""
    location: str = ""


class LeadMagnet(BaseModel):
    type: str
    title: str = ""
    description: str = ""
    url: str = ""


class IndustryInfo(BaseModel):
    primary: str = ""
    secondary: str = ""
    confidence: float = 0.0


class CrawlResult(BaseModel):
    company_name: str = ""
    tagline: str = ""
    about: str = ""
    brand: BrandInfo = Field(default_factory=BrandInfo)
    metadata: MetadataInfo = Field(default_factory=MetadataInfo)
    social_links: SocialLinks = Field(default_factory=SocialLinks)
    products: list[ProductItem] = []
    categories: list[CategoryItem] = []
    features: list[str] = []
    images: list[str] = []
    contact: ContactInfo = Field(default_factory=ContactInfo)
    pages_crawled: list[str] = []
    crawl_duration_seconds: float = 0.0
    pricing: list[PricingPlan] = []
    team: list[TeamMember] = []
    testimonials: list[Testimonial] = []
    tech_stack: TechStack = Field(default_factory=TechStack)
    brand_voice: BrandVoice = Field(default_factory=BrandVoice)
    business_type: str = ""
    founded_year: str = ""
    employee_count: str = ""
    headquarters: str = ""
    client_logos: list[ClientLogo] = []
    case_studies: list[CaseStudy] = []
    media_mentions: list[MediaMention] = []
    ctas: list[CTAButton] = []
    lead_magnets: list[LeadMagnet] = []
    industry: IndustryInfo = Field(default_factory=IndustryInfo)
