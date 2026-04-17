# asr-eval-lib

`asr-eval-lib` ist eine Python-Library fuer ASR-Evaluation mit SCTK/SCLITE.
Sie erzeugt TRN-Dateien, wendet profilierte GLM-Regeln ueber `csrfilt.sh` an
und berechnet anschliessend die Fehlermaße mit `sclite`.

Unterstuetzt sind:

- orthografische Transkription fuer Deutsch und Englisch: WER und CER
- Transliteration fuer Deutsch und Englisch: WER und CER mit getrennten GLM-Regeln
- phonemische Transkription fuer Deutsch und Englisch: PER fuer `ipa`, `sampa`, `xsampa`
  und eigene Notationen mit eigener GLM-Datei

## Voraussetzung

Die Runtime erwartet SCTK-Tools im `PATH` oder explizit ueber Pfade:

- `sclite`
- `csrfilt.sh` oder `csrfilt`

Beide Tools sind Teil von SCTK. Die Library selbst bringt keine SCTK-Binaries mit.

## Installation

```bash
pip install -e .
```

Fuer lokale Entwicklung:

```bash
pip install -e ".[dev]"
```

## Deutsches ORT

Deutsch ORT steht hier fuer orthografische Transkription. Das Profil
`orthographic_profile("de")` nutzt die eingebaute Datei
`glm/de/orthographic.glm`, normalisiert Text fuer orthografisches Scoring und
berechnet standardmaessig WER und CER.

```python
from asr_eval_lib import ScliteEvaluator, orthographic_profile

profile = orthographic_profile("de")
result = ScliteEvaluator().evaluate(
    references={"utt1": "Die Straße ist schön."},
    hypotheses={"utt1": "Die Strasse schön"},
    profile=profile,
)

print(result.scores["wer"].rate)
print(result.scores["cer"].rate)
```

Die Normalisierung faltet unter anderem Gross-/Kleinschreibung und
orthografische Unicode-Varianten. Im Beispiel wird `Straße` vor dem Scoring zu
`strasse`. Fuer CER werden Leerzeichen standardmaessig nicht als Zeichenfehler
gezaehlt.

## GLM-Kompositionen

Optionale GLM-Komponenten koennen pro Evaluierung aktiviert oder entfernt
werden. Die Profil-Basis-GLM bleibt dabei aktiv; die Komponenten werden fuer den
SCTK-Filterlauf in eine temporaere `composed.glm` geschrieben.

```python
from asr_eval_lib import (
    ScliteEvaluator,
    available_glm_components,
    orthographic_profile,
)

profile = orthographic_profile("de")
print(available_glm_components(profile))
# ("dates", "numbers")

result = ScliteEvaluator().evaluate(
    references={"utt1": "3. März"},
    hypotheses={"utt1": "dritter März"},
    profile=profile,
    glm_components=["dates", "numbers"],
)
```

Fuer deutsches ORT sind in v1 die Starter-Komponenten `numbers` und `dates`
enthalten. Sie normalisieren auf interne Tokens wie `num_3` und `date_03_03`,
damit Varianten wie `3. März`, `dritter März` und `03.03` fuer WER und CER
gleich behandelt werden. Fuer produktive Korpora sollten projektspezifische
Regeln ueber `extra_glm_paths=[...]` ergaenzt werden.

Einzelne Komponenten koennen aus einer Auswahl entfernt werden:

```python
result = ScliteEvaluator().evaluate(
    references=refs,
    hypotheses=hyps,
    profile=profile,
    glm_components=["dates", "numbers"],
    exclude_glm_components=["numbers"],
)
```

## Allgemeines Beispiel

```python
from asr_eval_lib import ScliteEvaluator, orthographic_profile

profile = orthographic_profile("de")
evaluator = ScliteEvaluator()

result = evaluator.evaluate(
    references={"utt1": "Das ist ein Test."},
    hypotheses={"utt1": "Das ist Test"},
    profile=profile,
)

print(result.scores["wer"].rate)
print(result.scores["cer"].rate)
```

Phonemische Auswertung:

```python
from asr_eval_lib import ScliteEvaluator, phonetic_profile

profile = phonetic_profile("en", notation="ipa")
result = ScliteEvaluator().evaluate(
    references={"utt1": "h ə l oʊ"},
    hypotheses={"utt1": "h ɛ l oʊ"},
    profile=profile,
)

print(result.scores["per"].rate)
```

Eigene Lautschrift mit eigener GLM-Datei:

```python
from asr_eval_lib import ScliteEvaluator, custom_phonetic_profile

profile = custom_phonetic_profile(
    language="de",
    notation="my_phone_set",
    glm_path="/path/to/my_phone_set.glm",
)

result = ScliteEvaluator().evaluate(
    references={"utt1": "x a n"},
    hypotheses={"utt1": "x a m"},
    profile=profile,
)
```

## Hinweise zum Ablauf

SCTK wendet GLM-Regeln nicht direkt in `sclite` an. Die uebliche SCTK-Pipeline
filtert Referenz und Hypothese zuerst mit `csrfilt.sh` und scored danach mit
`sclite`. Genau diese Trennung bildet die Library ab.

Fuer CER werden die gefilterten Transkripte in Unicode-Zeichen-Token zerlegt und
dann als TRN-Dateien durch `sclite` ausgerichtet. Leerzeichen werden standardmaessig
nicht als Zeichenfehler gezaehlt.

Fuer phonemische Profile ist whitespace-separierte Eingabe die robusteste Form.
Wenn keine Leerzeichen vorhanden sind, nutzt die Library einfache Notations-Tokenizer
fuer IPA/SAMPA/X-SAMPA; fuer produktive Evaluationen sollten projektspezifische
Tokenisierung und GLM-Regeln explizit gepflegt werden.

## Tests

```bash
PYTHONDONTWRITEBYTECODE=1 pytest -q -p no:cacheprovider
```
