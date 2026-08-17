#!/usr/bin/env python3
"""Author the provisional sample question set for AusLawExam-Bench.

This is the single source of truth for the shipped sample items. It builds each
item, stamps a deterministic per-item canary (``make_canary(id)``), validates the
whole set (schema + jurisdiction + canary + dedup) via the ingest layer, and
writes ``data/questions/auslex.jsonl``.

STATUS: every item is PROVISIONAL — realistic exam-style questions written for
prototyping the harness, each flagged ``provisional: true`` and ``tier B``.
They require verification by a qualified Australian lawyer before external use.
Run:  python3 tools/author_samples.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from auslex.canary import make_canary  # noqa: E402
from auslex.ingest import validate_dataset  # noqa: E402
from auslex.schema import validate_item  # noqa: E402

PROV_AUTHOR = "auslex provisional sample set"
LAW_AS_AT = "2026-01-01"


def item(
    *,
    id: str,
    type: str,
    jurisdiction: list[str],
    area: str,
    topics: list[str],
    difficulty: str,
    marks: int,
    question_text: str,
    gold_answer: str,
    key_issues: list[str],
    authorities: list[dict],
    rubric: list[tuple[str, int]],
    tier: str = "B",
    mcq_options: list[str] | None = None,
    mcq_correct: int | None = None,
) -> dict:
    d: dict = {
        "id": id,
        "version": "0.1.0",
        "type": type,
        "jurisdiction": jurisdiction,
        "priestley_area": area,
        "topics": topics,
        "difficulty": difficulty,
        "marks": marks,
        "question_text": question_text,
        "gold_answer": gold_answer,
        "key_issues": key_issues,
        "required_authorities": authorities,
        "rubric": [{"criterion": c, "max": m} for c, m in rubric],
        "law_as_at": LAW_AS_AT,
        "provenance": {"tier": tier, "author": PROV_AUTHOR, "provisional": True},
        "verification": {"second_pass": False},
        "canary": make_canary(id),
    }
    if type == "mcq":
        d["mcq_options"] = mcq_options
        d["mcq_correct"] = mcq_correct
    return d


ITEMS: list[dict] = [
    # 1 — contract / hypothetical / pass
    item(
        id="auslex-2026-0001", type="hypothetical",
        jurisdiction=["NSW"], area="contract",
        topics=["promissory estoppel", "reliance", "pre-contractual reliance"],
        difficulty="pass", marks=15,
        question_text=(
            "B, a land developer, orally agreed to sell its suburban retail land to A, a "
            "supermarket chain. Relying on that agreement, A began demolition and site works. "
            "The parties never reduced the deal to a signed contract, and B subsequently sold "
            "the land to a third party. Advise A on any claim against B and the elements A must "
            "establish."
        ),
        gold_answer=(
            "A's realistic claim is the equitable doctrine of promissory estoppel, as developed "
            "in Waltons Stores (Interstate) Ltd v Maher (1988) 164 CLR 387. There the High Court "
            "held that a party who knowingly allows another to act to its detriment in reliance on "
            "a clear and unequivocal representation may be estopped from repudiating the basis of "
            "that reliance, with a remedy tailored to the prejudice. To succeed, A must show (1) a "
            "clear and unambiguous representation or conduct from B that the land was to be sold to "
            "A, (2) that A actually relied on it to its detriment (the demolition and site works), "
            "(3) that B knew or ought to have known A would rely, and (4) that it would be "
            "unconscionable for B to resile. The remedy is not specific performance but compensation "
            "for the detriment suffered, so A should quantify demolition, site costs and lost position."
        ),
        key_issues=[
            "promissory estoppel", "reliance and detriment",
            "clear and unequivocal representation", "knowledge of reliance",
            "unconscionability of repudiating",
        ],
        authorities=[{"kind": "case",
                      "cite": "Waltons Stores (Interstate) Ltd v Maher (1988) 164 CLR 387"}],
        rubric=[("issue_identification", 3), ("rule", 4), ("application", 5),
                ("conclusion", 3)],
    ),
    # 2 — contract / short_answer / credit
    item(
        id="auslex-2026-0002", type="short_answer",
        jurisdiction=["NSW"], area="contract",
        topics=["frustration", "impossibility", "variation"],
        difficulty="credit", marks=10,
        question_text=(
            "A building contractor agreed to supply and install a facade for a fixed sum by a fixed "
            "date. Weeks into the work, the owner unilaterally changed the design in a way that added "
            "substantial cost and made timely completion impossible. The contract has no variation or "
            "force-majeure clause. Has the contract been frustrated? Explain the test."
        ),
        gold_answer=(
            "The leading authority is Codelfa Construction Construction Pty Ltd v State Rail "
            "Authority of New South Wales (1982) 149 CLR 337. Frustration discharges a contract when, "
            "without fault of either party, a supervening event renders performance impossible or "
            "radically transforms the obligations so that they are fundamentally different from what "
            "was undertaken. Two requirements: the event must not be self-induced, and the changed "
            "obligations must be so different that holding the parties to the original bargain would "
            "amount to a new contract. A mere increase in cost or difficulty is not enough. Here the "
            "obstacle was the owner's own variation, so the contractor cannot rely on frustration "
            "(self-inducement) and should instead pursue a variation claim or, if the owner's conduct "
            "repudiated, a claim for repudiatory breach."
        ),
        key_issues=[
            "frustration", "impossibility or radical change", "no self-inducement",
            "increase in cost not enough", "variation or repudiation alternatives",
        ],
        authorities=[{"kind": "case",
                      "cite": "Codelfa Construction Construction Pty Ltd v State Rail Authority of New South Wales (1982) 149 CLR 337"}],
        rubric=[("rule", 4), ("application", 4), ("conclusion", 2)],
    ),
    # 3 — torts / mcq / pass
    item(
        id="auslex-2026-0003", type="mcq",
        jurisdiction=["VIC"], area="torts",
        topics=["informed consent", "duty to warn", "negligence"],
        difficulty="pass", marks=4,
        question_text=(
            "A surgeon fails to warn a patient of a known, material risk of a recommended procedure, "
            "and the risk materialises. Which of the following best states the Australian position on "
            "the duty to warn?"
        ),
        gold_answer=(
            "The correct answer is B. In Rogers v Whitaker (1992) 175 CLR 479 the High Court held "
            "that a practitioner's duty is to warn of material risks, and a risk is material if a "
            "reasonable person in the patient's position would be likely to attach significance to it "
            "if warned. The standard is objective (the reasonable patient) and protects the patient's "
            "right to informed decision-making; it is not a question of what a reasonable body of "
            "professional opinion would disclose."
        ),
        key_issues=["material risk", "objective reasonable-patient standard",
                    "right to informed decision-making"],
        authorities=[{"kind": "case", "cite": "Rogers v Whitaker (1992) 175 CLR 479"}],
        rubric=[("correct_answer", 4)],
        mcq_options=[
            "A. The doctor must warn of every risk, however remote.",
            "B. The doctor must disclose material risks, judged by what a reasonable person in the patient's position would regard as material.",
            "C. The standard is what a reasonable body of professional opinion would disclose.",
            "D. There is no duty to warn unless the doctor was negligent in performing the procedure itself.",
        ],
        mcq_correct=1,
    ),
    # 4 — torts / essay / distinction
    item(
        id="auslex-2026-0004", type="essay",
        jurisdiction=["VIC"], area="torts",
        topics=["negligent misstatement", "pure economic loss", "duty of care"],
        difficulty="distinction", marks=20,
        question_text=(
            "Discuss, with reference to the authorities, when a person who makes a negligent "
            "misstatement that induces another to act can be held liable in negligence for the pure "
            "economic loss that results. Address the duty of care, the requirement of reasonable "
            "foreseeability and proximity, and why pure economic loss is treated differently from "
            "physical loss."
        ),
        gold_answer=(
            "The central authority is Caltex Oil (Australia) Pty Ltd v Davenport (1979) 144 CLR 397. "
            "The High Court held that a duty of care can arise in respect of a negligent misstatement "
            "where the maker knew, or ought reasonably to have known, of the particular purpose for "
            "which the information would be relied on, and that the recipient would in fact rely on "
            "it to its detriment. Liability therefore turns on (1) a special relationship or proximity "
            "in which the maker assumed responsibility for the accuracy of the information for the "
            "recipient's identified purpose, (2) reasonable foreseeability that reliance would cause "
            "loss if the information were careless, and (3) actual detrimental reliance. Pure economic "
            "loss is treated differently from physical loss because it is not confined by the bounds "
            "of physical harm: absent a special relationship, imposing liability for foreseeable "
            "pecuniary loss alone would expose people to an indeterminate class of claimants for an "
            "indeterminate time. The special-relationship and proximity requirement is the control "
            "device that justifies recovery. The claimant must also show the statement was made "
            "without reasonable care and that the loss flowed from reliance on it, not from an "
            "independent cause."
        ),
        key_issues=[
            "negligent misstatement", "duty of care and proximity",
            "known purpose and reliance", "pure economic loss",
            "indeterminate liability as the policy reason",
        ],
        authorities=[{"kind": "case",
                      "cite": "Caltex Oil (Australia) Pty Ltd v Davenport (1979) 144 CLR 397"}],
        rubric=[("rule", 6), ("application", 8), ("critical_analysis", 4),
                ("structure", 2)],
    ),
    # 5 — crime / short_answer / credit
    item(
        id="auslex-2026-0005", type="short_answer",
        jurisdiction=["Cth"], area="crime",
        topics=["burden of proof", "beyond reasonable doubt", "presumption of innocence"],
        difficulty="credit", marks=10,
        question_text=(
            "State and explain the standard of proof the prosecution must meet in a criminal trial, "
            "and the meaning of 'beyond reasonable doubt' as it applies to a jury. Explain the "
            "distinction between the prosecution's legal burden and the defendant's evidentiary "
            "burden, and why legal burdens on the accused are restricted."
        ),
        gold_answer=(
            "The standard is set out in R v Cooper (2017) 259 CLR 500. The prosecution bears the legal "
            "(persuasive) burden of proving every element of the offence, and every defence not "
            "expressly placed on the accused, beyond reasonable doubt. 'Beyond reasonable doubt' "
            "means the jury must be satisfied to a moral certainty, leaving no reasonable doubt on the "
            "basis of the evidence; a mere suspicion is not enough, and the accused need not be proved "
            "innocent to a positive certainty. By contrast, the defendant's ordinary burden is merely "
            "an evidentiary one: the accused must adduce sufficient evidence to put a matter (such as "
            "an exception or excuse) in issue, after which the prosecution must still disprove it "
            "beyond reasonable doubt. Legal (persuasive) burdens on the accused are restricted because "
            "the presumption of innocence requires the State to prove guilt; a legal burden on the "
            "accused inverts that principle and is confined to the narrow statutory exceptions."
        ),
        key_issues=[
            "beyond reasonable doubt", "legal vs evidentiary burden", "moral certainty",
            "presumption of innocence", "restriction of legal burdens on the accused",
        ],
        authorities=[{"kind": "case", "cite": "R v Cooper (2017) 259 CLR 500"}],
        rubric=[("rule", 4), ("application", 4), ("conclusion", 2)],
    ),
    # 6 — crime / mcq / pass
    item(
        id="auslex-2026-0006", type="mcq",
        jurisdiction=["QLD"], area="crime",
        topics=["burden of proof", "statutory defences", "presumption of innocence"],
        difficulty="pass", marks=4,
        question_text=(
            "A criminal statute says 'it is a defence to the accused that ...'. On its face, who bears "
            "the legal (persuasive) burden for that defence, and how does that interact with the "
            "presumption of innocence?"
        ),
        gold_answer=(
            "The correct answer is B. Following He Kaw Teh v The Queen (1985) 155 CLR 623, a defence "
            "expressed in statutory language such as 'it is a defence to the accused that ...' may, on "
            "its natural meaning, place the legal (persuasive) burden on the accused. However, because "
            "of the presumption of innocence, the court will construe the provision so as to impose the "
            "least onerous burden consistent with its terms, ordinarily an evidentiary burden on the "
            "accused, with the prosecution retaining the legal burden of disproving the defence beyond "
            "reasonable doubt."
        ),
        key_issues=["legal vs evidentiary burden", "statutory construction",
                    "presumption of innocence"],
        authorities=[{"kind": "case", "cite": "He Kaw Teh v The Queen (1985) 155 CLR 623"}],
        rubric=[("correct_answer", 4)],
        mcq_options=[
            "A. The accused bears an evidentiary burden only, and the prosecution must still disprove it beyond reasonable doubt.",
            "B. The accused may bear the legal burden on a natural reading, but the court will construe the provision to impose the least onerous burden consistent with the presumption of innocence.",
            "C. The prosecution always bears the burden for every defence, so the provision is void.",
            "D. The accused need not prove anything once the defence is mentioned.",
        ],
        mcq_correct=1,
    ),
    # 7 — constitutional / essay / high_distinction
    item(
        id="auslex-2026-0007", type="essay",
        jurisdiction=["Cth"], area="constitutional",
        topics=["heads of power", "s 61 executive power", "s 81 taxation", "spending limits"],
        difficulty="high_distinction", marks=20,
        question_text=(
            "The Commonwealth legislated a package of economic stimulus payments to individuals. "
            "Discuss, with reference to the authorities, the High Court's approach to identifying "
            "valid heads of Commonwealth legislative power, and the reasoning in Pape v Commissioner "
            "of Taxation (2009) 243 CLR 336 about the 'executive government' power and the implied "
            "limitation that Commonwealth spending must be within a valid head of power."
        ),
        gold_answer=(
            "The key authority is Pape v Commissioner of Taxation (2009) 243 CLR 336. A majority of "
            "the High Court upheld the stimulus payments as supported by the executive government "
            "power in s 61 read with s 81, rather than (as also argued) a national-emergency or "
            "external-affairs power. The decision confirms that the Commonwealth's legislative power "
            "is confined to the express and implied heads of power in the Constitution, and that s 61 "
            "read with s 81 confers a general executive power to receive and manage the revenues and "
            "make expenditures, including a power to tax and appropriate, that can support laws in "
            "relation to the conduct of the Commonwealth's executive government. The implied "
            "limitation identified is that the Commonwealth cannot simply tax or spend for any "
            "purpose: the expenditure must fall within a power the Commonwealth validly possesses, "
            "and grants to the States under s 96 must be within a Commonwealth power. The Court "
            "declined to found validity on a free-standing national-life or national-emergency head, "
            "preferring the s 61/s 81 footing. The decision is significant for recognising a general "
            "executive-power head, reinforcing that all Commonwealth spending must trace to a valid "
            "head, and working the incidental and implied limits through the structure of the heads of "
            "power rather than a free-standing general welfare power."
        ),
        key_issues=[
            "heads of power", "s 61 and s 81 executive power",
            "implied limitation that spending must be within a valid head",
            "rejection of a general welfare power", "role of s 96",
        ],
        authorities=[{"kind": "case",
                      "cite": "Pape v Commissioner of Taxation (2009) 243 CLR 336"}],
        rubric=[("rule", 6), ("application", 8), ("critical_analysis", 4),
                ("structure", 2)],
    ),
    # 8 — constitutional / short_answer / credit
    item(
        id="auslex-2026-0008", type="short_answer",
        jurisdiction=["Cth", "VIC"], area="constitutional",
        topics=["external affairs power", "treaty implementation", "s 51(xxix)"],
        difficulty="credit", marks=10,
        question_text=(
            "Explain the external affairs power in s 51(xxix) and its use to support Commonwealth "
            "legislation on matters otherwise within a State's field of competence. What are the main "
            "limits on its exercise, with reference to Victoria v The Commonwealth (External Affairs) "
            "(1975) 134 CLR 135?"
        ),
        gold_answer=(
            "The external affairs power in s 51(xxix) allows the Commonwealth to make laws with "
            "respect to external affairs, including implementing treaty obligations. In Victoria v "
            "The Commonwealth (External Affairs) (1975) 134 CLR 135 the High Court upheld "
            "Commonwealth legislation implementing a treaty even though the subject matter would "
            "otherwise fall within State competence, confirming that a validly entered treaty can "
            "support Commonwealth legislation on a topic otherwise State. The main limits, developed "
            "in that and later cases, are: (1) the treaty must be a valid international agreement to "
            "which Australia is a party; (2) the domestic legislation must be reasonably appropriate "
            "and adapted to giving effect to the treaty obligation, not an unrelated pretext; and "
            "(3) the law must be consistent with the treaty. The power is therefore a significant and "
            "broad head, but it is not a general power to legislate on any subject the executive has "
            "treated as external; the legislative link to a genuine treaty obligation is essential."
        ),
        key_issues=[
            "s 51(xxix) external affairs", "treaty implementation",
            "legislation on a State topic", "appropriateness to the treaty", "validity of the treaty",
        ],
        authorities=[{"kind": "case",
                      "cite": "Victoria v The Commonwealth (External Affairs) (1975) 134 CLR 135"}],
        rubric=[("rule", 4), ("application", 4), ("conclusion", 2)],
    ),
    # 9 — admin / hypothetical / credit
    item(
        id="auslex-2026-0009", type="hypothetical",
        jurisdiction=["Cth"], area="admin",
        topics=["procedural fairness", "audi alteram partem", "reasons", "certiorari"],
        difficulty="credit", marks=15,
        question_text=(
            "The Department of Immigration makes a decision not to renew a resident's visa. The "
            "decision-maker does not give the resident a statement of reasons or a chance to respond to "
            "new adverse material before deciding. Advise on the decision's validity, identifying the "
            "procedural-fairness obligations the decision-maker owed."
        ),
        gold_answer=(
            "The decision is vulnerable to being set aside for breach of procedural fairness. The "
            "leading authority is Kioa v West (1985) 159 CLR 550. Procedural fairness (natural "
            "justice) is a common-law obligation that applies to administrative decisions affecting a "
            "person's rights, interests or legitimate expectations, unless excluded by statute. Its "
            "two core rules, identified in Kioa v West, are (1) the rule against bias, the "
            "decision-maker must be free of actual or a reasonable apprehension of bias; and (2) the "
            "audi alteram partem rule, the affected person is entitled to be informed of the case "
            "against them and to a fair opportunity to be heard and to respond. The content of the "
            "duty is flexible and depends on the statutory scheme, the nature of the decision, and the "
            "seriousness of its consequences. Here, where fresh adverse material was relied on and no "
            "reasons were given, the resident was denied a meaningful opportunity to respond, which is "
            "a breach of the hearing rule (the extent of a reasons duty is a further issue). The likely "
            "remedy is a writ in the nature of certiorari quashing the decision, or mandamus to make a "
            "fresh decision, depending on the available review jurisdiction."
        ),
        key_issues=[
            "procedural fairness", "rule against bias", "audi alteram partem / hearing rule",
            "flexible content by context", "remedy of certiorari or mandamus",
        ],
        authorities=[{"kind": "case", "cite": "Kioa v West (1985) 159 CLR 550"}],
        rubric=[("issue_identification", 4), ("rule", 4), ("application", 5),
                ("conclusion", 2)],
    ),
    # 10 — admin / mcq / pass
    item(
        id="auslex-2026-0010", type="mcq",
        jurisdiction=["Cth"], area="admin",
        topics=["legitimate expectations", "procedural fairness"],
        difficulty="pass", marks=4,
        question_text=(
            "A government department has historically granted a particular permit on the strength of "
            "representations it makes, though it has no statutory obligation to do so. A relying party "
            "applies, relying on those representations. Which of the following best describes the "
            "doctrine of legitimate expectations?"
        ),
        gold_answer=(
            "The correct answer is B. In Minister for Aboriginal Affairs v Peko-Wallsend Ltd (1986) "
            "162 CLR 24 the High Court recognised the legitimate-expectations aspect of procedural "
            "fairness: where a public authority has made clear and unambiguous representations on "
            "which a party has come to rely, the authority is generally obliged either to act "
            "consistently with those representations or to give the party a reasoned explanation before "
            "departing from them. It does not create an absolute right to the promised outcome, and it "
            "operates within, not as a substitute for, the decision-maker's statutory discretion."
        ),
        key_issues=["legitimate expectations", "clear and unambiguous representations",
                    "reasoned explanation before departing", "within statutory discretion"],
        authorities=[{"kind": "case",
                      "cite": "Minister for Aboriginal Affairs v Peko-Wallsend Ltd (1986) 162 CLR 24"}],
        rubric=[("correct_answer", 4)],
        mcq_options=[
            "A. It requires the government to grant the permit because it promised to.",
            "B. It requires the decision-maker to act in accordance with its earlier representations, or at minimum to give a reasoned explanation before departing from them; it is not a free-standing right to the outcome.",
            "C. It creates an enforceable contractual right to the permit.",
            "D. It never applies to administrative decisions, only to legislative ones.",
        ],
        mcq_correct=1,
    ),
    # 11 — equity_trusts / short_answer / credit
    item(
        id="auslex-2026-0011", type="short_answer",
        jurisdiction=["WA"], area="equity_trusts",
        topics=["proprietary estoppel", "reliance and detriment", "unconscionability"],
        difficulty="credit", marks=10,
        question_text=(
            "A parent represents to their adult child that a family property will be left to them on "
            "the parent's death. Relying on that, the child makes substantial financial and personal "
            "contributions to the property. The parent then alters the will to leave the property to a "
            "charity. Discuss the child's equitable position."
        ),
        gold_answer=(
            "The child's position is analysed under proprietary estoppel, as applied in Re Frame "
            "(1987) 163 CLR 147. Where a legal right is to be defeated by an equitable claim of "
            "estoppel, the claimant must show (1) a clear and unambiguous representation or assumption "
            "of a right (that the property would pass to the child), (2) reliance on that "
            "representation, and (3) detriment suffered in reliance, such that it would be "
            "unconscionable for the representor to resile. The representation can arise from conduct "
            "as well as words. In Re Frame the Court held that the assurance that the property would "
            "pass, acted on by the claimant to their detriment, gives rise to an equitable interest "
            "enforceable against the legal owner, the court's task being to do the minimum equity "
            "necessary to prevent unconscionability, which may be short of the whole beneficial "
            "interest if that is all the unconscionability requires. The child should therefore plead "
            "estoppel and seek a declaration of an equitable interest, with the quantum of the "
            "interest tailored to the detriment."
        ),
        key_issues=[
            "proprietary estoppel", "clear representation", "reliance and detriment",
            "unconscionability", "minimum equity to prevent unconscionability",
        ],
        authorities=[{"kind": "case", "cite": "Re Frame (1987) 163 CLR 147"}],
        rubric=[("rule", 4), ("application", 4), ("conclusion", 2)],
    ),
    # 12 — property / mcq / pass
    item(
        id="auslex-2026-0012", type="mcq",
        jurisdiction=["NSW"], area="property",
        topics=["Torrens system", "caveat", "registered land"],
        difficulty="pass", marks=4,
        question_text=(
            "Under the New South Wales Torrens system, a person who claims an interest in registered "
            "land but has not yet had it recognised may protect that claim by giving a caveat. Which of "
            "the following best describes the effect of a caveat under the Real Property Act 1900 (NSW)?"
        ),
        gold_answer=(
            "The correct answer is B. Under the Real Property Act 1900 (NSW), a caveat under s 42 "
            "operates to prevent the registered proprietor (or Registrar) from dealing with the "
            "registered land, for example registering a transfer, while the caveat remains, giving the "
            "caveator an opportunity to establish the claimed interest or have the caveat removed. It "
            "does not itself vest any interest; it is a protective notice. If a caveat is wrongly "
            "maintained, a person who was prevented from dealing may seek damages for the loss caused "
            "by the improper caveat."
        ),
        key_issues=["caveat as a protective notice", "prevents dealings while on title",
                    "does not vest title", "damages for improper caveat"],
        authorities=[{"kind": "statute",
                      "cite": "Real Property Act 1900 (NSW) s 42"}],
        rubric=[("correct_answer", 4)],
        mcq_options=[
            "A. It immediately vests the caveator's interest in the registered land.",
            "B. It prevents the registered proprietor from dealing with the land (e.g. registering a transfer) while the caveat is on the title, so the caveator can seek to have the interest confirmed or removed.",
            "C. It is a form of easement over the land.",
            "D. It has no legal effect and is merely a notice.",
        ],
        mcq_correct=1,
    ),
    # 13 — corporations / hypothetical / distinction
    item(
        id="auslex-2026-0013", type="hypothetical",
        jurisdiction=["Cth"], area="corporations",
        topics=["directors' duties", "related-party transactions", "confidential information"],
        difficulty="distinction", marks=15,
        question_text=(
            "A director of a listed company votes in favour of a related-party transaction in which a "
            "company the director controls stands to benefit, without disclosing the material personal "
            "interest. Separately, the director uses confidential information about a pending, "
            "unannounced acquisition to buy the company's shares before the announcement. Identify and "
            "analyse the directors' duties breached and the potential remedies."
        ),
        gold_answer=(
            "The director engages in at least two breaches of Part 2D.1 of the Corporations Act 2001 "
            "(Cth). First, s 181 requires a director to exercise powers and discharge duties in good "
            "faith in the best interests of the corporation and for a proper purpose; the related-party "
            "transaction rules (s 191) require a self-interested transaction to meet the statutory "
            "criteria and the director to comply with the disclosure and approval process, so voting "
            "for a transaction benefitting a company they control, without disclosing the material "
            "personal interest, is a breach. Second, s 184 prohibits a director from using their "
            "position to gain an advantage for themselves or another, or to cause detriment to the "
            "corporation, and the related provisions prohibit using confidential information; using "
            "confidential, price-sensitive information about the unannounced acquisition to trade is a "
            "breach of the duty not to misuse a position or confidential information, and may also "
            "engage continuous-disclosure and market-integrity concerns. Potential remedies include a "
            "civil penalty order, a compensation order for loss or damage to the corporation (s 1317H), "
            "a disqualification order (s 206C), and possibly an injunction; the corporation (or, in "
            "some cases, a member via derivative or class action) may seek relief. The non-disclosure is "
            "itself a significant aggravating factor."
        ),
        key_issues=[
            "s 181 good faith and best interests", "s 191 related-party and self-dealing",
            "s 184 misuse of position / confidential information",
            "non-disclosure of material personal interest",
            "remedies: civil penalty, compensation, disqualification",
        ],
        authorities=[
            {"kind": "statute", "cite": "Corporations Act 2001 (Cth) s 181"},
            {"kind": "statute", "cite": "Corporations Act 2001 (Cth) s 184"},
        ],
        rubric=[("issue_identification", 4), ("rule", 4), ("application", 5),
                ("conclusion", 2)],
    ),
    # 14 — evidence / short_answer / credit
    item(
        id="auslex-2026-0014", type="short_answer",
        jurisdiction=["Cth"], area="evidence",
        topics=["hearsay rule", "s 58", "purpose of evidence"],
        difficulty="credit", marks=10,
        question_text=(
            "In a civil proceeding governed by the Evidence Act 1995 (Cth), a party seeks to adduce a "
            "statement made by a witness to a third person, not for the purpose of proving its truth "
            "but to prove that the witness said it. Explain how the hearsay rule applies and why the "
            "statement may still be admissible."
        ),
        gold_answer=(
            "The hearsay rule in s 58 of the Evidence Act 1995 (Cth) provides that hearsay evidence "
            "is not admissible to prove the existence of a fact that it was the maker's state of mind "
            "or that the statement asserted. The critical point is purpose: the rule bites only when "
            "the statement is adduced to prove the truth of the matter asserted. Here the statement is "
            "offered only to prove that the witness said it, for example to prove the witness's notice, "
            "intent, or that a representation was made, not to prove that what was said was true. "
            "Because the fact in issue is the making of the statement itself (an act or state of mind "
            "of the maker, or its effect on the listener) and not the truth of the assertion, the "
            "statement falls outside s 58 and is admissible as non-hearsay. If it were instead offered "
            "to prove the truth of the assertion, it would be hearsay and admissible only via an "
            "exception or exemption in the Act."
        ),
        key_issues=[
            "s 58 hearsay rule", "purpose of the evidence",
            "truth of the assertion vs the fact that it was said",
            "non-hearsay admissibility", "exceptions for hearsay",
        ],
        authorities=[{"kind": "statute", "cite": "Evidence Act 1995 (Cth) s 58"}],
        rubric=[("rule", 4), ("application", 4), ("conclusion", 2)],
    ),
    # 15 — civil_procedure / mcq / pass
    item(
        id="auslex-2026-0015", type="mcq",
        jurisdiction=["NSW"], area="civil_procedure",
        topics=["striking out", "pleadings", "civil procedure"],
        difficulty="pass", marks=4,
        question_text=(
            "Under the Civil Procedure Act 2011 (NSW), on what basis may a party apply to have a "
            "pleading struck out?"
        ),
        gold_answer=(
            "The correct answer is B. Under the Civil Procedure Act 2011 (NSW) (s 56), a party may "
            "apply to have a step in the proceedings struck out where it discloses no reasonable cause "
            "of action or defence, is frivolous or vexatious, is an abuse of the court's process, or "
            "may prejudice or endanger a fair trial. The test is whether, accepting the facts pleaded "
            "as true, the pleading discloses a tenable claim or defence; it is not a full merits "
            "determination, and the moving party need only show the pleaded case is legally "
            "insufficient or an abuse. Striking out is discretionary and is ordinarily a last resort."
        ),
        key_issues=["no reasonable cause of action or defence", "frivolous or vexatious",
                    "abuse of process", "discretionary last-resort remedy"],
        authorities=[{"kind": "statute",
                      "cite": "Civil Procedure Act 2011 (NSW) s 56"}],
        rubric=[("correct_answer", 4)],
        mcq_options=[
            "A. Whenever a party disagrees with the other side's legal argument.",
            "B. Where the pleading discloses no reasonable cause of action or defence, is frivolous, vexatious, or an abuse of the court's process, or may prejudice a fair trial.",
            "C. Only where the pleading is factually wrong.",
            "D. Only at the judge's own initiative, never on application.",
        ],
        mcq_correct=1,
    ),
    # 16 — ethics / short_answer / credit
    item(
        id="auslex-2026-0016", type="short_answer",
        jurisdiction=["NSW"], area="ethics",
        topics=["confidentiality", "professional conduct", "s 267"],
        difficulty="credit", marks=10,
        question_text=(
            "A client discloses to their lawyer, in confidence, information about a past, unrelated "
            "financial irregularity that the client says is now fully remediated. A third party, who is "
            "not a party to any proceeding with the client, requests that information from the lawyer. "
            "Discuss the lawyer's confidentiality obligations and whether the information may be "
            "disclosed."
        ),
        gold_answer=(
            "The lawyer is bound by the duty of confidentiality in s 267 of the Legal Profession Act "
            "2014 (NSW) (and the equivalent professional-conduct rules), which obliges a lawyer to keep "
            "confidential all information, of whatever kind, acquired in the course of the retainer or "
            "in the client's presence, whether or not it relates to the matters the client engaged the "
            "lawyer about, and to use it only for the purposes of the retainer. The duty persists after "
            "the retainer ends and, subject to narrow exceptions, cannot be waived by a third party. "
            "The general rule is that the lawyer may not disclose the information to the requesting "
            "third party. The main recognised exceptions are disclosure with the client's informed "
            "consent, disclosure required by law or court order, and the limited serious-harm or "
            "crime-fraud exceptions where non-disclosure is necessary to prevent a serious and imminent "
            "threat to a person's life or safety, or the commission of a serious criminal offence. A "
            "past, fully remediated financial irregularity, disclosed in confidence and not connected "
            "to an imminent threat or to a current fraud against the requesting party, does not fall "
            "within those exceptions. The lawyer should therefore refuse the request, explain (without "
            "revealing the confidential content) that the information is subject to confidentiality, "
            "and advise the third party to seek it from the client directly or by other lawful means."
        ),
        key_issues=[
            "s 267 duty of confidentiality", "scope: all information in the retainer",
            "persists after the retainer", "exceptions: consent, compulsion, serious-harm",
            "no exception for a remediated past irregularity",
        ],
        authorities=[{"kind": "statute",
                      "cite": "Legal Profession Act 2014 (NSW) s 267"}],
        rubric=[("rule", 4), ("application", 4), ("conclusion", 2)],
    ),
]


def main() -> int:
    # Validate every item individually for a clear per-item error report.
    errors = 0
    for it in ITEMS:
        try:
            validate_item(it)
        except ValueError as exc:
            errors += 1
            print(f"SCHEMA FAIL {it['id']}:\n{exc}")
    # Whole-set validation (schema + jurisdiction + canary + dedup).
    report = validate_dataset(ITEMS)
    errs = [i for i in report.issues if i.level == "error"]
    warns = [i for i in report.issues if i.level == "warning"]
    print(f"items={len(ITEMS)}  errors={len(errs)}  warnings={len(warns)}")
    for i in errs:
        print(f"  ERROR [{i.code}] {i.item_id}: {i.message}")
    for i in warns:
        print(f"  warn  [{i.code}] {i.item_id}: {i.message}")

    if errors or errs:
        print("NOT WRITING: validation errors present.")
        return 1

    out = ROOT / "data" / "questions" / "auslex.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        for it in ITEMS:
            fh.write(json.dumps(it, sort_keys=True, default=str) + "\n")
    print(f"wrote {out} ({len(ITEMS)} items)")

    # Summary by type / area / difficulty.
    from collections import Counter
    print("by type:", dict(Counter(i['type'] for i in ITEMS)))
    print("by area:", dict(Counter(i['priestley_area'] for i in ITEMS)))
    print("by difficulty:", dict(Counter(i['difficulty'] for i in ITEMS)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
