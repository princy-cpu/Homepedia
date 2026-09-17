import pytest

from homepedia.jobs.common import normalize_code_insee
from homepedia.nlp.sentiment import count_mentions, polarite_to_label


@pytest.mark.parametrize(
    "raw, expected",
    [
        (1004, "01004"),
        ("1004", "01004"),
        ("1004.0", "01004"),
        ("2a004", "2A004"),
        ("75112", "75056"),   # Paris 12e -> Paris
        ("69385", "69123"),   # Lyon 5e -> Lyon
        ("13208", "13055"),   # Marseille 8e -> Marseille
        ("abc", None),
        (None, None),
    ],
)
def test_normalize_code_insee(raw, expected):
    assert normalize_code_insee(raw) == expected


def test_arrondissement_conserve_si_demande():
    assert normalize_code_insee("75112", merge_plm=False) == "75112"


def test_count_mentions():
    texte = "Trop de bruit, des rats partout. Bruyant ? Non, juste du bruit."
    assert count_mentions(texte, ["bruit", "rats", "calme"]) == {"bruit": 2, "rats": 1}


@pytest.mark.parametrize("p, label", [(-1, "negatif"), (0, "neutre"), (0.5, "positif")])
def test_polarite_to_label(p, label):
    assert polarite_to_label(p) == label
