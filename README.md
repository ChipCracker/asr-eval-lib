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

## Beispiel

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
