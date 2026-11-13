import tempfile
import unittest
from pathlib import Path

from drumchotic.fit.metrics import community_accuracy
from drumchotic.sources import community

CLAIMS = """# comment
@ Car Bomb | someone, somewhere
Hard One; Hard Two
Easy (B)
"""


class CommunityTests(unittest.TestCase):
    def setUp(self):
        self.path = Path(tempfile.mkdtemp()) / 'claims.txt'
        self.path.write_text(CLAIMS)

    def test_claims_parse_into_ordered_groups(self):
        [c] = community.load(self.path)
        self.assertEqual((c.artist, c.source), ('Car Bomb', 'someone, somewhere'))
        self.assertEqual(c.groups, (('Hard One', 'Hard Two'), ('Easy (B)',)))

    def test_every_harder_song_pairs_with_every_easier_one(self):
        titles = {'a': 'Car Bomb - Hard One', 'b': 'Car Bomb - Hard Two', 'c': 'Car Bomb - easy', 'd': 'Other - Hard One'}
        pairs, missing = community.pairs(community.load(self.path), titles)
        self.assertEqual(sorted((h, e) for _, h, e in pairs), [('a', 'c'), ('b', 'c')])
        self.assertEqual(missing, [])

    def test_accuracy_counts_wrong_orderings(self):
        pairs = [(None, 'a', 'c'), (None, 'b', 'c')]
        acc, wrong = community_accuracy(pairs, {'a': 2.0, 'b': 0.5, 'c': 1.0})
        self.assertEqual(acc, 0.5)
        self.assertEqual([p[1] for p in wrong], ['b'])


if __name__ == '__main__':
    unittest.main()
