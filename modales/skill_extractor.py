
import re

SKILLS = [
    "python",
    "java",
    "javascript",
    "html",
    "css",
    "react",
    "flask",
    "django",
    "mysql",
    "mongodb",
    "machine learning",
    "deep learning",
    "data analysis",
    "artificial intelligence",
    "nlp",
    "sql",
    "excel",
    "power bi",
    "tensorflow",
    "pytorch",
    "scikit-learn",
    "git",
    "docker",
    "aws"
]


def extract_skills(text):

    text = text.lower()

    found_skills = []

    for skill in SKILLS:

        pattern = (
            r"(?<![a-z0-9+#])"
            + re.escape(skill)
            + r"(?![a-z0-9+#])"
        )

        if re.search(pattern, text):
            found_skills.append(skill)

    return sorted(set(found_skills))
