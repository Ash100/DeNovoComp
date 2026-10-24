# -*- coding: utf-8 -*-
"""Static prose for the DeNovoComp manuscript.

Sections that contain run-derived numbers are built in build_manuscript.py.
Strings here use {named} fields filled from the run record.
"""

TITLE = ("DeNovoComp: specification-driven reinforcement learning for de novo molecular "
         "design with pre-optimisation feasibility assessment and integrated candidate "
         "triage")

# Alternative, shorter, if the editor requests a tighter title:
TITLE_ALT = ("Specification-driven reinforcement learning for de novo molecular design "
             "with feasibility assessment and auditable candidate triage")

KEYWORDS = ("de novo drug design; reinforcement learning; generative chemistry; SELFIES; "
            "transformer; desirability functions; synthetic accessibility; "
            "applicability domain; cheminformatics")

INTRO = [
    ("h2", "From enumeration to generation"),
    ("p", "Small-molecule discovery has historically been an exercise in selection. "
          "Chemists enumerate or purchase a library, filter it computationally, and assay "
          "the survivors. The scale of accessible chemical space, however, defeats "
          "exhaustive enumeration: the number of synthetically plausible drug-like "
          "molecules is frequently estimated at 10⁶⁰ or more, whereas even "
          "ultralarge commercial catalogues span only 10⁹ to 10¹⁰ compounds"
          "¹,². Virtual screening therefore explores a vanishingly small, "
          "historically biased fraction of what could be made."),
    ("p", "Deep generative modelling reframes the problem. Rather than ranking a fixed "
          "set, a generative model learns a probability distribution over molecular "
          "structures and samples new ones from it. The foundational demonstrations of "
          "this idea — continuous latent-space encodings³, recurrent neural "
          "networks over SMILES strings⁴, and, more recently, transformer decoders "
          "such as MolGPT⁵ — established that neural sequence models can "
          "internalise the syntactic and statistical regularities of drug-like chemistry. "
          "Graph-based variational autoencoders⁶ and adversarial approaches⁷ "
          "extended the same principle to explicit molecular graphs. Layering "
          "reinforcement learning (RL) on top of a pretrained generative prior, as "
          "introduced by Olivecrona et al. and matured in the REINVENT family of "
          "tools⁸–¹⁰, converted these unconditional samplers into "
          "goal-directed design engines capable of optimising arbitrary scoring "
          "functions. The field has since produced high-profile prospective validations, "
          "including generatively designed kinase inhibitors advanced to in vivo "
          "evaluation within weeks¹¹, while related deep-learning approaches "
          "have identified structurally novel antibacterial agents from large chemical "
          "libraries⁵²."),
    ("h2", "The persistent gap between generation and decision"),
    ("p", "Despite this progress, a practical gap separates a trained generative model "
          "from a defensible list of molecules a project team can act upon. Generation is "
          "only the first of several decisions. A generated structure must additionally "
          "be assessed for physicochemical suitability, for whether it can plausibly be "
          "synthesised, for the presence of substructures known to interfere with assays "
          "or confer liabilities, and for whether any computational property estimate "
          "applied to it can be trusted at all. Each of these questions is well studied in "
          "isolation, and mature tools exist for each: drug-likeness "
          "heuristics¹²–¹⁴, synthetic accessibility "
          "scoring¹⁵–¹⁷ and retrosynthetic route search¹⁸, "
          "structural-alert catalogues¹⁹,²⁰, and "
          "applicability-domain theory inherited from the QSAR "
          "literature²¹."),
    ("p", "What is largely absent is an integrated, opinionated workflow that connects "
          "them. In current practice, a researcher who wishes to move from “I want "
          "molecules with these properties” to “these twenty structures merit "
          "attention” must typically combine a generation framework, one or more "
          "scoring libraries, a benchmarking suite, and hand-written filtering and ranking "
          "code. That integration work is repeated in laboratory after laboratory, is "
          "rarely published alongside the results, and constitutes a substantial share of "
          "the total effort. Because the glue code is bespoke, the decision rules embedded "
          "within it — the thresholds, the weights, the order of filters — are "
          "frequently undocumented, which impedes both reproduction and critical "
          "appraisal."),
    ("h2", "Why an additional pipeline is warranted"),
    ("p", "The existence of capable generative frameworks raises a fair question: why "
          "introduce another? DeNovoComp is not proposed as a replacement for REINVENT, "
          "GuacaMol, MOSES, or the graph-generative literature, all of which it depends "
          "upon conceptually and cites as prior art. It addresses five specific "
          "deficiencies that are, in our assessment, poorly served by the current "
          "ecosystem."),
    ("h3", "(i) Objective specification is written as code, not declared as a specification"),
    ("p", "In most frameworks, defining what the user actually wants requires composing "
          "scoring components programmatically or editing structured configuration files "
          "whose semantics are documented separately from the chemistry. This raises the "
          "barrier for the medicinal chemist or biologist who has a clear design intent "
          "but limited software engineering experience, and it makes design campaigns "
          "harder to audit after the fact. DeNovoComp exposes a single declarative "
          "specification object in which every objective — a molecular-weight window, "
          "a lipophilicity range, a hydrogen-bond-donor cap, a similarity window to a "
          "reference ligand, a substructure that must be retained, a motif that must be "
          "excluded — is expressed as a named entry with an explicit mode and weight. "
          "The specification is simultaneously the user interface, the reward definition, "
          "and the provenance record."),
    ("h3", "(ii) Objective feasibility is rarely tested before optimisation"),
    ("p", "Goal-directed RL can fail silently. If the requested profile lies far outside "
          "the region of chemical space represented in the training corpus, or if two "
          "objectives are mutually contradictory, the reward signal remains near zero and "
          "optimisation converges to nothing useful — but only after the "
          "computational budget has been spent. To our knowledge, no widely used pipeline "
          "performs an explicit, reported pre-optimisation feasibility assessment. "
          "DeNovoComp scores the unsteered baseline sample against the specification and "
          "reports both the overall score distribution and a per-objective desirability "
          "breakdown before any RL step is taken, so that unreachable or internally "
          "inconsistent specifications are diagnosed at the outset and attributed to the "
          "responsible objective."),
    ("h3", "(iii) Synthesizability is treated as a post hoc filter rather than a design objective"),
    ("p", "A well-documented failure mode of generative chemistry is the production of "
          "structures that are formally valid and score well on the target property yet "
          "are impractical to prepare; Gao and Coley demonstrated systematically that "
          "molecules proposed by generative models are frequently not synthesizable and "
          "that this deficiency is not detected by standard generative "
          "benchmarks²². Applying a synthetic-accessibility filter only after "
          "generation discards work already performed and leaves the generator no "
          "incentive to improve. DeNovoComp admits synthesizability directly into the "
          "reward as a first-class objective, so that the optimisation pressure favours "
          "makeable chemistry from the outset, while retaining independent "
          "post-generation scoring as a verification layer."),
    ("h3", "(iv) Applicability domain is almost never reported for generated libraries"),
    ("p", "Novelty is routinely celebrated in generative benchmarking, yet novelty and "
          "reliability are in tension. A structure distant from the training distribution "
          "is, by construction, one about which any model trained on that distribution is "
          "least qualified to speak. The QSAR community formalised this concern decades "
          "ago as the applicability domain²¹, and regulatory guidance treats "
          "domain assessment as a requirement for predictive models. Generative workflows "
          "have largely not inherited this discipline. DeNovoComp computes a "
          "leverage-based domain assessment for every generated molecule against the "
          "training fingerprint distribution and propagates the resulting in-domain flag "
          "into the final triage, so that novelty is reported alongside, rather than "
          "instead of, trustworthiness."),
    ("h3", "(v) Prioritisation logic is opaque and inconsistently reported"),
    ("p", "The step from a scored library to a shortlist involves value judgements: which "
          "thresholds constitute acceptance, how competing signals are weighted, and what "
          "an advancement recommendation actually asserts. These judgements are often "
          "buried in analysis scripts. DeNovoComp makes the triage explicit, emitting a "
          "per-molecule table in which every contributing signal, the composite score, and "
          "the resulting GO, CAUTION, or NO-GO label are recorded together with the "
          "thresholds that produced them. The recommendation is framed narrowly and "
          "deliberately: a GO label asserts computational priority under a stated rule "
          "set, not predicted biological activity or experimental success."),
    ("h2", "Accessibility and reproducibility as design goals"),
    ("p", "A secondary motivation is pedagogical and infrastructural. Substantive "
          "engagement with generative chemistry currently presupposes the ability to "
          "provision a GPU environment and resolve a non-trivial dependency stack. "
          "DeNovoComp is distributed as a single notebook that executes end-to-end on "
          "freely available hosted infrastructure, with graceful degradation when optional "
          "components cannot be installed. Every stage is preceded by expository text that "
          "states what the computation does, what the researcher may change, how the "
          "output should be interpreted, and what a problematic result implies. This makes "
          "the pipeline usable both as a working instrument and as a teaching artefact, "
          "and it makes the reasoning behind each stage inspectable rather than implicit."),
    ("h2", "Contributions"),
    ("p", "The specific contributions of this work are as follows."),
    ("b", "A declarative design specification that expresses multi-objective molecular "
          "design intent — property windows, caps, floors, maximisation targets, "
          "analogue-similarity windows, and required or forbidden substructures — in "
          "a single auditable object that doubles as the reward definition."),
    ("b", "A desirability-based reward construction, adapted from the Derringer–Suich "
          "formalism for simultaneous optimisation of multiple responses²³, with "
          "selectable geometric or arithmetic aggregation that lets the user choose "
          "between strict balance and permitted trade-off."),
    ("b", "An a priori feasibility preview that diagnoses unreachable or contradictory "
          "specifications, with per-objective attribution, before reinforcement-learning "
          "resources are committed."),
    ("b", "Integration of synthesizability into the optimisation objective rather than "
          "only into post hoc filtering, addressing a documented failure mode of "
          "generative models²²."),
    ("b", "Inclusion of leverage-based applicability-domain assessment as a routine, "
          "reported component of a generative workflow, and its propagation into candidate "
          "prioritisation."),
    ("b", "A transparent, fully recorded GO/CAUTION/NO-GO triage and a single-archive "
          "export of all tables, figures, configuration, and model checkpoints, supporting "
          "reproduction and downstream ADMET evaluation."),
]

DISCUSSION = [
    ("h2", "What integration contributes"),
    ("p", "The individual components of DeNovoComp are, with the exception of the "
          "specification layer and the feasibility preview, established methods. The "
          "contribution lies in their assembly into a coherent decision pathway in which "
          "the output of each stage is defined in terms of the decision it informs. This "
          "is not a trivial convenience. When generation, scoring, filtering, and "
          "prioritisation are performed by separate tools connected by ad hoc code, the "
          "assumptions that link them tend to remain undocumented; the resulting shortlist "
          "is difficult to reproduce and, more importantly, difficult to criticise. By "
          "recording the specification, every intermediate table, all thresholds, and both "
          "model checkpoints in a single archive, the pipeline makes the entire chain from "
          "design intent to recommendation available for inspection."),
    ("p", "This orientation reflects a broader argument in the field. Reviews of "
          "generative chemistry and of computational drug discovery more generally have "
          "repeatedly observed that the discipline’s bottleneck has shifted from "
          "model capability to evaluation, prioritisation, and integration with "
          "experimental practice⁴¹–⁴⁵. Commentators have "
          "cautioned specifically that the apparent productivity of generative models can "
          "obscure whether their output is actionable⁴¹. The same concern "
          "motivates the wider call for interpretability in machine-learning-driven "
          "discovery, on the argument that a prediction a chemist cannot interrogate is "
          "difficult to act upon responsibly⁵⁴. A pipeline that produces fewer "
          "molecules but states clearly why each was advanced is, on this view, more "
          "useful than one that produces more with an opaque rationale."),
    ("h2", "Specification-driven design as a user interface"),
    ("p", "Expressing design intent as a declarative object rather than as procedural "
          "scoring code has consequences beyond convenience. It compels the researcher to "
          "state the objective completely and in advance, including the relative weighting "
          "of competing criteria and the aggregation rule that governs trade-off. "
          "Requirements that are ordinarily implicit — that a scaffold be retained, "
          "that a motif be excluded, that a candidate resemble a known ligand without "
          "duplicating it — become explicit, versioned, and auditable. The "
          "specification also functions as a communication artefact: a chemist and a "
          "computational scientist can review it jointly without reading the "
          "implementation, which is difficult when the objective exists only as code."),
    ("p", "The use of desirability functions²³ rather than raw property values "
          "is central to this design. Desirability places heterogeneous quantities — "
          "mass in daltons, a dimensionless partition coefficient, a surface area, a "
          "similarity coefficient — on a common unit scale with a shared "
          "interpretation, so that weighting expresses relative importance rather than an "
          "artefact of differing units. Retaining a graded response outside the accepted "
          "window is equally important: a policy-gradient learner cannot distinguish a "
          "molecule that narrowly misses a target from one that misses it grossly if the "
          "objective is binary, and that distinction carries most of the learning signal "
          "in early optimisation."),
    ("h2", "The value of testing feasibility before optimising"),
    ("p", "The feasibility preview addresses a failure mode that is, in our experience, "
          "both common and under-reported. Reinforcement learning against an unreachable "
          "objective does not raise an error; it produces a flat reward trajectory and a "
          "designed library indistinguishable from the baseline, an outcome easily misread "
          "as a limitation of the method rather than of the specification. Because the "
          "preview reports per-objective desirability rather than only an aggregate, it "
          "distinguishes among the plausible causes: a uniformly demanding specification, "
          "a single unsatisfiable term, a conflict between two terms, or a corpus that "
          "does not contain the relevant chemistry."),
    ("p", "The final case deserves emphasis. Reinforcement learning reweights the "
          "probability of chemistry the prior can already express; it does not introduce "
          "structural motifs absent from the training distribution. A specification "
          "requesting properties characteristic of chemistry unrepresented in the corpus "
          "is therefore not a reinforcement-learning problem but a data problem, and the "
          "appropriate remedy is to retrain the prior on an appropriate corpus — for "
          "instance a target-focused set drawn from a bioactivity "
          "database⁴⁶ — rather than to increase optimisation intensity."),
    ("h2", "Synthesizability as an objective rather than a filter"),
    ("p", "Placing synthetic accessibility inside the reward reflects the finding of Gao "
          "and Coley that generative models frequently propose molecules that cannot be "
          "readily synthesised, and that conventional generative benchmarks do not detect "
          "this²². Filtering after the fact discards computation already "
          "performed and, more importantly, provides the generator with no gradient toward "
          "more tractable chemistry. Including the term in the objective aligns the "
          "optimisation pressure with practical constraints from the outset."),
    ("p", "The limits of this approach should be stated plainly. The synthetic "
          "accessibility score is a fragment-contribution heuristic¹⁵, and the "
          "Bertz index is a graph-complexity measure³⁹; neither constitutes a "
          "synthetic plan. Machine-learned alternatives trained on reaction corpora, such "
          "as SCScore¹⁶ and the retrosynthetic accessibility "
          "classifier¹⁷, are better calibrated to real synthetic practice but "
          "remain estimates. Only retrosynthetic route search against a template library "
          "and a purchasable-building-block "
          "inventory¹⁸,⁵¹ answers the question of how a molecule "
          "would actually be made. The pipeline therefore treats the cheap scores as a "
          "triage layer and reserves route search for the shortlist, which is the "
          "economically rational ordering given the cost differential."),
    ("h2", "Novelty, reliability, and the applicability domain"),
    ("p", "Generative benchmarking has tended to treat novelty as an unqualified good. "
          "The applicability-domain concept, long established in QSAR practice and "
          "codified in model-validation "
          "guidance²¹,⁵³, supplies the necessary counterweight: a "
          "structure far from the training distribution is precisely the structure about "
          "which a model trained on that distribution is least entitled to make claims. "
          "Because generative pipelines routinely apply predictive models to their own "
          "output, importing this discipline is not optional if the resulting property "
          "estimates are to be interpreted responsibly."),
    ("p", "Reporting leverage alongside novelty makes the trade-off visible rather than "
          "implicit. A designed library that is highly novel but largely outside the "
          "domain is not thereby worthless; it may represent exactly the exploration a "
          "project requires. It does, however, warrant different downstream handling, with "
          "greater weight on experimental confirmation and less on computed property "
          "estimates. Carrying the in-domain flag into the triage rule ensures that this "
          "distinction reaches the shortlist rather than being lost in an intermediate "
          "table."),
    ("h2", "Over-optimisation and the preservation of diversity"),
    ("p", "Aggressive policy-gradient optimisation against a bounded objective "
          "concentrates probability mass on a small number of high-scoring solutions. Renz "
          "and colleagues characterised several such failure modes in molecular "
          "optimisation and cautioned against evaluating generative performance by "
          "objective attainment alone³⁵. The practical consequence for a design "
          "campaign is severe: a library with excellent compliance but few distinct "
          "scaffolds presents a single structural hypothesis in many variations, and if "
          "that hypothesis fails experimentally, the campaign has no fallback."),
    ("p", "DeNovoComp therefore reports uniqueness, internal diversity, and scaffold "
          "statistics alongside compliance, and treats a decline in these quantities as a "
          "diagnostic result rather than an incidental one. The recommended operating "
          "point is the optimisation intensity at which compliance has substantially "
          "improved while scaffold diversity remains close to baseline. Where the "
          "objective is intrinsically restrictive — a mandatory substructure, or a "
          "narrow similarity window — some contraction is expected and is not "
          "evidence of over-optimisation, which is why the specification is reported "
          "alongside the diversity metrics."),
    ("h2", "Relationship to existing tools"),
    ("p", "DeNovoComp should be understood as complementary to, rather than competitive "
          "with, the established generative frameworks. REINVENT remains substantially "
          "more capable as a production optimisation engine, offering a wider range of "
          "scoring components, diversity filters, curriculum strategies, and "
          "scaffold-decoration modes⁹,¹⁰. MOSES and GuacaMol remain "
          "the appropriate instruments for comparing generative architectures under "
          "controlled conditions³⁶,³⁷, a purpose for which "
          "DeNovoComp is not designed and against which it makes no claim. Specialised "
          "property predictors and ADMET platforms, trained and evaluated against curated "
          "molecular-property benchmarks⁴⁷, provide far deeper pharmacokinetic "
          "modelling than the descriptor-level assessment implemented "
          "here⁴⁸,⁴⁹."),
    ("p", "The distinct position DeNovoComp occupies is that of an integrated, auditable, "
          "low-barrier path from a declared design objective to a justified shortlist, "
          "executable without local infrastructure and legible to a reader who is not a "
          "specialist in generative modelling. Its natural downstream connection is to "
          "dedicated ADMET and toxicity evaluation, and the exported candidate table is "
          "structured for that handoff."),
]

LIMITATIONS = [
    ("No target-based scoring.", "The objective set is physicochemical, structural, and "
     "synthesizability-oriented. It contains no docking, pharmacophore matching, or "
     "ligand- or structure-based activity model, and therefore does not optimise for "
     "binding to any biological target. Analogue design against a reference ligand, as in "
     "campaign C, provides only an indirect, similarity-based proxy."),
    ("Descriptor-level property estimation.", "Drug-likeness is assessed through computed "
     "descriptors and rule-based heuristics rather than trained pharmacokinetic models, "
     "and consequently does not substitute for dedicated ADMET prediction."),
    ("Heuristic synthesizability.", "The synthesizability layers reported here are "
     "estimates rather than synthetic plans. SCScore and AiZynthFinder were not available "
     "in the execution environment used for this study, so the composite rests on SAscore "
     "and Bertz complexity with weights renormalised accordingly; retrosynthetic "
     "validation was not performed."),
    ("Modest prior capacity and reduced corpus.", "The transformer prior is small by "
     "design so that the pipeline executes within hosted-notebook constraints, and the run "
     "reported here was executed on CPU only, which required the training corpus to be "
     "subsampled from the full curated set. Larger priors trained on larger corpora would "
     "be expected to produce more sophisticated chemistry, at proportionate computational "
     "cost. The quantitative results below should accordingly be read as characterising "
     "the behaviour of the pipeline at this configuration, not as an upper bound on it."),
    ("Single-objective aggregation.", "Multiple objectives are collapsed into one scalar "
     "reward. This is transparent and effective, but it does not recover a Pareto front, "
     "and genuinely non-dominated trade-off solutions may be obscured by the aggregation."),
    ("Representation trade-off.", "The guaranteed decodability of SELFIES eliminates "
     "invalid output but constrains the token distribution the model learns. Evidence that "
     "permitting invalid strings can benefit chemical language models³⁰, "
     "together with the demonstrated effect of SMILES randomisation on generative "
     "quality⁵⁰, indicates that representation choice materially shapes model "
     "behaviour and that the present selection is a considered trade-off rather than a "
     "strict improvement."),
    ("Applicability domain did not discriminate.", "At the basis size and component count "
     "used here the leverage threshold was permissive enough that every molecule in every "
     "library fell inside the domain, so the in-domain flag contributed nothing to the "
     "triage. The assessment is therefore demonstrated but not stress-tested, and a GO "
     "label from this run should not be read as carrying domain evidence."),
    ("Over-optimisation at the default intensity.", "Three of the four campaigns entered "
     "the over-optimisation regime at the pipeline's default reinforcement-learning "
     "intensity, and structural-alert incidence rose in three of four. These are "
     "properties of the default setting rather than of the architecture, and the intensity "
     "sweep identifies better operating points, but they mean the default should be "
     "treated as a starting point to be tuned rather than a recommendation."),
    ("Partial intensity sweep.", "The sweep covered three of the four campaigns at four "
     "intensities with 1,000-molecule libraries, and the campaigns were not re-triaged at "
     "the recommended operating point; the claim that a lower intensity yields a better "
     "shortlist is therefore supported by the diversity and alert data but not yet by a "
     "GO count."),
    ("Single replicate per campaign.", "Each campaign was executed once at a fixed seed. "
     "The seed is a configuration parameter and independent replicates are obtained by "
     "varying it, but the between-replicate variance of the reported quantities was not "
     "estimated here."),
    ("Absence of prospective validation.", "The pipeline has not, in this work, been "
     "coupled to synthesis and assay. Computational triage narrows attention; it does not "
     "establish activity, and the GO label is defined accordingly."),
]

FUTURE = (
    "Four extensions follow directly from the limitations above. First, admitting "
    "target-based scoring components — docking scores, pharmacophore fit, or trained "
    "activity models — into the specification would convert DeNovoComp from a "
    "property-directed to a target-directed design system, and the specification schema "
    "already accommodates this without structural change. Second, integrating "
    "retrosynthetic route search as a routine terminal stage for the shortlist would "
    "replace estimated accessibility with proposed routes at the point where the "
    "additional cost is justified. Third, replacing scalar aggregation with an explicit "
    "multi-objective formulation would expose the Pareto front and allow the trade-off "
    "structure of a campaign to be examined rather than assumed. Fourth, and most "
    "consequentially, prospective validation — synthesis and assay of a GO shortlist "
    "— is required to establish whether the triage rules select molecules that "
    "succeed experimentally, and remains the decisive test of any computational "
    "prioritisation scheme.")

REFERENCES = [
    "Sterling, T. & Irwin, J. J. ZINC 15 — ligand discovery for everyone. J. Chem. Inf. Model. 55, 2324–2337 (2015).",
    "Irwin, J. J. et al. ZINC20 — a free ultralarge-scale chemical database for ligand discovery. J. Chem. Inf. Model. 60, 6065–6073 (2020).",
    "Gómez-Bombarelli, R. et al. Automatic chemical design using a data-driven continuous representation of molecules. ACS Cent. Sci. 4, 268–276 (2018).",
    "Segler, M. H. S., Kogej, T., Tyrchan, C. & Waller, M. P. Generating focused molecule libraries for drug discovery with recurrent neural networks. ACS Cent. Sci. 4, 120–131 (2018).",
    "Bagal, V., Aggarwal, R., Vinod, P. K. & Priyakumar, U. D. MolGPT: molecular generation using a transformer-decoder model. J. Chem. Inf. Model. 62, 2064–2076 (2022).",
    "Jin, W., Barzilay, R. & Jaakkola, T. Junction tree variational autoencoder for molecular graph generation. Proc. 35th Int. Conf. Mach. Learn. 80, 2323–2332 (2018).",
    "De Cao, N. & Kipf, T. MolGAN: an implicit generative model for small molecular graphs. Preprint at https://arxiv.org/abs/1805.11973 (2018).",
    "Olivecrona, M., Blaschke, T., Engkvist, O. & Chen, H. Molecular de-novo design through deep reinforcement learning. J. Cheminform. 9, 48 (2017).",
    "Blaschke, T. et al. REINVENT 2.0: an AI tool for de novo drug design. J. Chem. Inf. Model. 60, 5918–5922 (2020).",
    "Loeffler, H. H. et al. REINVENT 4: modern AI-driven generative molecule design. J. Cheminform. 16, 20 (2024).",
    "Zhavoronkov, A. et al. Deep learning enables rapid identification of potent DDR1 kinase inhibitors. Nat. Biotechnol. 37, 1038–1040 (2019).",
    "Lipinski, C. A., Lombardo, F., Dominy, B. W. & Feeney, P. J. Experimental and computational approaches to estimate solubility and permeability in drug discovery and development settings. Adv. Drug Deliv. Rev. 23, 3–25 (1997).",
    "Veber, D. F. et al. Molecular properties that influence the oral bioavailability of drug candidates. J. Med. Chem. 45, 2615–2623 (2002).",
    "Bickerton, G. R., Paolini, G. V., Besnard, J., Muresan, S. & Hopkins, A. L. Quantifying the chemical beauty of drugs. Nat. Chem. 4, 90–98 (2012).",
    "Ertl, P. & Schuffenhauer, A. Estimation of synthetic accessibility score of drug-like molecules based on molecular complexity and fragment contributions. J. Cheminform. 1, 8 (2009).",
    "Coley, C. W., Rogers, L., Green, W. H. & Jensen, K. F. SCScore: synthetic complexity learned from a reaction corpus. J. Chem. Inf. Model. 58, 252–261 (2018).",
    "Thakkar, A., Chadimová, V., Bjerrum, E. J., Engkvist, O. & Reymond, J. L. Retrosynthetic accessibility score (RAscore). Chem. Sci. 12, 3339–3349 (2021).",
    "Genheden, S. et al. AiZynthFinder: a fast, robust and flexible open-source software for retrosynthetic planning. J. Cheminform. 12, 70 (2020).",
    "Baell, J. B. & Holloway, G. A. New substructure filters for removal of pan assay interference compounds (PAINS) from screening libraries and for their exclusion in bioassays. J. Med. Chem. 53, 2719–2740 (2010).",
    "Brenk, R. et al. Lessons learnt from assembling screening libraries for drug discovery for neglected diseases. ChemMedChem 3, 435–444 (2008).",
    "Netzeva, T. I. et al. Current status of methods for defining the applicability domain of (quantitative) structure–activity relationships. ATLA 33, 155–173 (2005).",
    "Gao, W. & Coley, C. W. The synthesizability of molecules proposed by generative models. J. Chem. Inf. Model. 60, 5714–5723 (2020).",
    "Derringer, G. & Suich, R. Simultaneous optimization of several response variables. J. Qual. Technol. 12, 214–219 (1980).",
    "Landrum, G. RDKit: open-source cheminformatics software. https://www.rdkit.org",
    "Paszke, A. et al. PyTorch: an imperative style, high-performance deep learning library. Adv. Neural Inf. Process. Syst. 32, 8024–8035 (2019).",
    "Pedregosa, F. et al. Scikit-learn: machine learning in Python. J. Mach. Learn. Res. 12, 2825–2830 (2011).",
    "McInnes, L., Healy, J., Saul, N. & Großberger, L. UMAP: uniform manifold approximation and projection. J. Open Source Softw. 3, 861 (2018).",
    "Weininger, D. SMILES, a chemical language and information system. 1. Introduction to methodology and encoding rules. J. Chem. Inf. Comput. Sci. 28, 31–36 (1988).",
    "Krenn, M., Häse, F., Nigam, A., Friederich, P. & Aspuru-Guzik, A. Self-referencing embedded strings (SELFIES): a 100% robust molecular string representation. Mach. Learn. Sci. Technol. 1, 045024 (2020).",
    "Skinnider, M. A. Invalid SMILES are beneficial rather than detrimental to chemical language models. Nat. Mach. Intell. 6, 437–448 (2024).",
    "Vaswani, A. et al. Attention is all you need. Adv. Neural Inf. Process. Syst. 30, 5998–6008 (2017).",
    "Loshchilov, I. & Hutter, F. Decoupled weight decay regularization. Int. Conf. Learn. Represent. (2019).",
    "Rogers, D. & Hahn, M. Extended-connectivity fingerprints. J. Chem. Inf. Model. 50, 742–754 (2010).",
    "Williams, R. J. Simple statistical gradient-following algorithms for connectionist reinforcement learning. Mach. Learn. 8, 229–256 (1992).",
    "Renz, P., Van Rompaey, D., Wegner, J. K., Hochreiter, S. & Klambauer, G. On failure modes in molecule generation and optimization. Drug Discov. Today Technol. 32–33, 55–63 (2019).",
    "Polykovskiy, D. et al. Molecular Sets (MOSES): a benchmarking platform for molecular generation models. Front. Pharmacol. 11, 565644 (2020).",
    "Brown, N., Fiscato, M., Segler, M. H. S. & Vaucher, A. C. GuacaMol: benchmarking models for de novo molecular design. J. Chem. Inf. Model. 59, 1096–1108 (2019).",
    "Preuer, K., Renz, P., Unterthiner, T., Hochreiter, S. & Klambauer, G. Fréchet ChemNet distance: a metric for generative models for molecules in drug discovery. J. Chem. Inf. Model. 58, 1736–1741 (2018).",
    "Bertz, S. H. The first general index of molecular complexity. J. Am. Chem. Soc. 103, 3599–3601 (1981).",
    "Bemis, G. W. & Murcko, M. A. The properties of known drugs. 1. Molecular frameworks. J. Med. Chem. 39, 2887–2893 (1996).",
    "Walters, W. P. & Murcko, M. Assessing the impact of generative AI on medicinal chemistry. Nat. Biotechnol. 38, 143–145 (2020).",
    "Schneider, P. et al. Rethinking drug design in the artificial intelligence era. Nat. Rev. Drug Discov. 19, 353–364 (2020).",
    "Meyers, J., Fabian, B. & Brown, N. De novo molecular design and generative models. Drug Discov. Today 26, 2707–2715 (2021).",
    "Bilodeau, C., Jin, W., Jaakkola, T., Barzilay, R. & Jensen, K. F. Generative models for molecular discovery: recent advances and challenges. WIREs Comput. Mol. Sci. 12, e1608 (2022).",
    "Sadybekov, A. V. & Katritch, V. Computational approaches streamlining drug discovery. Nature 616, 673–685 (2023).",
    "Mendez, D. et al. ChEMBL: towards direct deposition of bioassay data. Nucleic Acids Res. 47, D930–D940 (2019).",
    "Wu, Z. et al. MoleculeNet: a benchmark for molecular machine learning. Chem. Sci. 9, 513–530 (2018).",
    "Swanson, K. et al. ADMET-AI: a machine learning ADMET platform for evaluation of large-scale chemical libraries. Bioinformatics 40, btae416 (2024).",
    "Huang, K. et al. Therapeutics Data Commons: machine learning datasets and tasks for drug discovery and development. Adv. Neural Inf. Process. Syst. Datasets and Benchmarks Track (2021).",
    "Arús-Pous, J. et al. Randomized SMILES strings improve the quality of molecular generative models. J. Cheminform. 11, 71 (2019).",
    "Segler, M. H. S., Preuss, M. & Waller, M. P. Planning chemical syntheses with deep neural networks and symbolic AI. Nature 555, 604–610 (2018).",
    "Stokes, J. M. et al. A deep learning approach to antibiotic discovery. Cell 180, 688–702 (2020).",
    "Tropsha, A. Best practices for QSAR model development, validation, and exploitation. Mol. Inform. 29, 476–488 (2010).",
    "Jiménez-Luna, J., Grisoni, F. & Schneider, G. Drug discovery with explainable artificial intelligence. Nat. Mach. Intell. 2, 573–584 (2020).",
]
