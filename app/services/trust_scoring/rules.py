# Trust Scoring Weights (must sum to 1.0)
WEIGHT_SOURCE_RELIABILITY = 0.30
WEIGHT_CLAIM_ACCURACY = 0.40
WEIGHT_CORROBORATION = 0.15
WEIGHT_RECENCY = 0.15

# Grade Boundaries
GRADE_A_THRESHOLD = 85.0
GRADE_B_THRESHOLD = 70.0
GRADE_C_THRESHOLD = 50.0

GRADE_DESCRIPTIONS = {
    "A": "Highly Trustworthy — Rigorous attribution, high claim accuracy, and corroborated by accredited sources.",
    "B": "Likely Authentic — Verifiable statements and credible sources with minor unconfirmed details.",
    "C": "Questionable — Insufficient independent corroboration, ambiguous claims, or sensationalist tone.",
    "D": "Disputed / Unreliable — Multiple false or misleading claims detected, or unknown unverified publisher.",
}

# Known accredited news and scientific domains
ACCREDITED_DOMAINS = {
    "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk",
    "nature.com", "sciencemag.org", "who.int", "cdc.gov",
    "theguardian.com", "nytimes.com", "wsj.com", "bloomberg.com",
    "npr.org", "pbs.org", "washingtonpost.com", "ft.com"
}
