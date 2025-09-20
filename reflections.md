## Reflection on AI-Assisted Development of SaveMyLinks

### Introduction
This reflection documents my experience using AI tools to develop **SaveMyLinks**, a public link curation dashboard, as the capstone project for the AI For Developers II course. Balancing a full-time job with this project necessitated a highly efficient workflow, making AI assistance not just beneficial but essential.

### How AI Impacted the Build Process
The most significant impact was **accelerating development despite limited time**. Without AI, learning new JavaScript frameworks would have been prohibitive. By leveraging my existing Python skills and using AI to fill knowledge gaps, I maintained momentum. AI acted as a force multiplier, handling boilerplate code, suggesting architecture, and generating documentation—allowing me to focus on high-level design and integration.

### What Worked Well
- **Strategic Planning:** Defining a detailed tech stack (FastAPI, Bulma, SQLite) and creating rule files (`.trae/rules/`) upfront provided the AI with critical context. This ensured generated code was consistent and aligned with project goals.
- **Scaffolding and Boilerplate:** AI excelled at generating foundational code: FastAPI endpoints, Pydantic schemas, SQLAlchemy models, and Bulma-based templates. This drastically reduced initial setup time.
- **Code Review and Security:** CodeRabbit was invaluable for pre-commit reviews, identifying vulnerabilities like exposed secrets, and suggesting improvements. This added a layer of quality assurance akin to a senior developer review.
- **Context-Aware Prompts:** Providing clear, structured prompts—often including code snippets or schema definitions—yielded highly accurate and relevant outputs. The rule files ensured the AI adhered to project conventions throughout.

### Challenges and Limitations
- **Non-Production Code:** AI-generated code often required refinement for production use. It provided excellent starters, but logic optimizations, error handling, and edge cases needed manual intervention.
- **Prompting Complexity:** Effective prompting required significant upfront effort. I had to possess a clear vision and technical understanding to guide the AI correctly. Without strong critical thinking and direction, the output could be generic or misaligned.
- **Iteration and Reversion:** While AI could generate code quickly, sometimes it overcomplicated solutions. I frequently used version control to revert changes and re-prompt with clearer instructions.

### Lessons Learned
- **Prompting is a Skill:** Success depends on providing rich context. Gathering requirements, defining rules, and having a precise roadmap before engaging AI leads to better outcomes. The AI is a tool, not a substitute for architectural planning.
- **Review is Essential:** AI-generated code must be critically reviewed. Tools like CodeRabbit are crucial, but human judgment is irreplaceable for ensuring logic correctness, security, and adherence to design intent.
- **AI Complements Expertise:** The AI amplified my productivity because I had enough technical knowledge to evaluate its suggestions. It is most powerful when used by developers who can discern good output from bad.

### Conclusion
This project demonstrated that AI is a transformative partner in software development, particularly under constraints. It enabled me to deliver a complete, functional full-stack application efficiently. The experience underscored that AI does not replace developer skill but rather enhances it—requiring clear vision, critical thinking, and technical oversight to realize its full potential.