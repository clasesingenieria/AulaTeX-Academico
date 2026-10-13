from collections import Counter

def fuse_responses(responses:list[str]) -> str:
    cleaned=[r.strip() for r in responses if r and r.strip()]
    counts=Counter(cleaned)
    ranked=[text for text,_ in counts.most_common()]
    return "\n\n---FUSION---\n\n".join(ranked)
