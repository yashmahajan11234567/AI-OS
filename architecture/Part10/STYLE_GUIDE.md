# AI-OS Architecture Documentation Style Guide

## 1. Purpose

This document defines the official writing standard for every AI-OS architecture document. It ensures that every section written by any AI appears as though it was written by a single experienced software architect. The guide promotes consistency, clarity, and professionalism across all technical documentation within the AI-OS project.

## 2. Writing Philosophy

### Professional
Write with the authority and precision expected of a principal engineer or distinguished architect. Assume readers are competent professionals who value substance over flair.

### Objective
Present facts, decisions, and trade-offs without bias. Focus on what is, what was decided, and why—not on aspirations or unverified claims.

### Implementation-Oriented
Every concept should connect to concrete implementation concerns. Describe how things work, not just what they are. Link architecture to code, deployment, and operational realities.

### Precise
Use exact terminology. Avoid vague qualifiers like "somewhat," "mostly," or "often." When uncertainty exists, state it explicitly with supporting evidence.

### Architecture-First
Prioritize structural concerns, interaction patterns, and system properties over incidental details. Focus on elements that affect scalability, maintainability, and resilience.

### Engineering Tone
Adopt the voice of an experienced engineer explaining complex systems to peers. Be direct, respect the reader's intelligence, and avoid hype or defensiveness.

## 3. Writing Style

### Present Tense
Describe the system as it exists or is specified. Use present tense for current architecture and future specifications only when describing approved plans.

*Correct:* "The authentication service validates tokens using HMAC-SHA256."
*Incorrect:* "The authentication service will validate tokens..." (unless describing a future, approved change)

### Active Voice
Prefer active constructions where the subject performs the action. This improves clarity and directness.

*Correct:* "The scheduler assigns tasks to worker nodes."
*Incorrect:* "Tasks are assigned to worker nodes by the scheduler."

### Third Person
Avoid first-person pronouns (I, we) and second-person (you) except in direct quotes or documented conversations. Use impersonal constructions or refer to roles/components.

*Correct:* "The system provides an API for configuration updates."
*Incorrect:* "You can update the configuration using our API."

### RFC 2119 Terminology
Use the keywords defined in RFC 2119 for requirement specifications: MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT, RECOMMENDED, MAY, OPTIONAL. Only use these when documenting actual requirements or conventions.

### Avoid Marketing Language
Eliminate superlatives, buzzwords, and promotional phrasing. Let technical merits speak for themselves.

*Avoid:* "revolutionary," "cutting-edge," "seamlessly integrated," "industry-leading"
*Prefer:* Specific descriptions of capabilities, performance characteristics, or design properties

### Avoid Conversational Language
Remove filler phrases, asides, and colloquialisms. Maintain a formal yet accessible tone suitable for international engineering audiences.

*Avoid:* "as you can see," "it's important to note that," "basically," "actually"
*Prefer:* Direct statements of fact

### Avoid Speculative Wording
Do not use words that imply uncertainty about established facts: "appears to," "seems like," "might be," "could potentially." When describing uncertain areas, explicitly label them as such with supporting rationale.

## 4. Terminology Rules

### How Terminology Is Introduced
On first use, define acronyms and uncommon terms parenthetically. Subsequently use the abbreviated form consistently.

*Correct:* "The system uses a Distributed Hash Table (DHT) for node discovery. The DHT employs consistent hashing..."
*Incorrect:* First use: "The system uses a DHT..." without prior definition

### Capitalization
Apply title case for proper nouns, product names, and defined architectural components. Use sentence case for headings and general descriptions. Follow established conventions for technologies (e.g., "REST API," not "Rest api").

### Definitions
Provide clear, operational definitions for specialized terms. Place definitions where terms are first defined or in a dedicated glossary. Avoid circular definitions.

### Consistency
Use exactly one term for each concept throughout the document. Maintain a terminology mapping if multiple naming conventions exist across subsystems.

### Avoid Synonyms
Do not alternate between different words for the same concept (e.g., sometimes "node," sometimes "instance," sometimes "server"). Choose one term and use it exclusively unless distinguishing distinct concepts.

## 5. Section Structure

### Heading Hierarchy
Use only three heading levels:
- `#` for main parts (e.g., Part 1: Foundations)
- `##` for major sections within a part
- `###` for subsections

Do not skip levels (e.g., going from `#` to `###`). Do not use `####` or deeper.

### Subsection Depth
Limit subsections to two levels deep beneath a part heading (i.e., `##` and `###`). If deeper decomposition is needed, consider restructuring or moving details to appendices.

### Paragraph Length
Keep paragraphs focused on a single idea. Target 3-5 sentences per paragraph. Longer paragraphs (up to 8 sentences) are acceptable for complex explanations but should be rare.

### Bullet Usage
Use bullet lists for:
- Enumerating items where order doesn't matter
- Presenting alternatives or options
- Listing characteristics or properties

Use numbered lists for:
- Sequential steps or procedures
- Priority rankings
- Items requiring reference by number

Keep list items concise—ideally one line. Multi-sentence list items should be avoided; convert to subsections if needed.

### Tables
Use tables for:
- Comparing alternatives across multiple dimensions
- Presenting configuration options with default values
- Showing metrics or measurements
- Mapping inputs to outputs

Avoid tables for simple lists or hierarchical data.

### Examples
Include examples only when they clarify non-obvious concepts. Format examples distinctly (see Code Standards). Label examples when referencing them in text.

## 6. Diagram Standards

### Mermaid
Use Mermaid syntax for all diagrams. Ensure diagrams are self-contained and render correctly in the documentation system.

### Flowcharts
Use flowcharts for processes, algorithms, and decision flows. Follow standard flowchart symbols:
- Rectangles: processes or actions
- Diamonds: decisions
- Parallelograms: inputs/outputs
- Arrows: flow direction

### State Diagrams
Use state diagrams for objects with distinct lifecycle phases. Clearly label states and transitions. Include initial and final states where applicable.

### Sequence Diagrams
Use sequence diagrams for interactions between components. Show lifelines vertically, time progressing downward. Label messages clearly. Include return values where significant.

### Architecture Diagrams
Use component or deployment diagrams for structural views. Group related components. Show interfaces and data flows. Use consistent icons/symbols for similar element types.

### Naming Conventions
Use clear, descriptive labels in diagrams. Avoid abbreviations unless universally understood. Maintain consistent terminology between diagrams and text.

### Placement
Place diagrams immediately after their first reference in text. Provide adequate whitespace before and after. Do not embed diagrams within paragraphs.

### Captions
Every diagram must have a caption. Format: `Figure X.Y: [Descriptive title]` where X is the part number and Y is the sequential figure number within that part. Captions should concisely describe the diagram's purpose, not repeat obvious details.

## 7. Table Standards

### Formatting
Use GitHub-flavored Markdown table syntax. Align headers with a separator row. Keep tables narrow enough to render without horizontal scrolling in standard views.

### Column Naming
Use clear, concise column headers. Prefer noun phrases. Avoid articles and unnecessary words. Use sentence case for multi-word headers.

### Ordering
Order columns logically: typically from most general to most specific, or alphabetically for equivalent items. For comparison tables, put the baseline or default option first.

### Alignment
Align numeric columns right. Align text columns left. Align columns containing mixed content based on predominant type.

### Consistency
Use the same table style throughout the document. If using specialized table formats (e.g., for configurations), document and follow that pattern consistently.

## 8. Code Standards

### Pseudocode
Use pseudocode for algorithms when actual code would obscure the concept. Follow these conventions:
- Use clear, English-like keywords (IF, THEN, ELSE, FOR, WHILE)
- Indent consistently (2 spaces)
- Use camelCase for variables and functions
- Include brief comments for non-obvious steps
- Label pseudocode blocks with purpose

### JSON
Format JSON examples with 2-space indentation. Quote all property names. Use double quotes exclusively. Include trailing commas only if demonstrating a specific variant that permits them.

### YAML
Use 2-space indentation for YAML. Prefer block style over flow style for readability. Quote strings that contain special characters or could be confused with numbers/booleans.

### Configuration Examples
Show complete, runnable configuration snippets when possible. Omit irrelevant sections with ellipses (...) and explain what was omitted. Include comments only when explaining non-obvious settings.

### Shell Examples
Use GNU bash syntax for shell examples. Prefix commands with `$ ` for input and show output without prefix. Clearly distinguish between user input and system output.

### Formatting Rules
- Indent code examples consistently (4 spaces or a code block)
- Syntax highlight where supported
- Show complete, minimal examples that demonstrate the concept
- Avoid overly long lines (target <80 characters)
- Include file paths when relevant to the example
- For language-specific examples, indicate the language implicitly through syntax

## 9. Cross References

### Sections
Reference sections by their full title and number. Example: "See Section 3.2 (Writing Style) for detailed guidelines."

### Parts
Reference parts by their number and title. Example: "Part 4 details the communication layer architecture."

### Figures
Reference figures by their full caption number. Example: "As shown in Figure 2.3, the data flow proceeds through three stages."

### Tables
Reference tables by their number and descriptive title. Example: "Configuration options are summarized in Table 5.1."

### Appendices
Reference appendices by their letter and title. Example: "Refer to Appendix A for the complete API specification."

Use relative references only within the same document. For cross-document references, use the full document path and section identifier.

## 10. Language Rules

### Words to Encourage
- use (instead of "utilize" or "employ")
- show (instead of "demonstrate")
- show (instead of "illustrate")
- because (instead of "due to the fact that")
- if (instead of "in the event that")
- to (instead of "in order to")
- must (for requirements)
- should (for recommendations)
- may (for permissions)

### Words to Avoid
- utilize
- leverage
- paradigm
- synergy
- holistic
- robust (unless describing specific fault tolerance)
- seamless
- next-generation
- state-of-the-art
- efficacious
- effectuate

### Forbidden Phrases
- "It is important to note that..."
- "As mentioned previously..."
- "Please note that..."
- "It should be noted that..."
- "In order to..."
- "Due to the fact that..."
- "It is worth mentioning that..."
- "Keep in mind that..."
- "For your information..."
- "It can be seen that..."

### Mandatory Wording
- Use "shall" only for binding requirements (rare in architecture docs)
- Use "must" for absolute requirements
- Use "should" for strong recommendations
- Use "may" for optional features or permissions
- Use "will" only for statements of fact about future behavior that is certain

### Examples
**Encouraged:** "The system must validate all incoming requests before processing."
**Discouraged:** "It is important to note that the system should, in order to ensure security, utilize validation mechanisms for all incoming requests due to the fact that external threats are prevalent."

## 11. Consistency Rules

### Terminology
Maintain a single term for each concept. Create a project-wide glossary if needed. Check against existing documentation for established usage.

### Formatting
Apply consistent code block styling, heading spacing, list indentation, and table formatting throughout. Use the same date format (YYYY-MM-DD) and number formatting conventions.

### Lists
Use parallel structure in bullet points (all phrases or all sentences). Maintain consistent punctuation (either all items end with periods or none do). Do not mix task-oriented and descriptive items in the same list without clear separation.

### Captions
Follow the exact format: `Figure X.Y: [Descriptive title]` for figures and `Table X.Y: [Descriptive title]` for tables. Number continuously within each part.

### Footnotes
Use footnotes sparingly for tangential explanations or attributions. Format consistently. Avoid using footnotes for essential information that belongs in the main text.

### Links
Use relative links for intra-document references. Use descriptive link text, not URLs. Check all links for validity before publication.

## 12. Quality Checklist

Before considering any architecture section complete, verify the following:

- [ ] All claims are supported by evidence, design decisions, or explicit assumptions
- [ ] Terminology is used consistently throughout the section
- [ ] Every acronym is defined on first use
- [ ] Sections follow the prescribed heading hierarchy without skipping levels
- [ ] Paragraphs address a single central idea
- [ ] Bullets and tables are used appropriately for their content type
- [ ] Diagrams have clear captions and are referenced in the text
- [ ] Code examples are correct, minimal, and properly formatted
- [ ] Cross-references use the correct format and point to existing content
- [ ] Language adheres to the encouraged/avoided word lists
- [ ] The section avoids marketing, conversational, and speculative language
- [ ] All required RFC 2119 terminology is used correctly where applicable
- [ ] The section could be understood by a competent engineer unfamiliar with this specific subsystem
- [ ] Trivial implementation details are omitted; focus remains on architectural significance
- [ ] Trade-offs and alternatives are mentioned where significant decisions were made
- [ ] The section answers: What problem does this solve? How does it work? Why was this approach chosen?

Any section failing to satisfy all checklist items requires revision before publication. This guide applies equally to human-authored and AI-generated content within the AI-OS architecture documentation.