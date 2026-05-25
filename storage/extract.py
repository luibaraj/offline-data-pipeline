import config
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate


class JDExtraction(BaseModel):
    qualifications: list[str]
    responsibilities: list[str]


_SYSTEM_PROMPT = """\
You are a precise information extractor. Given a job description, extract two lists:
- qualifications: required or preferred skills, education, certifications, and experience the candidate must have
- responsibilities: tasks, duties, and day-to-day work the candidate will perform in the role

Rules:
- Each item should be a single, complete sentence or phrase
- Do not merge qualifications with responsibilities
- Do not include company culture or benefits in either list
- Return only what is explicitly stated in the job description

--- EXAMPLE 1 (bullet-heavy) ---
Job Description:
Responsibilities:
• Design and implement machine learning pipelines
• Collaborate with data engineers to build feature stores
• Deploy models to production using Kubernetes

Requirements:
• 3+ years of experience with Python and ML frameworks (PyTorch, TensorFlow)
• Experience with distributed training
• BS/MS in Computer Science or related field

Output:
{{
  "qualifications": [
    "3+ years of experience with Python and ML frameworks (PyTorch, TensorFlow)",
    "Experience with distributed training",
    "BS/MS in Computer Science or related field"
  ],
  "responsibilities": [
    "Design and implement machine learning pipelines",
    "Collaborate with data engineers to build feature stores",
    "Deploy models to production using Kubernetes"
  ]
}}

--- EXAMPLE 2 (paragraph-form) ---
Job Description:
We are looking for a Data Scientist to join our team. You will analyze large datasets to surface business insights and build predictive models. You will also present findings to senior stakeholders. The ideal candidate holds a PhD or MS in Statistics, Mathematics, or a related quantitative field, has strong proficiency in R or Python, and has at least two years of industry experience working with structured and unstructured data.

Output:
{{
  "qualifications": [
    "PhD or MS in Statistics, Mathematics, or a related quantitative field",
    "Strong proficiency in R or Python",
    "At least two years of industry experience working with structured and unstructured data"
  ],
  "responsibilities": [
    "Analyze large datasets to surface business insights",
    "Build predictive models",
    "Present findings to senior stakeholders"
  ]
}}

--- EXAMPLE 3 (hybrid: paragraph intro, mixed bullet sections) ---
Job Description:
As a Senior ML Engineer you will own the full model lifecycle at our company.

What you'll do:
- Lead research into new model architectures for NLP tasks
- Mentor junior engineers and conduct code reviews
- Partner with product to define model evaluation metrics

What we're looking for:
5+ years of hands-on ML engineering experience. Familiarity with transformer architectures is required. You should be comfortable with cloud infrastructure (AWS or GCP) and have experience shipping models to production at scale. A Bachelor's degree in a technical field is the minimum requirement.

Output:
{{
  "qualifications": [
    "5+ years of hands-on ML engineering experience",
    "Familiarity with transformer architectures",
    "Comfortable with cloud infrastructure (AWS or GCP)",
    "Experience shipping models to production at scale",
    "Bachelor's degree in a technical field"
  ],
  "responsibilities": [
    "Lead research into new model architectures for NLP tasks",
    "Mentor junior engineers and conduct code reviews",
    "Partner with product to define model evaluation metrics"
  ]
}}
"""

_prompt = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM_PROMPT),
    ("human", "Job Description:\n{description}"),
])

_llm = ChatOpenAI(
    model="deepseek/deepseek-chat-v3-0324",
    base_url=config.OPENROUTER_BASE_URL,
    api_key=config.OPENROUTER_API_KEY,
)

_chain = (_prompt | _llm.with_structured_output(JDExtraction)).with_retry(
    stop_after_attempt=3,
    wait_exponential_jitter=True,
)


def extract_jd_fields(description_clean: str) -> JDExtraction:
    result = _chain.invoke({"description": description_clean})
    if not result.qualifications and not result.responsibilities:
        result = _chain.invoke({"description": description_clean})
    return result
