# Samples

Three small biopharma cases for trying groundlint. Each folder has:

- `source.md`: a short excerpt from an FDA drug label
- `answer.md`: a hand-written answer in the style of an LLM reply
- `expected.json`: the expected verdict for every claim in the answer

Each answer contains deliberately planted errors (a changed number, a reversed finding, an overextended population and a claim with no source) alongside some correct claims. Don't use these answers as drug information.

All three sources were retrieved on 2026-11-08.

## What the verdicts mean

groundlint judges each claim only against the sources it's given:

- `unsupported` means the claim is **not established by the given sources**. It does not mean the claim is false. The "no source" claims here are a deliberate example: the full drug labels likely cover topics such as food or grapefruit juice, but these short excerpts don't, so the claims are `unsupported`.
- `contradicted` means the given sources conflict with the claim.

## Cases

### apixaban-dosing

- Drug and topic: ELIQUIS (apixaban), dosing (Section 2 Dosage and Administration)
- Source: https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=e9481622-7cc6-418a-acb6-c5450daae9b0
- Text retrieved from openFDA: https://api.fda.gov/drug/label.json?search=set_id:"e9481622-7cc6-418a-acb6-c5450daae9b0" (label effective date 2025-04-17)
- Claims: 8 (3 supported, 1 changed number, 1 reversed finding, 1 overextended population, 1 no source)

### simvastatin-contraindications-interactions

- Drug and topic: ZOCOR (simvastatin, Organon LLC), contraindications and dosage limits due to drug interactions (Sections 4, 2.1 and 2.5)
- Source: https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=8f55d5de-5a4f-4a39-8c84-c53976dd6af9
- Text retrieved from openFDA: https://api.fda.gov/drug/label.json?search=set_id:"8f55d5de-5a4f-4a39-8c84-c53976dd6af9" (label effective date 2025-03-28)
- Claims: 7 (3 supported, 1 changed number, 1 reversed finding, 1 overextended population, 1 no source)

### empagliflozin-cv-outcomes

- Drug and topic: JARDIANCE (empagliflozin, Boehringer Ingelheim), trial outcome: EMPA-REG OUTCOME (Section 14.3 Clinical Studies)
- Source: https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=faf3dd6a-9cd0-39c2-0d2e-232cb3f67565
- Text retrieved from openFDA: https://api.fda.gov/drug/label.json?search=set_id:"faf3dd6a-9cd0-39c2-0d2e-232cb3f67565" (label effective date 2026-01-30)
- Claims: 7 (3 supported, 1 changed number, 1 reversed finding, 1 overextended population, 1 no source)

## License

All three excerpts come from FDA drug labeling (Structured Product Labeling submitted to FDA), retrieved through openFDA, with the matching DailyMed page linked above. Evidence checked on 2026-11-08:

- openFDA license, https://open.fda.gov/license/: "unless otherwise noted, the content, data, documentation, code, and related materials on openFDA is public domain and made available with a Creative Commons CC0 1.0 Universal dedication." The only exemption listed is GMDN device nomenclature data, which these samples don't use. Drug labeling isn't listed as an exemption.
- FDA website policies, https://www.fda.gov/about-fda/about-website/website-policies: "Unless otherwise noted, the contents of the FDA website (www.fda.gov) — both text and graphics — are not copyrighted. They are in the public domain and may be republished, reprinted and otherwise used freely by anyone." Credit to FDA is appreciated but not required, and FDA recommends listing the copy date and a link back, which this file does.
- openFDA drug label API page, https://open.fda.gov/apis/drug/label/: the data comes from FDA SPL files, "its content has neither been altered nor verified by FDA", and it "may not be the labeling on currently distributed products."
- NLM web policies (which DailyMed's Copyright link points to), https://www.nlm.nih.gov/web_policies.html: government works may be freely used, but NLM sites can include non-government content that may be copyrighted, and NLM "cannot guarantee the copyright status for any item." DailyMed doesn't state a separate license for label text.

Conclusion: we rely on the openFDA CC0 dedication and FDA's public-domain statement. The labels are written by the manufacturers, so some copyright doubt remains. Each excerpt is a short factual passage of about 200 to 300 words, so it would also be a modest, attributed use. ELIQUIS, ZOCOR and JARDIANCE are trademarks of their owners. They're used here only to identify the products, and nothing here implies endorsement by FDA or the manufacturers.

## How the excerpts were edited

The excerpts keep the label's original sentences. The only changes are formatting:

- Bracketed cross-references such as "[see Warnings and Precautions (5.2)]" and "(see Table 15 and Figures 5 and 6)" were removed.
- Bulleted lists became plain sentences. In the apixaban case, the three bulleted dose-reduction criteria are joined with commas.
- Subsection headings are kept as plain lines. In the simvastatin case, a colon follows each "Patients taking ..." heading.
- Sentences outside the chosen topic were left out.
