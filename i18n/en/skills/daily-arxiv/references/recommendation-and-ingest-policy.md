# Recommendation policy

Rank only previously unknown papers. Ground every rationale in the supplied arXiv metadata, wiki profile, Semantic Scholar, or DeepXiv evidence. Allowed decisions are `strong_recommend`, `maybe`, and `skip`. The daily feed is notification-only: it never downloads a paper into user data, invokes the ingest skill, or modifies wiki state.
