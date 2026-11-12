"""How well a score orders charts against tournament tiers."""
from collections import defaultdict


def pairwise(tiers, scores):
    """Share of cross-tier pairs the score orders the same way as the tiers. 0.5 = coin flip."""
    right = total = 0.0
    for i in range(len(tiers)):
        for j in range(i + 1, len(tiers)):
            if tiers[i] == tiers[j]:
                continue
            total += 1
            if scores[i] == scores[j]:
                right += 0.5
            else:
                right += (tiers[i] < tiers[j]) == (scores[i] < scores[j])
    return right / total if total else float('nan')


def tier_accuracy(labels, score):
    """Pairwise accuracy within each tournament, weighted by its size.
    labels: [(dmt.Label, md5)]; score: md5 -> value."""
    groups = defaultdict(list)
    for lab, md5 in labels:
        if md5 in score:
            groups[lab.group].append((lab.tier, score[md5]))
    n = sum(map(len, groups.values()))
    return sum(pairwise(*zip(*v)) * len(v) for v in groups.values()) / n


def community_accuracy(pairs, score):
    """Share of community (harder, easier) pairs the score orders the same way, and the pairs it
    gets wrong. pairs: [(claim, harder md5, easier md5)]; score: md5 -> value."""
    used = [(c, h, e) for c, h, e in pairs if h in score and e in score]
    wrong = [p for p in used if score[p[1]] <= score[p[2]]]
    return (1 - len(wrong) / len(used) if used else float('nan')), wrong
