export const APP_CONFIG = {
  name: 'FreshGuard',
  tagline: 'Trust the answer. Verify its freshness.',
  description: 'Real-time freshness verification for LLM responses with Tavily-powered evidence and Bifrost semantic cache protection.',
  github: 'https://github.com/kamalsolanki143/FreshGuard',
  email: 'contact@freshguard.ai',
  ctaText: 'Deploy Plugin',
  version: '1.0.0',
};

export interface FAQItem {
  question: string;
  answer: string;
}

export const FAQ: FAQItem[] = [
  {
    question: 'How does FreshGuard intercept LLM responses?',
    answer:
      'FreshGuard deploys as a native Go plugin directly inside the Bifrost gateway. Using the PreLLMHook and PostLLMHook lifecycle boundaries, it inspects incoming prompts and outgoing model completions to identify temporal claims before they are cached or returned to users.',
  },
  {
    question: 'Which claim categories does FreshGuard verify in the MVP?',
    answer:
      'The initial release supports three high-risk categories: (1) Pricing and subscription tiers, (2) Software and API version specifications, and (3) Executive and company leadership changes. Outdated claims in these categories are common due to model training cutoff limits.',
  },
  {
    question: 'How does FreshGuard prevent semantic cache poisoning?',
    answer:
      'Bifrost semantic caching can inadvertently serve stale responses for semantically equivalent queries. FreshGuard tags cached responses with deterministic TTL freshness policies. On cache hits, FreshGuard validates whether the verification metadata is still fresh, re-verifying or invalidating stale entries through Bifrost’s cache eviction API.',
  },
  {
    question: 'What happens if the Tavily search service is unreachable?',
    answer:
      'FreshGuard enforces configurable fail-open and fail-closed policies. In fail-open mode, the original model response is delivered with an explicit "unverified" status and freshness warning. In fail-closed mode, unverified time-sensitive claims are safely rejected.',
  },
  {
    question: 'Can FreshGuard run with local models or other gateways?',
    answer:
      'Yes. While FreshGuard is optimized for the Bifrost gateway, its Python verification engine exposes standard REST APIs (/v1/verifications) that can be integrated with LangChain, LlamaIndex, vLLM, or custom AI agent pipelines.',
  },
];
