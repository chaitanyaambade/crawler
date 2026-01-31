export interface CrawlRequest {
  url: string;
  client_name: string;
  industry: string;
}

export interface StepInfo {
  status: "pending" | "in_progress" | "complete" | "failed";
  detail: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface CrawlStatus {
  job_id: string;
  status: string;
  steps: Record<string, StepInfo>;
}

export interface BrandInfo {
  dominant_color: string;
  palette: string[];
  fonts: string[];
  logo_url: string;
  favicon_url: string;
  og_image: string;
}

export interface ContactInfo {
  emails: string[];
  phones: string[];
  addresses: string[];
}

export interface SocialLinks {
  instagram: string;
  twitter: string;
  linkedin: string;
  facebook: string;
  youtube: string;
  github: string;
  tiktok: string;
  pinterest: string;
  medium: string;
  discord: string;
  slack: string;
  telegram: string;
}

export interface ProductItem {
  name: string;
  description: string;
  image_url: string;
  price: string;
  category: string;
}

export interface CategoryItem {
  name: string;
  url: string;
  subcategories: CategoryItem[];
}

export interface BrandVoice {
  tone: string;
  formality: string;
  person: string;
  personality: string[];
}

export interface MetadataInfo {
  title: string;
  description: string;
  keywords: string[];
  structured_data: Record<string, unknown>;
}

export interface TeamMember {
  name: string;
  role: string;
  photo_url: string;
  linkedin_url: string;
}

export interface PricingPlan {
  name: string;
  price: string;
  billing_period: string;
  features: string[];
  is_highlighted: boolean;
}

export interface Testimonial {
  quote: string;
  author_name: string;
  author_company: string;
  author_role: string;
  rating: number | null;
}

export interface TechStack {
  frameworks: string[];
  cms: string[];
  analytics: string[];
  cdn: string[];
  other: string[];
}

export interface ClientLogo {
  name: string;
  logo_url: string;
}

export interface CaseStudy {
  title: string;
  summary: string;
  client_name: string;
  url: string;
  metrics: string[];
}

export interface MediaMention {
  title: string;
  source: string;
  url: string;
  date: string;
}

export interface CTAButton {
  text: string;
  url: string;
  location: string;
}

export interface LeadMagnet {
  type: string;
  title: string;
  description: string;
  url: string;
}

export interface IndustryInfo {
  primary: string;
  secondary: string;
  confidence: number;
}

export interface CrawlResult {
  company_name: string;
  tagline: string;
  about: string;
  brand: BrandInfo;
  metadata: MetadataInfo;
  social_links: SocialLinks;
  products: ProductItem[];
  categories: CategoryItem[];
  features: string[];
  images: string[];
  contact: ContactInfo;
  pages_crawled: string[];
  crawl_duration_seconds: number;
  pricing: PricingPlan[];
  team: TeamMember[];
  testimonials: Testimonial[];
  tech_stack: TechStack;
  brand_voice: BrandVoice;
  business_type: string;
  founded_year: string;
  employee_count: string;
  headquarters: string;
  client_logos: ClientLogo[];
  case_studies: CaseStudy[];
  media_mentions: MediaMention[];
  ctas: CTAButton[];
  lead_magnets: LeadMagnet[];
  industry: IndustryInfo;
}

export const STEP_LABELS: Record<string, string> = {
  discovering: "Discover pages",
  crawling: "Crawl website pages",
  extracting: "Extract text & metadata",
  colors: "Extract brand colors",
  images: "Extract images & logos",
  complete: "Finalize results",
};

export const STEP_ORDER = [
  "discovering",
  "crawling",
  "extracting",
  "colors",
  "images",
  "complete",
];
