/**
 * Speaker notes for the 4-minute presentation.
 *
 * Total budget: 240 s.  Each note gives the timing, the sentences to say,
 * and the course concept the slide connects to (Lecture 2 = searching,
 * Lecture 3 = knowledge representation + uncertainty, Lecture 4 = machine
 * learning, Lecture 5 = unsupervised learning, Lecture 8 = expert systems
 * + recommender systems, Lecture 9 = generative AI / LLMs).
 *
 * These notes are what the marker hears.  They say the lecture words out
 * loud, so the work is recognisable as course material.
 */
module.exports = {
  '01': `[0:00-0:12  |  12 s]
"Good morning. I'm Niannian Chen, 26063619G. PetSafe-Greenery: a dual-constraint
agentic workflow for pet-safe balcony planting."

"Before I start: over 700 ornamental species are dangerous to cats or dogs, and
a language model cannot check that fact for itself. So the question is not
'can an LLM design a garden?', it is 'when do we let it decide?'"

KEY LINE: "My answer is that we never let it decide anything that can be checked."`,

  '02': `[0:12-0:42  |  30 s]
Point at the two rows, then read the quote.

"Beautiful for you. Fatal for your cat."

"True Lily - Lilium species. Ingesting one petal is enough. Acute kidney failure
in cats. No antidote. And this is not an exotic plant: it is the classic
balcony flower."

"Sago Palm - Cycas revoluta. Same story for dogs. The plant is sold everywhere.
The toxicity is in a public database. The LLM simply does not consult it."

"700+ species are dangerous to cats or dogs. And LLMs recommend them - because
toxicity is a fact the model cannot check for itself."

(Do NOT read the whole table. Two rows, one quote, then move.)`,

  '03': `[0:42-0:55  |  13 s]
"Three users: pet-owning residents who cannot judge toxicity themselves,
landscape-architecture students who need a defensible first draft, and junior
planting designers who need one design that satisfies every constraint at once."

"All three need the same thing: a design they can defend, not a suggestion they
have to check by hand."`,

  '04': `[0:55-1:35  |  40 s]  <-- THE CORE SLIDE
"One idea: split the task by what can be checked.

Step 1, extract: the LLM reads the brief and pulls out pets, light class and
moisture class. Step 2, filter: Python removes every species that is toxic to
a pet in the house - and also every species that cannot survive the site.
Step 3, design: the LLM composes the layout, the combination logic, the care
instructions and the cautions. Step 4, check: deterministic code verifies the
result and hands the model a list of what is missing, for one repair round."

"If a constraint can be checked deterministically, the LLM should not be allowed
to decide it."

COURSE LINK (say this): "In course terms, this is a hybrid of two things we
learned. The LLM is the Language Model of Lecture 9 - prompt-based completion,
used as a general task solver. And the filter plus the ground-truth database is
an Expert System in the sense of Lecture 8: a knowledge base, an inference
engine, and a user interface. The safety-critical decision never goes through
the neural network."`,

  '05': `[1:35-2:00  |  25 s]
"150 species in the ground-truth database, 25 benchmark scenarios, 3 methods
compared."

"Every species comes from the ASPCA toxic-and-non-toxic-plants database, with
light and moisture conditions from NC State Extension. This is the knowledge
acquisition step of Lecture 8 - the database is built by a reproducible script,
not by hand, so it can be rebuilt and audited."

"And I measured the sources against each other: on the 155 species where two
sources overlap, they agree on 140 - 90.3%. The 15 disagreements are all in the
same direction: the secondary source under-reports toxicity. That is exactly
the situation where you must not average the two."`,

  '06': `[2:00-2:35  |  35 s]
"Three methods, one prompt requirement, one rubric. Only the grounding and the
filtering differ - so the comparison measures the architecture, not the prompt."

"B1 zero-shot: the model answers from memory. No catalogue, no filter.
B2 naive RAG: we retrieve the top-k species and hand them to the model, but we
exclude nothing. P, our agent: retrieve, filter, then design, then check."

"Both baselines are the kind of system a student would build in a week. The
agent is the kind of system you can put in front of a pet."

COURSE LINK: "B2 is a recommender system in the Lecture 8 sense - candidate
generation and ranking by BM25, but with no filtering. The agent keeps the
retrieval and adds the inference engine."`,

  '07': `[2:35-3:10  |  35 s]  <-- THE CORE SLIDE
Read the table row by row, column by column. Do not paraphrase the numbers.

"The headline: B1 zero-shot recommends plants that are toxic to the pets in the
house. Zero. B2 naive RAG is also zero - retrieving the catalogue did not help,
because nothing was excluded. Our agent is 1.0, and that is not luck: the filter
runs in Python, so the model is never given the opportunity to pick an unsafe
species."

"On completeness, the ordering is the same and the gap is 15 against 12 out of
15 items."

"And note the column I did not expect: the naive RAG also produces designs that
are horticulturally impossible - plants that cannot survive the light or the
moisture of the site. Grounding the model in a catalogue does not make its
design coherent. Our agent is 1.0 there too, because the viability rule is also
in code."

COURSE LINK: "The agent loop is a bounded generate-and-test search in the sense
of Lecture 2 - the candidate pool is the open list, the filter closes it, and the
cost of the search is the number of model calls, which I report. The repair
loop is hill climbing on the rubric score."`,

  '08': `[3:10-3:35  |  25 s]
"Safety and design quality are two different axes, and I score them separately."

"Safety is binary and deterministic. Completeness is a 15-item rubric, and every
item has a stored detection rule in the code - three spatial zones, the
combination rationale, watering frequency, light position, cautions that name a
concrete risk. A vague mention scores nothing."

"Five of those items form the core score: the three zones plus watering and
light - zero to five."

COURSE LINK: "That is the discipline of Lecture 4 applied to a non-learned
system: the rubric was developed on three scenarios and then measured on the
remaining twenty-two, and the model never sees its own score - it only sees the
list of items it failed."`,

  '09': `[3:35-3:45  |  10 s]
"I want to state my own limits: 150 curated species out of more than a thousand
listed; cats and dogs only; 25 scenarios - a defensible scale, not a large one.
A mis-parsed brief propagates into the candidate pool, and the guarantee covers
the species in the database - the out-of-database rate is reported separately
rather than hidden."

Do not read every bullet. Name two and move on.`,

  '10': `[3:45-4:00  |  15 s]
"One sentence: every checkable constraint belongs in code."

"The LLM designs. Deterministic code decides what is allowed and checks what
came back. That is what makes the 100% safety number a guarantee instead of a
statistic."

"150-species ground truth, reproducible data pipeline, 25-scenario benchmark,
deterministic completeness rubric, live demo, and the code is on GitHub.
Thank you."

COURSE LINK (if there is time): "The whole system is the Expert System of
Lecture 8 with a Language Model from Lecture 9 in the explanation role."`,

  // ---------------------------------------------------------------------
  // Q&A preparation -- 60 seconds, five likely questions.
  // ---------------------------------------------------------------------
  'QA': `Q&A PREP (60 s) -- five questions you will almost certainly get

Q1 "You did not train any model. Why not a neural network? (L6 / L7)"
A: "There are no labelled examples - no target design for a balcony - so nothing
   could be fitted, and the input is a short brief, not an image or a sequence.
   More importantly: the component that decides whether a plant is safe for a
   pet has to be auditable and deterministic. It must give the same answer on
   every run and every machine, and a reader must be able to inspect why. So
   the safety-critical part is in code with a fixed rule set, and the lecture
   techniques are used where they add something measurable rather than
   asserted. The LLM itself is the neural network - Lecture 9 - and it is used
   where it is strongest: language and composition, not arithmetic over
   toxicity."

Q2 "Is the 100% safety not trivially achieved by the filter? What is the agent
    actually contributing?"
A: "Correct, and deliberately so - the guarantee is the point. What the agent
   contributes is everything the baselines cannot do at all: a coherent design
   that satisfies the site constraints, the combination rationale, the care
   instructions and the cautions - 15 out of 15 against 12. And the informative
   comparison is B2: adding the catalogue to a prompt without a filter still
   gives zero safety and impossible plants."

Q3 "How do you know your ground truth is right?"
A: "Every species carries its provenance - the ASPCA URL it came from - and I
   kept two independent sources. On the 155 shared species they agree 90.3% of
   the time. I also wrote a second, formal implementation of the rules as
   Horn clauses with a forward-chaining inference engine, and a test proves the
   two implementations agree on all 25 scenarios. Species I cannot resolve are
   reported as unresolvable rather than guessed."

Q4 "Isn't the completeness score just your own opinion in disguise?"
A: "Every one of the 15 items has a stored detection rule in the code - a
   regular expression or a structured-field check - and the scorer reads them
   out of the JSON. I can show you the rule for any item. The core score is
   five of those items: three zones, watering frequency, light position."

Q5 "25 scenarios - is that enough to claim anything?"
A: "No, and I do not claim more than that. It is a defensible scale, not a
   large one; I state it as a limitation. What the design gives is a
   deterministic guarantee per scenario rather than a statistical claim about
   the world, and the report says exactly that."
`,
};
