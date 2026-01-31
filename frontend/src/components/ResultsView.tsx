import type { CrawlResult } from "../types";

interface Props {
  result: CrawlResult;
  onReset: () => void;
}

export default function ResultsView({ result, onReset }: Props) {
  const hasTechStack =
    result.tech_stack &&
    (result.tech_stack.frameworks.length > 0 ||
      result.tech_stack.cms.length > 0 ||
      result.tech_stack.analytics.length > 0 ||
      result.tech_stack.cdn.length > 0 ||
      result.tech_stack.other.length > 0);

  return (
    <div className="max-w-3xl mx-auto mt-8 space-y-6">
      {/* Header */}
      <div className="bg-white rounded-xl shadow-lg p-8">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {result.company_name}
            </h1>
            {result.tagline && (
              <p className="text-gray-500 mt-1">{result.tagline}</p>
            )}
          </div>
          {result.brand.logo_url && (
            <img
              src={result.brand.logo_url}
              alt="Logo"
              className="h-12 object-contain"
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = "none";
              }}
            />
          )}
        </div>
        {result.business_type && (
          <span className="inline-block px-2 py-0.5 bg-indigo-100 text-indigo-700 text-xs rounded-full mt-1">
            {result.business_type.replace("_", " ")}
          </span>
        )}
        {result.about && (
          <p className="text-gray-600 text-sm leading-relaxed mt-2">
            {result.about}
          </p>
        )}
        {/* Company metadata */}
        {(result.founded_year || result.employee_count || result.headquarters) && (
          <div className="flex flex-wrap gap-4 mt-3 text-xs text-gray-500">
            {result.founded_year && <span>Founded: {result.founded_year}</span>}
            {result.employee_count && <span>Employees: {result.employee_count}</span>}
            {result.headquarters && <span>HQ: {result.headquarters}</span>}
          </div>
        )}
        <p className="text-xs text-gray-400 mt-3">
          Crawled {result.pages_crawled.length} pages in{" "}
          {result.crawl_duration_seconds}s
        </p>
      </div>

      {/* Brand Colors */}
      {result.brand.palette.length > 0 && (
        <Section title="Brand Colors">
          <div className="flex gap-3 flex-wrap">
            {result.brand.palette.map((color, i) => (
              <div key={i} className="text-center">
                <div
                  className="w-14 h-14 rounded-lg shadow-sm border border-gray-200"
                  style={{ backgroundColor: color }}
                />
                <span className="text-xs text-gray-500 mt-1 block">
                  {color}
                </span>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Brand Fonts */}
      {result.brand.fonts && result.brand.fonts.length > 0 && (
        <Section title="Brand Fonts">
          <div className="flex flex-wrap gap-2">
            {result.brand.fonts.map((font, i) => (
              <span
                key={i}
                className="px-3 py-1.5 bg-gray-100 rounded-full text-sm text-gray-700"
              >
                {font}
              </span>
            ))}
          </div>
        </Section>
      )}

      {/* Brand Voice */}
      {result.brand_voice &&
        (result.brand_voice.tone ||
          result.brand_voice.formality ||
          result.brand_voice.personality?.length > 0) && (
          <Section title="Brand Voice">
            <div className="flex flex-wrap gap-4 text-sm text-gray-700">
              {result.brand_voice.tone && (
                <div>
                  <span className="text-gray-400 text-xs block">Tone</span>
                  <span className="capitalize">{result.brand_voice.tone}</span>
                </div>
              )}
              {result.brand_voice.formality && (
                <div>
                  <span className="text-gray-400 text-xs block">Formality</span>
                  <span className="capitalize">{result.brand_voice.formality}</span>
                </div>
              )}
              {result.brand_voice.person && (
                <div>
                  <span className="text-gray-400 text-xs block">Voice</span>
                  <span className="capitalize">
                    {result.brand_voice.person.replace("_", " ")}
                  </span>
                </div>
              )}
            </div>
            {result.brand_voice.personality &&
              result.brand_voice.personality.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-3">
                  {result.brand_voice.personality.map((trait, i) => (
                    <span
                      key={i}
                      className="px-2 py-1 bg-purple-50 text-purple-700 rounded text-xs capitalize"
                    >
                      {trait}
                    </span>
                  ))}
                </div>
              )}
          </Section>
        )}

      {/* Metadata */}
      <Section title="Metadata">
        <dl className="grid grid-cols-1 gap-2 text-sm">
          {result.metadata.title && (
            <Row label="Title" value={result.metadata.title} />
          )}
          {result.metadata.description && (
            <Row label="Description" value={result.metadata.description} />
          )}
          {result.metadata.keywords.length > 0 && (
            <Row label="Keywords" value={result.metadata.keywords.join(", ")} />
          )}
        </dl>
      </Section>

      {/* Social Links */}
      {Object.values(result.social_links).some(Boolean) && (
        <Section title="Social Links">
          <div className="flex flex-wrap gap-2">
            {Object.entries(result.social_links).map(
              ([platform, url]) =>
                url && (
                  <a
                    key={platform}
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-full text-sm text-gray-700 capitalize transition-colors"
                  >
                    {platform}
                  </a>
                )
            )}
          </div>
        </Section>
      )}

      {/* Product Categories (e-commerce sites) */}
      {result.categories && result.categories.length > 0 && (
        <Section title={`Product Categories (${result.categories.length})`}>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {result.categories.map((cat, i) => (
              <div
                key={i}
                className="border border-gray-200 rounded-lg p-3"
              >
                <h4 className="font-medium text-gray-800 text-sm">
                  {cat.url ? (
                    <a
                      href={cat.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="hover:text-blue-600 transition-colors"
                    >
                      {cat.name}
                    </a>
                  ) : (
                    cat.name
                  )}
                </h4>
                {cat.subcategories && cat.subcategories.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {cat.subcategories.slice(0, 8).map((sub, j) => (
                      <span
                        key={j}
                        className="px-2 py-0.5 bg-gray-100 rounded text-xs text-gray-600"
                      >
                        {sub.url ? (
                          <a
                            href={sub.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="hover:text-blue-600 transition-colors"
                          >
                            {sub.name}
                          </a>
                        ) : (
                          sub.name
                        )}
                      </span>
                    ))}
                    {cat.subcategories.length > 8 && (
                      <span className="text-xs text-gray-400">
                        +{cat.subcategories.length - 8} more
                      </span>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Products (hidden when categories are present — ecommerce sites) */}
      {result.products.length > 0 &&
        !(result.categories && result.categories.length > 0) && (
        <Section title={`Products / Services (${result.products.length})`}>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {result.products.map((p, i) => (
              <div
                key={i}
                className="border border-gray-200 rounded-lg p-3"
              >
                <div className="flex items-start justify-between gap-2">
                  <h4 className="font-medium text-gray-800 text-sm">
                    {p.name}
                  </h4>
                  {p.price && (
                    <span className="text-sm font-semibold text-green-700 whitespace-nowrap">
                      {p.price}
                    </span>
                  )}
                </div>
                {p.category && (
                  <span className="text-xs text-gray-400">{p.category}</span>
                )}
                {p.description && (
                  <p className="text-xs text-gray-500 mt-1 line-clamp-2">
                    {p.description}
                  </p>
                )}
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Features */}
      {result.features.length > 0 && (
        <Section title="Features">
          <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
            {result.features.map((f, i) => (
              <li key={i}>{f}</li>
            ))}
          </ul>
        </Section>
      )}

      {/* Pricing Plans */}
      {result.pricing && result.pricing.length > 0 && (
        <Section title={`Pricing Plans (${result.pricing.length})`}>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {result.pricing.map((plan, i) => (
              <div
                key={i}
                className={`border rounded-lg p-4 ${
                  plan.is_highlighted
                    ? "border-blue-500 bg-blue-50"
                    : "border-gray-200"
                }`}
              >
                <h4 className="font-semibold text-gray-800">{plan.name}</h4>
                {plan.price && (
                  <p className="text-lg font-bold text-gray-900 mt-1">
                    {plan.price}
                    {plan.billing_period && (
                      <span className="text-xs font-normal text-gray-500 ml-1">
                        /{plan.billing_period}
                      </span>
                    )}
                  </p>
                )}
                {plan.features.length > 0 && (
                  <ul className="mt-2 space-y-1">
                    {plan.features.slice(0, 6).map((f, j) => (
                      <li key={j} className="text-xs text-gray-600 flex items-start gap-1">
                        <span className="text-green-500 mt-0.5">&#10003;</span>
                        {f}
                      </li>
                    ))}
                    {plan.features.length > 6 && (
                      <li className="text-xs text-gray-400">
                        +{plan.features.length - 6} more
                      </li>
                    )}
                  </ul>
                )}
                {plan.is_highlighted && (
                  <span className="inline-block mt-2 text-xs bg-blue-500 text-white px-2 py-0.5 rounded-full">
                    Popular
                  </span>
                )}
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Team Members */}
      {result.team && result.team.length > 0 && (
        <Section title={`Team (${result.team.length})`}>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {result.team.map((member, i) => (
              <div key={i} className="text-center">
                {member.photo_url ? (
                  <img
                    src={member.photo_url}
                    alt={member.name}
                    className="w-16 h-16 rounded-full mx-auto object-cover border border-gray-200"
                    onError={(e) => {
                      (e.target as HTMLImageElement).style.display = "none";
                    }}
                  />
                ) : (
                  <div className="w-16 h-16 rounded-full mx-auto bg-gray-200 flex items-center justify-center">
                    <span className="text-gray-500 text-lg font-semibold">
                      {member.name.charAt(0)}
                    </span>
                  </div>
                )}
                <p className="text-sm font-medium text-gray-800 mt-2">
                  {member.linkedin_url ? (
                    <a
                      href={member.linkedin_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="hover:text-blue-600 transition-colors"
                    >
                      {member.name}
                    </a>
                  ) : (
                    member.name
                  )}
                </p>
                {member.role && (
                  <p className="text-xs text-gray-500">{member.role}</p>
                )}
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Testimonials */}
      {result.testimonials && result.testimonials.length > 0 && (
        <Section title={`Testimonials (${result.testimonials.length})`}>
          <div className="space-y-4">
            {result.testimonials.map((t, i) => (
              <div
                key={i}
                className="border border-gray-200 rounded-lg p-4 bg-gray-50"
              >
                <p className="text-sm text-gray-700 italic">"{t.quote}"</p>
                <div className="mt-2 flex items-center justify-between">
                  <div>
                    {t.author_name && (
                      <p className="text-sm font-medium text-gray-800">
                        {t.author_name}
                      </p>
                    )}
                    {(t.author_role || t.author_company) && (
                      <p className="text-xs text-gray-500">
                        {[t.author_role, t.author_company]
                          .filter(Boolean)
                          .join(" at ")}
                      </p>
                    )}
                  </div>
                  {t.rating != null && (
                    <div className="flex items-center gap-1">
                      <span className="text-yellow-500">&#9733;</span>
                      <span className="text-sm text-gray-600">
                        {t.rating}/5
                      </span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Industry Classification */}
      {result.industry && result.industry.primary && (
        <Section title="Industry Classification">
          <div className="flex flex-wrap gap-3 items-center">
            <span className="px-3 py-1.5 bg-indigo-100 text-indigo-800 rounded-full text-sm font-medium capitalize">
              {result.industry.primary.replace("_", " ")}
            </span>
            {result.industry.secondary && (
              <span className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-full text-sm capitalize">
                {result.industry.secondary.replace("_", " ")}
              </span>
            )}
            {result.industry.confidence > 0 && (
              <span className="text-xs text-gray-400">
                {Math.round(result.industry.confidence * 100)}% confidence
              </span>
            )}
          </div>
        </Section>
      )}

      {/* Client Logos */}
      {result.client_logos && result.client_logos.length > 0 && (
        <Section title={`Client Logos (${result.client_logos.length})`}>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {result.client_logos.map((logo, i) => (
              <div
                key={i}
                className="flex flex-col items-center gap-2 p-3 border border-gray-200 rounded-lg"
              >
                {logo.logo_url && (
                  <img
                    src={logo.logo_url}
                    alt={logo.name}
                    className="h-10 object-contain"
                    onError={(e) => {
                      (e.target as HTMLImageElement).style.display = "none";
                    }}
                  />
                )}
                <span className="text-xs text-gray-600 text-center">
                  {logo.name}
                </span>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* CTAs */}
      {result.ctas && result.ctas.length > 0 && (
        <Section title={`Call-to-Actions (${result.ctas.length})`}>
          <div className="space-y-2">
            {result.ctas.map((cta, i) => (
              <div
                key={i}
                className="flex items-center justify-between border border-gray-200 rounded-lg p-3"
              >
                <div>
                  <span className="text-sm font-medium text-gray-800">
                    {cta.text}
                  </span>
                  {cta.location && (
                    <span className="ml-2 px-2 py-0.5 bg-blue-50 text-blue-600 text-xs rounded-full capitalize">
                      {cta.location}
                    </span>
                  )}
                </div>
                {cta.url && (
                  <a
                    href={cta.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-blue-500 hover:text-blue-700 truncate max-w-[200px]"
                  >
                    {cta.url}
                  </a>
                )}
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Lead Magnets */}
      {result.lead_magnets && result.lead_magnets.length > 0 && (
        <Section title={`Lead Magnets (${result.lead_magnets.length})`}>
          <div className="space-y-3">
            {result.lead_magnets.map((magnet, i) => (
              <div
                key={i}
                className="border border-gray-200 rounded-lg p-4"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <span className="px-2 py-0.5 bg-green-50 text-green-700 text-xs rounded-full capitalize">
                      {magnet.type.replace("_", " ")}
                    </span>
                    {magnet.title && (
                      <h4 className="font-medium text-gray-800 text-sm mt-1">
                        {magnet.title}
                      </h4>
                    )}
                    {magnet.description && (
                      <p className="text-xs text-gray-500 mt-1 line-clamp-2">
                        {magnet.description}
                      </p>
                    )}
                  </div>
                  {magnet.url && (
                    <a
                      href={magnet.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-blue-500 hover:text-blue-700 shrink-0"
                    >
                      Link
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Case Studies */}
      {result.case_studies && result.case_studies.length > 0 && (
        <Section title={`Case Studies (${result.case_studies.length})`}>
          <div className="space-y-4">
            {result.case_studies.map((study, i) => (
              <div
                key={i}
                className="border border-gray-200 rounded-lg p-4"
              >
                <h4 className="font-medium text-gray-800 text-sm">
                  {study.url ? (
                    <a
                      href={study.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="hover:text-blue-600 transition-colors"
                    >
                      {study.title}
                    </a>
                  ) : (
                    study.title
                  )}
                </h4>
                {study.client_name && (
                  <p className="text-xs text-gray-400 mt-0.5">
                    Client: {study.client_name}
                  </p>
                )}
                {study.summary && (
                  <p className="text-xs text-gray-500 mt-1 line-clamp-3">
                    {study.summary}
                  </p>
                )}
                {study.metrics && study.metrics.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-2">
                    {study.metrics.map((metric, j) => (
                      <span
                        key={j}
                        className="px-2 py-0.5 bg-emerald-50 text-emerald-700 text-xs rounded"
                      >
                        {metric}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Media Mentions */}
      {result.media_mentions && result.media_mentions.length > 0 && (
        <Section title={`Media Mentions (${result.media_mentions.length})`}>
          <div className="space-y-2">
            {result.media_mentions.map((mention, i) => (
              <div
                key={i}
                className="flex items-center justify-between border border-gray-200 rounded-lg p-3"
              >
                <div>
                  <h4 className="text-sm font-medium text-gray-800">
                    {mention.url ? (
                      <a
                        href={mention.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="hover:text-blue-600 transition-colors"
                      >
                        {mention.title}
                      </a>
                    ) : (
                      mention.title
                    )}
                  </h4>
                  <div className="flex gap-2 mt-0.5">
                    {mention.source && (
                      <span className="text-xs text-gray-400">
                        {mention.source}
                      </span>
                    )}
                    {mention.date && (
                      <span className="text-xs text-gray-400">
                        {mention.date}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Tech Stack */}
      {hasTechStack && (
        <Section title="Tech Stack">
          <div className="space-y-3">
            {(
              [
                ["Frameworks", result.tech_stack.frameworks],
                ["CMS", result.tech_stack.cms],
                ["Analytics", result.tech_stack.analytics],
                ["CDN", result.tech_stack.cdn],
                ["Other", result.tech_stack.other],
              ] as [string, string[]][]
            ).map(
              ([label, items]) =>
                items.length > 0 && (
                  <div key={label}>
                    <p className="text-xs font-medium text-gray-500 mb-1">
                      {label}
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {items.map((tech, i) => (
                        <span
                          key={i}
                          className="px-2 py-1 bg-gray-100 rounded text-xs text-gray-700"
                        >
                          {tech}
                        </span>
                      ))}
                    </div>
                  </div>
                )
            )}
          </div>
        </Section>
      )}

      {/* Contact */}
      {(result.contact.emails.length > 0 ||
        result.contact.phones.length > 0 ||
        result.contact.addresses.length > 0) && (
        <Section title="Contact">
          <dl className="text-sm space-y-1">
            {result.contact.emails.map((email, i) => (
              <Row key={`email-${i}`} label="Email" value={email} />
            ))}
            {result.contact.phones.map((phone, i) => (
              <Row key={`phone-${i}`} label="Phone" value={phone} />
            ))}
            {result.contact.addresses.map((a, i) => (
              <Row key={`addr-${i}`} label="Address" value={a} />
            ))}
          </dl>
        </Section>
      )}

      {/* Images */}
      {result.images.length > 0 && (
        <Section title={`Images (${result.images.length})`}>
          <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
            {result.images.slice(0, 12).map((src, i) => (
              <img
                key={i}
                src={src}
                alt=""
                className="w-full h-24 object-cover rounded-lg border border-gray-200"
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = "none";
                }}
              />
            ))}
          </div>
        </Section>
      )}

      {/* Reset */}
      <div className="text-center pb-8">
        <button
          onClick={onReset}
          className="text-sm text-blue-600 hover:text-blue-800 underline"
        >
          Crawl another website
        </button>
      </div>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-white rounded-xl shadow-lg p-6">
      <h3 className="text-lg font-semibold text-gray-800 mb-3">{title}</h3>
      {children}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-2">
      <dt className="text-gray-400 font-medium min-w-[80px]">{label}</dt>
      <dd className="text-gray-700">{value}</dd>
    </div>
  );
}
