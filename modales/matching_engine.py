
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def calculate_similarity(resume_text, job_description):

    documents = [resume_text, job_description]

    vectorizer = TfidfVectorizer(
        stop_words="english"
    )

    matrix = vectorizer.fit_transform(documents)

    similarity = cosine_similarity(
        matrix[0:1],
        matrix[1:2]
    )[0][0]

    return round(similarity * 100, 2)


def match_candidate(
    resume_skills,
    required_skills,
    experience_score,
    resume_text,
    job_description
):

    resume_set = set(resume_skills)
    required_set = set(required_skills)

    matched = resume_set.intersection(required_set)

    if required_set:

        skill_score = (
            len(matched) / len(required_set)
        ) * 100

    else:
        skill_score = 0

    similarity_score = calculate_similarity(
        resume_text,
        job_description
    )

    overall_score = (
        skill_score * 0.70
        + experience_score * 0.20
        + similarity_score * 0.10
    )

    return {
        "matched_skills": sorted(matched),

        "missing_skills": sorted(
            required_set - resume_set
        ),

        "skill_score": round(skill_score, 2),

        "experience_score": experience_score,

        "similarity_score": similarity_score,

        "overall_score": round(overall_score, 2)
    }
