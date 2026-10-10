# PlotPlanner

## AI-Powered Personal Growth, Career Exploration and Opportunity Platform

Version: 1.0  
Status: Active Development  
Architecture: Modular Monolith  
Backend: Python + FastAPI  
Frontend: React + TypeScript + Vite  
Database: PostgreSQL / Supabase  
Authentication: Supabase Auth

---

# 1. Project Vision

PlotPlanner is an AI-powered personal development platform designed
for people who have multiple interests, skills, ambitions and
possible career directions but struggle to determine where to start.

A user might be interested in:

- Software engineering
- Artificial intelligence
- Music production
- Guitar and singing
- Painting and digital art
- Film direction and writing
- Fitness and calisthenics
- Entrepreneurship
- Community work
- Personal development

Traditional career platforms often try to narrow a person down
to one role or career path.

PlotPlanner must not do that.

The objective is to help users understand their possibilities,
explore their interests, develop their skills, pursue meaningful
goals and discover realistic opportunities.

PlotPlanner should help users answer five questions:

1. What am I interested in?
2. What can I learn or improve?
3. What can I realistically pursue right now?
4. How can I turn my existing skills into opportunities or income?
5. How can I make progress without neglecting the other parts
   of my life?

The system should adapt to the user's circumstances and progress.

It must never assume that the user has only one identity or
that every interest must become a career.

A person can be a software engineer, musician, artist, athlete
and entrepreneur simultaneously.

PlotPlanner should help them explore and organize these
possibilities rather than forcing them to choose one.

---

# 2. Core Product Principles

These principles govern every implementation decision.

## 2.1 Preserve Multiple Paths

Never force the user to select a single career direction.

Support multiple primary interests, secondary interests,
professional identities, creative pursuits and personal goals.

Users must be able to explore multiple paths simultaneously.

## 2.2 Personalization Must Be Evidence-Based

Recommendations must consider:

- Existing education
- Current occupation
- Professional experience
- Technical and creative skills
- Personal interests
- Available time
- Financial constraints
- Location
- Learning preferences
- Existing equipment and resources
- Personal goals
- Previous interactions
- Learning progress
- User feedback

Do not invent personal attributes or silently convert
speculation into established facts.

Distinguish between:

- Explicitly stated facts
- User preferences
- User goals
- Inferred interests
- Uncertain assumptions
- Recommendations requiring confirmation

## 2.3 Realistic, Actionable Advice

Recommendations must be practical.

Avoid generic advice such as:

- Work hard.
- Learn more.
- Build a portfolio.
- Network with people.

Instead, explain what the user should do, why it matters,
what they need, how to start and what a useful first result
would look like.

## 2.4 Personal Goals Matter Equally

PlotPlanner must support personal development alongside
professional development.

Examples:

- Learning guitar
- Singing
- Fitness
- Calisthenics
- Running
- Better sleep habits
- Creative writing
- Volunteering
- Social work
- Learning a language

Do not automatically turn personal goals into monetization
opportunities.

Only recommend monetization for a personal interest when
the user explicitly expresses that intention or requests
income-related advice.

## 2.5 Keep the Engineering Simple

Prefer straightforward solutions that solve the actual problem.

Do not introduce unnecessary abstractions, frameworks,
microservices, fallback chains or dependencies.

When an integration fails:

1. Identify the actual failure.
2. Return a meaningful error.
3. Log enough information to diagnose it.
4. Fix the underlying issue.

Do not silently return fabricated data or switch between
multiple unrelated providers to hide failures.

Retries are appropriate for documented transient failures,
not as a substitute for correct implementation.

## 2.6 Never Fabricate External Information

Do not invent:

- Job openings
- Salaries
- Course URLs
- Certifications
- Video links
- API responses
- Company requirements
- Learning resource availability

When current external information is required, retrieve it
from a reliable source.

Clearly distinguish verified information from estimates
and AI-generated suggestions.

## 2.7 User Control

Users must be able to:

- Edit their profiles.
- Add or remove interests.
- Update goals.
- Reject recommendations.
- Modify learning plans.
- Delete uploaded documents.
- Review their progress.
- Request changes to their plans.
- Delete their account and associated application data,
  subject to applicable retention requirements.

The AI assists the user. It does not own the user's identity.

---

# 3. Technology Stack

Use the following stack unless repository inspection
identifies an existing compatible implementation that
should be preserved.

## 3.1 Frontend

- React
- TypeScript
- Vite
- Tailwind CSS
- shadcn/ui
- React Router
- React Flow: @xyflow/react
- Recharts
- Framer Motion
- Lucide React
- TanStack Query
- Zod
- Supabase JavaScript client

Responsibilities:

- User interface
- Authentication flow
- Onboarding conversation
- Dashboard
- Interest graph
- Learning pathways
- Course progress
- Personal goals
- Opportunities dashboard
- Chat interface
- Document upload
- Analytics

The frontend must not contain business-critical AI logic,
private API keys or privileged database operations.

## 3.2 Backend

- Python
- FastAPI
- Pydantic
- Pydantic Settings
- SQLAlchemy 2
- Alembic
- Psycopg
- HTTPX
- PyMuPDF
- python-docx
- Python MCP SDK
- pytest
- HTTPX-based API tests

Use an LLM provider's official Python SDK or a small,
well-defined HTTP client.

Do not introduce an AI framework unless it materially
simplifies a real workflow.

## 3.3 Database and Authentication

- PostgreSQL
- Supabase Auth
- Supabase Storage when needed
- SQLAlchemy for backend database operations
- Alembic for schema migrations

PostgreSQL is the source of truth for application data.

Supabase Auth is the source of truth for user identity.

## 3.4 Deployment

Initial target:

- Frontend: Netlify or another suitable static host.
- Backend: A Python-compatible hosting service with an
  appropriate free tier, if available.
- Database: Supabase PostgreSQL.

Do not assume that all hosting, API usage or AI inference
will be free.

Avoid provider-specific coupling where a small abstraction
would make future migration straightforward.

---

# 4. Architecture

## 4.1 Architectural Style

Use a modular monolith.

The application starts as one FastAPI backend with
clearly separated business modules.

Do not create separately deployed microservices for
every feature.

The code must preserve boundaries that make future
service extraction possible when there is a genuine need.

Initial modules:

1. Authentication and profiles
2. Discovery and interests
3. Learning and courses
4. Goals and planning
5. Opportunities
6. Conversations and AI orchestration
7. Document processing
8. Analytics
9. External integrations
10. MCP tools

## 4.2 Request Lifecycle

The normal request flow is:

React
  -> FastAPI router
  -> Authentication and authorization
  -> Request validation
  -> Service
  -> Repository or external integration
  -> Database or external system
  -> Response schema
  -> JSON response
  -> React

Keep HTTP handling separate from application logic.

Route handlers should not contain large prompts, complex
business rules, database orchestration or provider-specific
AI workflows.

## 4.3 Target Backend Structure

Adapt this structure to the existing repository.

backend/
  app/
    main.py

    api/
      profile.py
      onboarding.py
      interests.py
      courses.py
      goals.py
      analytics.py
      opportunities.py
      chat.py
      documents.py

    core/
      config.py
      security.py
      exceptions.py

    db/
      database.py
      models.py
      repositories.py

    schemas/
      profile.py
      onboarding.py
      interest.py
      course.py
      goal.py
      opportunity.py
      chat.py
      document.py

    services/
      profile_service.py
      discovery_service.py
      course_service.py
      planning_service.py
      opportunity_service.py
      analytics_service.py
      conversation_service.py
      document_service.py

    ai/
      llm_client.py
      prompts.py
      structured_outputs.py
      orchestrator.py

    mcp/
      client.py
      tools.py

    integrations/
      youtube.py
      job_search.py
      learning_resources.py

  tests/
  alembic/
  requirements.txt
  .env.example

Do not create empty modules that have no implementation.

Do not split simple functionality into excessive numbers
of files merely to match the example.

Each module must have a clear responsibility.

## 4.4 Frontend Structure

frontend/
  src/
    app/
    components/
      layout/
      ui/
      onboarding/
      interests/
      courses/
      goals/
      opportunities/
      analytics/
      chat/

    pages/
      LoginPage.tsx
      OnboardingPage.tsx
      DashboardPage.tsx
      ExplorePage.tsx
      CoursesPage.tsx
      CourseDetailPage.tsx
      GoalsPage.tsx
      OpportunitiesPage.tsx
      ChatPage.tsx
      SettingsPage.tsx

    hooks/
    services/
      api.ts
      auth.ts

    types/
    schemas/
    lib/

    App.tsx
    main.tsx

  package.json

Adapt to the existing frontend instead of generating
duplicate components or configurations.

---

# 5. Authentication and User Identity

Use Supabase Auth.

Support:

- Email-based signup and login.
- Google login.
- Session persistence.
- Logout.
- Protected frontend routes.
- Protected backend endpoints.

## 5.1 Signup Flow

1. User creates an account.
2. Supabase authenticates the user.
3. Frontend obtains the authenticated session.
4. Frontend requests the user's profile.
5. If onboarding is incomplete, redirect to onboarding.
6. Otherwise, open the dashboard.

Do not create duplicate application profiles when the same
user signs in again.

## 5.2 Identity Model

Use the Supabase Auth UUID as the canonical user identifier.

profiles.user_id must reference auth.users.id.

Email is an attribute, not the application's primary key.

Do not trust user_id values supplied in request bodies
to determine which user's data can be accessed.

Derive the authenticated identity from the verified token.

## 5.3 Backend Authentication

Implement a reusable FastAPI authentication dependency.

It must:

1. Read the Bearer token.
2. Verify the Supabase access token using the supported
   Supabase signing-key/JWT verification mechanism.
3. Reject invalid or expired tokens.
4. Extract the authenticated user UUID.
5. Supply that identity to protected endpoints.

Use the correct JWT audience and issuer settings when
applicable.

Do not decode a JWT and trust its contents without
verifying its signature.

Do not expose service-role keys to the frontend.

## 5.4 Authorization

Every user-owned record must be accessed within the
authenticated user's authorization scope.

A user must not be able to access another user's:

- Profile
- Conversations
- Documents
- Courses
- Learning progress
- Goals
- Saved opportunities

Implement ownership checks in the backend and appropriate
Row Level Security policies in Supabase.

---

# 6. Product Feature A: Conversational Onboarding

## 6.1 Purpose

Discover enough about the user to create a useful initial
profile without overwhelming them with a long form.

The onboarding should feel like a natural conversation.

## 6.2 Experience

After login, show an animated introduction:

"How are you doing, {name}?"

Then:

"Ready to find your plot?"

Follow with:

"Let's start with what you're doing right now."

Continue naturally based on the user's responses.

Example:

Assistant:
"What are you currently doing, and what would you like
to explore next?"

User:
"I'm a software engineer, but I also want to learn music
production and improve my fitness."

The system should recognize these as separate areas rather
than trying to select one as the user's primary identity.

## 6.3 Adaptive Questions

Ask only questions that improve the resulting plan.

Possible topics:

- Current occupation or education
- Existing skills
- Interests
- Desired learning outcomes
- Career ambitions
- Personal goals
- Financial constraints
- Location
- Available time
- Current equipment
- Preferred learning methods

The questions must be dynamic.

Do not force every user through every question.

If the user says "I don't know", do not reject the input.

Instead, ask a simpler exploratory question.

Examples:

- What do you enjoy doing in your free time?
- What subjects or activities make you curious?
- What would you try if you had a free weekend?
- What skills do people usually ask you for help with?

Avoid asking for sensitive information that is not necessary
for the product.

## 6.4 Input Validation

Implement a validate_inputs function or equivalent
validation service.

It must:

- Validate request structure and data types.
- Detect empty or unusable responses.
- Preserve meaningful user text.
- Distinguish unknown answers from missing requests.
- Identify when more information is genuinely needed.
- Prevent malformed AI output from updating the profile.
- Return clear validation results.

Do not implement arbitrary validation rules that reject
reasonable personal responses.

Do not treat "I don't know" as a technical error.

## 6.5 Onboarding Completion

Onboarding is complete when sufficient information exists
to generate an initial set of useful interests and plans.

Do not require the user to answer every possible question.

On completion:

1. Save the structured profile.
2. Save the relevant conversation history.
3. Generate initial interest nodes.
4. Generate initial learning pathways.
5. Generate suitable initial goals.
6. Mark onboarding as complete.
7. Redirect to the dashboard.

Long-running AI work must not cause the browser request
to hang indefinitely.

For the first version, keep workflows synchronous where
they are predictably short. If a task becomes long-running,
introduce an explicit job/status workflow.

---

# 7. Product Feature B: Dynamic User Model

PlotPlanner must maintain a structured, evolving model
of the user's interests, skills and goals.

## 7.1 Information Sources

The profile may be updated from:

- Onboarding
- Chat conversations
- Explicit interest edits
- Goal creation and updates
- Resume uploads
- Other supported documents
- Course selections
- Learning progress
- User feedback

## 7.2 Structured Information

Store meaningful information as typed database records.

Do not rely exclusively on a large text field containing
the entire user's history.

Examples:

- Current occupation
- Professional experience
- Skill
- Interest
- Goal
- Preference
- Time constraint
- Career direction
- Learning preference

Where useful, store provenance:

- Source type
- Source record
- Timestamp
- Whether the information was user-confirmed

## 7.3 Updating the Model

After a relevant interaction:

1. Retrieve the necessary profile and recent context.
2. Identify possible updates.
3. Produce structured changes.
4. Validate the changes.
5. Persist only relevant updates.
6. Keep the original user statements available as history.
7. Ask for confirmation when an inference is uncertain
   or materially changes the user's profile.

Do not regenerate the entire profile after every message.

Do not remove existing interests merely because a new
interest appears.

## 7.4 Memory Boundaries

Use PostgreSQL for persistent user information.

Retrieve relevant conversation history when generating
recommendations.

Do not send the user's entire historical data to an LLM
on every request.

Minimize the amount of personal information sent to
external AI providers.

---

# 8. Product Feature C: Interactive Interest Network

## 8.1 Technology

Use React Flow through @xyflow/react.

Use custom React components for node presentation.

## 8.2 Graph Model

The graph must support:

- Main interests
- Secondary interests
- Skills
- Career paths
- Creative pursuits
- Personal goals
- Shared capabilities
- Connections between interests

Example:

Software Engineering
  -> AI/ML
  -> Backend Engineering
  -> DevOps
  -> Product Development
  -> UI/UX

Art and Design
  -> Painting
  -> Digital Art
  -> Graphic Design
  -> UI/UX
  -> Illustration

Music
  -> Guitar
  -> Singing
  -> Songwriting
  -> Music Production

Personal Development
  -> Fitness
  -> Calisthenics
  -> Running
  -> Sleep Habits

These are examples, not a fixed taxonomy.

Users must be able to create different structures.

## 8.3 Cross-Interest Relationships

The graph must support meaningful overlapping skills.

For example, UI/UX can connect software engineering
with art and design.

A node may have multiple valid parent relationships.

Do not force every node into a strict tree.

Use a graph model.

## 8.4 Node Interactions

Users must be able to:

- Add an interest.
- Edit an interest.
- Remove an interest.
- Connect related interests.
- Inspect a node's details.
- Open related courses.
- View relevant goals.
- View progress.
- Explore suggested connections.

Persist meaningful edits to PostgreSQL.

Do not persist transient visual positions on every drag
unless needed. Debounce or save layout changes explicitly.

## 8.5 Visual Semantics

Main nodes represent major areas of exploration or
identity.

Smaller nodes represent skills, subfields or activities.

Connections represent relationships, shared skills
or possible transitions.

Progress indicators must reflect actual stored data.

Distinguish between:

- Completed course progress
- Skill evidence
- User confidence
- AI-suggested relevance

Do not present a speculative AI estimate as an objective
career compatibility percentage.

Use labels and tooltips to explain each metric.

## 8.6 Graph Data

Keep graph data separate from presentation.

The backend should return structured nodes and edges.

React Flow should render that data and manage visual
interactions.

Do not generate graph layout directly from unvalidated
LLM text.

---

# 9. Product Feature D: Learning Pathways and Courses

## 9.1 Purpose

Generate structured learning pathways tailored to the
user's current skills, interests, available time and goals.

Every meaningful interest should be eligible for its own
learning pathway.

Examples:

- AI/ML engineering
- Backend engineering
- Music production
- Guitar
- Singing
- Songwriting
- Painting
- Film direction
- Fitness
- Calisthenics

Do not assume that every pathway needs a certificate.

## 9.2 Course Structure

A course should include:

- Title
- Description
- Associated interest
- Learning objective
- Difficulty level
- Estimated duration
- Prerequisites
- Ordered modules
- Lessons or activities
- External resources
- Practical assignments
- Completion criteria
- Optional assessments
- Relevant certifications, when appropriate

## 9.3 Example

Music Production:

Stage 1: Foundations

- Rhythm and tempo
- Basic music theory
- Digital audio workstations
- Basic audio terminology

Stage 2: Production

- Recording
- MIDI
- Arrangement
- Sound selection
- Mixing fundamentals

Stage 3: Practice

- Recreate a simple track
- Produce an original loop
- Complete a short composition
- Request feedback

Stage 4: Portfolio

- Produce a complete track
- Document the production process
- Publish a portfolio example

Stage 5: Optional Earning Path

Only when the user wants monetization:

- Freelance opportunities
- Working with independent artists
- Portfolio presentation
- Client communication
- Pricing experiments

This structure is illustrative. Generated pathways should
adapt to the user's existing knowledge.

## 9.4 Resource Requirements

Support:

- YouTube videos
- Official documentation
- Free tutorials
- Open learning materials
- MOOCs
- Professional certification courses
- Books and other legitimate resources
- Practical projects

Clearly identify whether a resource is:

- Free
- Free with optional paid features
- Paid
- Unknown or not verified

A free course and a paid certification are not the same.

Do not label a paid course as free simply because a
preview or trial exists.

Use official provider information where possible.

## 9.5 External Resource Validation

When resources come from external APIs:

1. Retrieve the resource.
2. Validate the returned fields.
3. Store the canonical URL and provider.
4. Preserve the retrieval timestamp.
5. Check availability when necessary.
6. Clearly represent unavailable resources.

Do not invent URLs to fill empty course sections.

If a provider returns no suitable resources, state that
no verified results were found.

## 9.6 Course Progress

Users must be able to:

- Enroll in a course.
- Start a module.
- Mark a lesson complete.
- Submit a project or reflection.
- Resume a course.
- Pause a course.
- Abandon a course.
- View completed modules.
- See remaining activities.

Progress must be calculated from persisted completion
records, not generated by an LLM.

## 9.7 Course Regeneration

When interests or circumstances change, recommend
adjustments rather than blindly replacing existing courses.

Preserve completion history.

If a pathway is materially updated, record the new
version or preserve the previous version where necessary.

---

# 10. Product Feature E: Personal Goals and Planning

Support goals that are not career-related.

Examples:

- Improve fitness
- Learn guitar
- Practice singing
- Develop flexibility
- Start running
- Improve sleep consistency
- Write songs
- Complete creative projects
- Volunteer regularly

## 10.1 Goal Model

Each goal should support:

- Title
- Description
- Category
- User-defined priority
- Target outcome
- Optional target date
- Available time
- Current status
- Progress records
- Related interests
- Related learning activities

## 10.2 Action Plans

Generate practical, adjustable plans.

For example:

Goal: Learn guitar.

Plan:

- Practice basic chords.
- Learn a simple rhythm.
- Practice chord transitions.
- Learn a complete song.
- Record a short performance.
- Review progress.

The plan should adapt to the user's experience and
available practice time.

Do not force unrealistic daily workloads.

## 10.3 Health-Related Boundaries

PlotPlanner may support general fitness and wellness
planning.

It must not diagnose medical conditions.

It must not present AI-generated medical advice as a
substitute for professional care.

Account for stated physical limitations and avoid
recommending unsafe training or extreme routines.

For medical or mental health concerns, provide
appropriately cautious guidance and encourage professional
support when warranted.

Do not infer sensitive diagnoses from user behavior.

---

# 11. Product Feature F: Things That Can Pay for You

This is a major product capability.

The objective is to help users discover realistic ways
to use their existing skills to earn money, find jobs
or build a business.

It must not promise income.

## 11.1 Opportunity Categories

Support:

1. Full-time jobs
2. Part-time jobs
3. Freelance work
4. Contract work
5. Creative commissions
6. Digital products
7. Small service businesses
8. Entrepreneurship
9. Skill-building opportunities that improve employability

## 11.2 Personalized Recommendations

Evaluate opportunities against:

- Current skills
- Experience level
- Education where relevant
- Portfolio evidence
- Location
- Work preferences
- Available time
- Salary expectations
- Financial constraints
- Existing employment
- Willingness to learn

The goal is to recommend both realistic near-term
opportunities and reasonable stretch opportunities.

Do not limit users to jobs that match their current
experience exactly.

Clearly explain the difference between:

- Ready to apply now
- Plausible stretch opportunity
- Requires additional preparation

## 11.3 Current Job Search

Use legitimate job-search providers or public APIs
when available and permitted.

Store relevant information:

- Job title
- Company
- Location
- Employment type
- Salary range, when provided
- Experience requirements
- Required skills
- Source
- Canonical job URL
- Date retrieved
- Closing date, if known

Never fabricate an active job listing.

Do not scrape websites in violation of their terms.

If reliable job-search access is unavailable, explain
the limitation and provide verified employer career
pages or other legitimate resources where possible.

## 11.4 Salary Guidance

Salary recommendations must be contextual.

Consider:

- Geography
- Experience
- Role
- Industry
- Employment type
- Relevant skills
- Available salary evidence

Clearly distinguish:

- Employer-provided salary
- Market salary estimate
- AI-generated expectation

Do not promise a salary based only on an experience label.

For example, entry-level software engineers in one city
may have very different compensation from engineers in
another city or industry.

## 11.5 Side Hustles

For every relevant side-hustle recommendation, explain:

1. What service or product to offer.
2. Who might pay for it.
3. What is needed to start.
4. How to build a small portfolio.
5. Where to find potential customers.
6. How to test demand.
7. How to estimate costs and pricing.
8. What to do during the first week.
9. How to evaluate results.
10. What to improve next.

Examples:

Software engineering:

- Build small business websites.
- Create simple automation tools.
- Offer website maintenance.
- Build niche internal tools.
- Offer clearly scoped freelance development.

Art and design:

- Sell original paintings.
- Offer commissioned artwork.
- Sell digital illustrations.
- Explore print-on-demand.
- Offer graphic design services.

Music:

- Offer music production services when skilled enough.
- Collaborate with independent artists.
- Build a production portfolio.
- Explore paid projects after developing the required
  skills and demonstrating quality.

These are possible pathways, not guaranteed opportunities.

## 11.6 Main Hustle and Side Hustle

The platform should distinguish between:

- Primary employment or main professional path.
- Secondary earning opportunities.
- Creative pursuits.
- Personal development goals.

A user's main professional path should not erase their
other interests.

The user must be able to change which paths receive
priority as their circumstances evolve.

Do not automatically monetize personal goals.

---

# 12. Product Feature G: Persistent AI Chat

Provide an AI chat interface throughout the application.

Users should be able to ask questions such as:

- What should I work on this week?
- How can I balance work and guitar practice?
- What should I learn after completing this module?
- Can I start freelancing with my current skills?
- How does music production connect to software engineering?
- Can you adjust my plan because I have less free time?
- What opportunities should I explore next?

## 12.1 Chat Context

Use relevant information from:

- User profile
- Interests
- Goals
- Active learning pathways
- Learning progress
- Relevant conversation history
- Uploaded documents, where appropriate
- Current opportunities, when requested

Retrieve only the context required for the current request.

## 12.2 Structured AI Output

Where an AI workflow modifies application data,
require structured output.

Use Pydantic models for validation.

Do not allow free-form model text to directly modify
database records.

The service layer must validate proposed changes before
persisting them.

## 12.3 Tool Selection

The AI orchestration layer should call external tools
only when needed.

Examples:

A question about a saved course may require only a
database query.

A question about currently available jobs may require
a job-search integration.

A request to discover YouTube learning resources may
require the YouTube integration.

Do not invoke every MCP tool on every message.

## 12.4 Errors

If the LLM provider fails:

- Return a clear, controlled error.
- Log the failure without exposing secrets.
- Preserve the user's message.
- Do not fabricate a response and present it as real
  AI-generated advice.

Do not create arbitrary chains of alternative models.

---

# 13. Product Feature H: Document and Resume Processing

Allow users to upload supported documents.

Initial supported formats:

- PDF
- DOCX
- TXT

Do not accept arbitrary file types by default.

## 13.1 Processing Flow

1. Authenticate the user.
2. Validate the file type and size.
3. Store the file securely.
4. Extract text.
5. Record processing status.
6. Analyze relevant information.
7. Produce structured extraction results.
8. Allow useful information to enrich the user profile.
9. Preserve the source document and its provenance.
10. Allow the user to delete the document.

## 13.2 Extraction

For a resume, extract information such as:

- Skills
- Education
- Employment history
- Projects
- Certifications
- Portfolio links
- Relevant experience

Extraction results must be treated as potentially
incorrect until validated.

Do not invent qualifications or employment history.

Allow users to review important extracted facts.

## 13.3 Security

- Enforce file-size limits.
- Validate actual file content where practical.
- Use private storage.
- Enforce user ownership.
- Avoid public document URLs.
- Do not execute uploaded files.
- Prevent uploaded documents from overriding system
  instructions or controlling tool execution.
- Do not expose raw extracted documents to other users.
- Support deletion of stored files and derived data.

For the initial demo, process documents synchronously
when processing is short and bounded.

Introduce background jobs only if processing time
or reliability requirements justify them.

---

# 14. Product Feature I: Analytics

The analytics dashboard should reflect actual user activity.

Support:

- Number of active interests
- Active learning pathways
- Completed modules
- Course completion
- Goal progress
- Learning activity over time
- Time spent, when reliably tracked
- Saved opportunities
- Skills demonstrated through completed projects
- Changes in user priorities

## 14.1 Interest Network Analytics

Use the interest graph to show relationships between
interests and progress in associated learning pathways.

Do not confuse visual connection strength with objective
career suitability.

Use clearly defined metrics.

## 14.2 Progress Calculation

Calculate progress from database records.

For example:

Course completion percentage =
completed required modules / total required modules * 100

Define how optional modules affect the calculation.

Do not ask the LLM to invent progress percentages.

## 14.3 Engagement

Use actual engagement data to make suggestions.

For example:

If a user repeatedly practices guitar but has not
started a particular course, suggest a smaller learning
activity or a more appropriate course.

Do not silently remove other interests because they
receive less engagement.

---

# 15. Database Design

Use PostgreSQL.

Use UUIDs for user-owned and major application entities.

Use foreign keys, indexes and constraints where
appropriate.

The exact schema should be adapted to the existing
database before migrations are generated.

## 15.1 profiles

Fields:

- user_id: UUID, primary key, references auth.users.id
- display_name
- location
- current_occupation
- education_summary
- experience_summary
- onboarding_completed
- created_at
- updated_at

Do not duplicate sensitive authentication credentials
inside the application profile.

## 15.2 user_preferences

Fields:

- id
- user_id
- preference_key
- preference_value
- created_at
- updated_at

Use a validated representation for preference values.

Avoid introducing a generic key-value system where
a dedicated typed field is clearly more appropriate.

## 15.3 interests

Fields:

- id
- user_id
- name
- description
- category
- interest_type
- priority
- source
- confidence, when meaningful
- created_at
- updated_at

Interest types may include:

- Professional
- Creative
- Personal
- Educational
- Entrepreneurial

The taxonomy must remain extensible.

## 15.4 interest_relationships

Fields:

- id
- user_id
- source_interest_id
- target_interest_id
- relationship_type
- created_at

Examples of relationships:

- Related to
- Develops into
- Shares skills with
- Supports
- Overlaps with

Prevent invalid self-references and unintended duplicate
relationships.

Ensure both interests belong to the authorized user.

## 15.5 goals

Fields:

- id
- user_id
- title
- description
- category
- target_outcome
- priority
- status
- target_date
- created_at
- updated_at

## 15.6 conversations

Fields:

- id
- user_id
- title
- created_at
- updated_at

## 15.7 messages

Fields:

- id
- conversation_id
- user_id
- role
- content
- created_at

Use a constrained set of roles.

Ensure messages can only be accessed through an
authorized conversation.

## 15.8 courses

Fields:

- id
- user_id
- interest_id
- title
- description
- difficulty
- estimated_duration
- status
- version
- created_at
- updated_at

Distinguish generated course templates from user-specific
course enrollments if reusable templates are introduced.

Do not duplicate entire course structures unnecessarily.

## 15.9 course_modules

Fields:

- id
- course_id
- title
- description
- position
- learning_objectives
- completion_criteria

## 15.10 learning_resources

Fields:

- id
- module_id
- title
- provider
- canonical_url
- resource_type
- cost_status
- retrieved_at
- verification_status

Do not treat an unverified resource as verified.

## 15.11 user_courses

Fields:

- id
- user_id
- course_id
- status
- started_at
- completed_at
- created_at

## 15.12 learning_progress

Fields:

- id
- user_id
- user_course_id
- module_id
- status
- completed_at
- notes

Use constraints to prevent duplicate completion records
where the model expects one record per user/module.

## 15.13 documents

Fields:

- id
- user_id
- filename
- storage_path
- content_type
- processing_status
- extracted_text_reference, when required
- created_at
- processed_at

Keep extracted document content private.

## 15.14 opportunities

Fields:

- id
- user_id, nullable only when supporting shared catalogues
- opportunity_type
- title
- description
- source
- canonical_url
- location
- compensation_min
- compensation_max
- currency
- requirements
- retrieved_at
- closing_at, when known

Represent unknown compensation explicitly.

Do not convert missing compensation into zero.

## 15.15 user_opportunities

Fields:

- id
- user_id
- opportunity_id
- status
- notes
- created_at
- updated_at

## 15.16 Migrations

Use Alembic.

All schema changes must be represented by migrations.

Do not modify production tables manually as the normal
development workflow.

Before generating migrations, inspect existing tables,
constraints and relationships.

Never drop existing user data as a shortcut.

---

# 16. API Design

Use the prefix:

/api/v1

Use consistent response schemas, validation and error
handling.

Protect private endpoints with authentication.

The following is the target API contract. Reuse existing
compatible endpoints when they already implement the
same responsibility.

## 16.1 Health

GET /health

Purpose:
- Confirm that the application is running.

GET /ready

Purpose:
- Check whether required dependencies are ready.

Do not expose credentials or internal infrastructure
details in health responses.

## 16.2 Profiles

GET /api/v1/profile

Purpose:
- Retrieve the authenticated user's profile.

PATCH /api/v1/profile

Purpose:
- Update editable profile fields.

POST /api/v1/onboarding/turn

Purpose:
- Submit a user's onboarding response.
- Continue the adaptive discovery conversation.
- Return the next prompt or onboarding completion result.

GET /api/v1/onboarding/status

Purpose:
- Retrieve onboarding status.

## 16.3 Interests

GET /api/v1/interests

Purpose:
- List the authenticated user's interests.

POST /api/v1/interests

Purpose:
- Create an interest.

PATCH /api/v1/interests/{interest_id}

Purpose:
- Update an interest.

DELETE /api/v1/interests/{interest_id}

Purpose:
- Delete an interest and handle its relationships
  according to defined integrity rules.

GET /api/v1/interests/graph

Purpose:
- Return nodes and edges for the interest visualization.

POST /api/v1/interests/relationships

Purpose:
- Create a validated relationship between interests.

DELETE /api/v1/interests/relationships/{relationship_id}

Purpose:
- Remove a relationship.

## 16.4 Courses

GET /api/v1/courses

Purpose:
- List the user's courses.

POST /api/v1/courses/generate

Purpose:
- Generate a learning pathway for one or more selected
  interests or goals.

GET /api/v1/courses/{course_id}

Purpose:
- Retrieve a course and its modules.

POST /api/v1/courses/{course_id}/enroll

Purpose:
- Enroll the user in a course.

PATCH /api/v1/courses/{course_id}/modules/{module_id}/progress

Purpose:
- Update the user's module progress.

DELETE /api/v1/courses/{course_id}/enrollment

Purpose:
- Remove an enrollment without destroying shared course
  content or unrelated progress history.

## 16.5 Goals

GET /api/v1/goals

Purpose:
- List the user's goals.

POST /api/v1/goals

Purpose:
- Create a goal.

PATCH /api/v1/goals/{goal_id}

Purpose:
- Update a goal.

DELETE /api/v1/goals/{goal_id}

Purpose:
- Delete a goal.

POST /api/v1/goals/{goal_id}/plan

Purpose:
- Generate an actionable plan for the goal.

## 16.6 Opportunities

GET /api/v1/opportunities

Purpose:
- Retrieve saved opportunities and relevant results
  from supported sources.

POST /api/v1/opportunities/search

Purpose:
- Search for jobs or other requested opportunities.

POST /api/v1/opportunities/plan

Purpose:
- Generate a practical earning plan from the user's
  existing skills and stated objectives.

POST /api/v1/opportunities/{opportunity_id}/save

Purpose:
- Save an opportunity.

PATCH /api/v1/opportunities/{opportunity_id}/status

Purpose:
- Update the user's status for an opportunity.

## 16.7 Chat

POST /api/v1/chat

Purpose:
- Submit a message and obtain an AI response.

GET /api/v1/chat/conversations

Purpose:
- List the user's conversations.

GET /api/v1/chat/conversations/{conversation_id}

Purpose:
- Retrieve an authorized conversation.

DELETE /api/v1/chat/conversations/{conversation_id}

Purpose:
- Delete a conversation and its associated messages.

## 16.8 Documents

POST /api/v1/documents

Purpose:
- Upload and process an authorized user's document.

GET /api/v1/documents

Purpose:
- List the user's documents and processing status.

GET /api/v1/documents/{document_id}

Purpose:
- Retrieve document metadata and permitted extraction
  results.

DELETE /api/v1/documents/{document_id}

Purpose:
- Delete the document and its associated stored content.

## 16.9 Analytics

GET /api/v1/analytics/overview

Purpose:
- Return actual learning and goal progress metrics.

GET /api/v1/analytics/interests

Purpose:
- Return interest-level progress and relationships.

GET /api/v1/analytics/activity

Purpose:
- Return time-based activity and completion records.

## 16.10 Endpoint Requirements

Do not implement every endpoint before its underlying
feature exists.

Implement endpoints incrementally alongside the relevant
database models, services and tests.

Use appropriate HTTP methods and status codes.

Examples:

- 200: Successful read or update.
- 201: Resource created.
- 204: Successful deletion without a response body.
- 401: Missing or invalid authentication.
- 403: Authenticated but unauthorized operation.
- 404: Resource not found or not accessible.
- 409: Conflicting state.
- 422: Request validation failure.
- 429: Rate limit exceeded.
- 502 or 503: Relevant upstream or dependency failure.

Do not expose raw stack traces, SQL statements or secrets
to clients.

---

# 17. AI Integration Architecture

## 17.1 Provider Boundary

Implement a small LLM client abstraction.

The application should not depend on provider-specific
response formats throughout the codebase.

Keep provider-specific request and response handling
inside the integration boundary.

Do not create an unnecessarily generic multi-provider
framework.

Start with one configured provider.

## 17.2 Structured Outputs

Use Pydantic schemas for workflows that require structured
data.

Examples:

- Profile extraction
- Interest suggestions
- Onboarding questions
- Course generation
- Goal planning
- Opportunity analysis
- Chat action proposals

Validate generated outputs before using them.

An invalid AI response must not silently become an empty,
incorrect or fabricated successful result.

## 17.3 AI Workflow Separation

Implement clear application workflows for:

1. Discovery and profile updates.
2. Learning pathway generation.
3. Goal planning.
4. Opportunity analysis.
5. Chat orchestration.
6. Document analysis.

These workflows may share the same LLM client.

Do not introduce separate agents merely because the
application has multiple features.

Use deterministic Python logic wherever possible.

## 17.4 Prompt Management

Keep substantial prompts out of route handlers.

Store them in the AI prompt module or separate versioned
prompt files where appropriate.

Prompts must specify:

- Task
- Available context
- Expected output schema
- Constraints
- Source-verification requirements
- Behavior when information is missing

Do not include API keys or secrets in prompts.

## 17.5 Context Selection

Retrieve only the information relevant to the request.

Use recent conversation history, structured profile
data, relevant goals and learning progress.

Summarize older conversation context when necessary.

Do not include unrelated personal documents in every
LLM request.

## 17.6 LLM Cost Controls

Implement:

- Configurable model selection.
- Request timeouts.
- Reasonable input size limits.
- Usage logging where supported.
- Basic per-user rate limits.
- Appropriate maximum output sizes.
- Explicit error handling.

Do not silently switch models or fabricate a successful
response when the configured provider fails.

---

# 18. MCP Integration

Use the Python MCP SDK where external tool integration
is useful.

## 18.1 Responsibilities

MCP tools should provide access to capabilities such as:

- Learning resource discovery.
- Job searches.
- Course details.
- Other relevant external systems.

The application should use the simplest interface that
solves the problem.

If a direct REST API call is sufficient and does not
benefit from MCP, use the direct API.

## 18.2 Tool Contracts

Every tool must have:

- A clear name.
- A description.
- A validated input schema.
- A defined output format.
- Timeout behavior.
- Documented errors.
- Appropriate access controls.

Do not expose arbitrary database operations as MCP tools.

Do not let external tools perform privileged actions
without authorization and validation.

## 18.3 Initial Tool Set

Potential tools:

- search_learning_resources
- get_course_details
- search_jobs

Implement only the tools required by the first workflows.

These names are proposed interfaces and must be checked
against the selected providers and actual implementations.

## 18.4 Tool Selection

The AI orchestration layer must decide which tools are
relevant to the current task.

A simple profile update should not invoke a job search.

A question about a saved course should not require a
YouTube API call unless resource discovery is requested.

## 18.5 MCP Reliability

Set explicit timeouts.

Propagate meaningful failures.

Do not retry indefinitely.

Use retries only for documented transient failures,
with sensible limits.

Do not return fake tool results.

---

# 19. External Learning Resources

## 19.1 YouTube

Use the YouTube Data API when available and configured.

Return:

- Video title
- Channel
- Canonical URL
- Duration, when available
- Publication information, when available
- Retrieval timestamp

Respect API quotas and applicable terms.

Do not invent video identifiers or URLs.

## 19.2 Other Learning Platforms

Use official APIs, public catalogues or permitted
resource-discovery methods.

Do not assume every platform provides a public API.

Do not assume paid platforms provide unrestricted free
course access.

When a resource is paid, identify it as paid.

When its cost cannot be verified, mark the cost as unknown.

## 19.3 Resource Relevance

Rank resources using factors such as:

- Topic relevance
- User skill level
- Learning objective
- Resource quality
- Cost preference
- Availability
- Prerequisites

Do not rank solely from an LLM's unsupported claim
that a resource is excellent.

---

# 20. Security and Privacy

Security is part of the implementation, not a final
optional phase.

Required protections:

- Verified authentication.
- User-level authorization.
- Input validation.
- Parameterized database operations.
- Secret management.
- File-size restrictions.
- File-type validation.
- Private document storage.
- Rate limiting for sensitive or expensive endpoints.
- Safe error responses.
- Ownership checks.
- Appropriate database constraints.
- HTTPS in deployed environments.
- Logging that avoids sensitive data.

Never log:

- Access tokens
- Passwords
- API keys
- Full authentication headers
- Unnecessary sensitive document content

Do not store secrets in Git.

Use least-privilege access.

Ensure uploaded documents and retrieved web content
are treated as untrusted input.

Do not allow prompt injection from a document or external
webpage to override system instructions or grant access
to privileged tools.

Implement account and data deletion behavior that
covers application records and stored documents.

Document any retention limitations.

---

# 21. Error Handling and Observability

Use consistent application errors.

Return structured error responses without exposing
internal implementation details.

Log relevant diagnostic information on the server.

Distinguish between:

- Invalid client requests
- Authentication failures
- Authorization failures
- Database failures
- AI provider failures
- External API failures
- MCP tool failures
- Unexpected application bugs

Do not catch every exception and return an empty result.

Do not convert all errors into HTTP 200 responses.

Unexpected failures should remain visible in logs and
appropriate monitoring.

Health endpoints must not reveal credentials or sensitive
infrastructure configuration.

---

# 22. Testing

Use pytest for backend tests.

Use HTTPX for FastAPI endpoint tests.

Use Vitest and React Testing Library for frontend tests.

## 22.1 Backend Tests

Test:

- Request validation.
- Authentication.
- Authorization.
- Profile CRUD.
- Interest CRUD.
- Graph relationships.
- Course creation and progress.
- Goal planning.
- Opportunity handling.
- Conversation persistence.
- Document validation.
- AI output validation.
- External integration errors.
- Database integrity.

## 22.2 AI Tests

Use deterministic test fixtures for application logic.

Mock the LLM client in ordinary unit tests.

Test malformed model outputs and provider failures.

Do not require paid AI API calls to run the normal
test suite.

Add a separate optional integration test for a real
provider when credentials are configured.

## 22.3 Frontend Tests

Test:

- Login and logout behavior.
- Protected routes.
- Onboarding progression.
- Graph interactions.
- Course progress updates.
- Goal creation and editing.
- Opportunity display.
- Loading and error states.

## 22.4 Acceptance Testing

Every implemented feature must have a clear way to
verify its behavior.

Do not mark a feature complete merely because the UI
renders or the endpoint returns HTTP 200.

---

# 23. Frontend Experience and Design Direction

PlotPlanner should feel like a personal exploration
workspace rather than a conventional corporate dashboard.

The design should communicate:

- Exploration
- Possibility
- Personal ownership
- Creative freedom
- Progress
- Clarity

Use restrained, consistent styling.

Avoid excessive cards, gradients, decorative charts
and unnecessary animations.

## 23.1 Onboarding

Use large typography, subtle animation and a conversational
layout.

Questions should appear progressively.

Preserve the conversation when the user navigates away
or reloads the page.

Provide a way to review or edit information before
finalizing the initial profile.

## 23.2 Dashboard

Show:

- Welcome message.
- Interest network.
- Active courses.
- Current goals.
- Recent progress.
- Relevant next actions.
- Selected opportunities.

Avoid overwhelming the user with every available metric.

## 23.3 Interest Graph

Make the graph interactive and readable.

Support zooming, panning, selecting nodes and opening
details.

Provide an accessible list or alternative representation
for users who cannot use the graph effectively.

## 23.4 Courses

Display learning pathways as clear, navigable cards.

Each card should communicate:

- What the user will learn.
- Why the pathway is relevant.
- Estimated effort.
- Current progress.
- The next activity.

## 23.5 Opportunities

Separate current job opportunities from longer-term
career development and side-hustle suggestions.

Make source links visible.

Clearly label estimates and unknown information.

## 23.6 Accessibility

Use semantic HTML, keyboard-accessible controls,
visible focus states, appropriate contrast and
meaningful labels.

Do not rely on color alone to convey graph relationships
or progress.

## 23.7 Responsive Layout

Support desktop and mobile layouts.

The desktop dashboard can provide a richer graph
experience, while mobile should retain access to
interests, courses, goals and chat.

---

# 24. Environment Configuration

Use Pydantic Settings or an equivalent centralized
configuration system.

Do not read environment variables independently
throughout the application.

Provide a safe .env.example containing placeholders.

Expected configuration categories:

- Application environment
- API prefix
- Database connection
- Supabase URL
- JWT verification configuration
- LLM provider
- LLM API key
- LLM model
- External API credentials
- Frontend origin
- File-size limits
- Timeouts and usage limits

Validate required configuration during startup or
before the corresponding integration is used.

Never log secret values.

The frontend must use only public configuration.

---

# 25. Development Workflow

The implementation must proceed incrementally.

Do not attempt to generate every feature in one enormous
code-generation step.

## Phase 0: Repository Audit

Before modifying anything:

1. Inspect the complete repository structure.
2. Read existing backend entry points.
3. Inspect profile_api.py, RAG_KB_api.py and mcp_tools.py
   if they exist.
4. Inspect requirements.txt and Python configuration.
5. Inspect the frontend package.json and source structure.
6. Inspect existing database models and migrations.
7. Inspect current authentication behavior.
8. Identify implemented and incomplete features.
9. Identify broken functionality and technical debt.
10. Report the actual current architecture.

Do not invent repository contents.

Do not overwrite working files without understanding them.

## Phase 1: Foundation

Implement or verify:

- Backend application startup.
- Central configuration.
- Database connection.
- Alembic setup.
- Supabase token verification.
- Authentication dependency.
- Error handling.
- Health and readiness endpoints.
- Frontend API client.
- Protected frontend routes.
- Basic automated tests.

Acceptance criteria:

- Backend starts successfully.
- Frontend starts successfully.
- Health endpoint works.
- Database connection can be verified.
- Invalid tokens are rejected.
- Authenticated users can access only their own data.
- Tests pass.

## Phase 2: Profiles and Onboarding

Implement:

- Profile retrieval and updates.
- Onboarding conversation.
- Adaptive question generation.
- Input validation.
- Structured profile extraction.
- Onboarding persistence.
- Onboarding completion status.

Acceptance criteria:

- A user can sign in.
- A new user can complete onboarding.
- A returning user can resume incomplete onboarding.
- User information persists.
- "I don't know" receives an appropriate response.
- Invalid AI output does not corrupt the profile.

## Phase 3: Interests and Graph

Implement:

- Interest CRUD.
- Interest relationships.
- Graph API.
- Interactive React Flow graph.
- Node editing.
- Node creation and deletion.
- Progress indicators based on real records.

Acceptance criteria:

- Graph data comes from the backend.
- Changes persist after reload.
- Cross-interest relationships work.
- Deleting an interest preserves database integrity.
- Graph metrics reflect actual data.

## Phase 4: Learning Pathways

Implement:

- Course generation.
- Course persistence.
- Modules and activities.
- Learning resource integration.
- Enrollment.
- Progress updates.
- Course dashboard.
- Course detail view.

Acceptance criteria:

- A user can generate a pathway.
- The pathway contains structured modules.
- Resources have valid URLs or are explicitly marked
  as unverified.
- Paid and free resources are distinguished.
- Progress persists.
- Course completion is calculated correctly.

## Phase 5: Personal Goals

Implement:

- Goal CRUD.
- Goal planning.
- Goal progress.
- Personal goal dashboard.
- Connections between goals and interests.

Acceptance criteria:

- Goals persist.
- Users can update priorities.
- Generated plans are actionable.
- Personal goals do not automatically become
  monetization opportunities.

## Phase 6: Opportunities

Implement:

- Job-search integration.
- Opportunity models.
- Source verification.
- Saved opportunities.
- Earning plan generation.
- Side-hustle planning.
- Opportunity dashboard.

Acceptance criteria:

- External listings are not fabricated.
- Source URLs are preserved.
- Salary estimates are appropriately qualified.
- Recommendations reflect user skills and constraints.
- The system distinguishes current opportunities
  from long-term possibilities.

## Phase 7: Persistent Chat

Implement:

- Conversation creation.
- Message persistence.
- Context retrieval.
- Structured action proposals.
- Relevant tool selection.
- AI response handling.
- Error states.

Acceptance criteria:

- Users can resume conversations.
- Chat can retrieve relevant profile context.
- AI actions are validated before persistence.
- Provider failures are visible and handled safely.
- Tool calls are limited to relevant operations.

## Phase 8: Documents

Implement:

- Secure upload.
- PDF/DOCX/TXT extraction.
- Processing status.
- Structured extraction.
- User review.
- Profile enrichment.
- Document deletion.

Acceptance criteria:

- Unsupported files are rejected.
- File limits are enforced.
- Extracted information is associated with the correct
  user.
- The user can review important extracted facts.
- Deleting a document removes its stored content and
  applicable derived records.

## Phase 9: Analytics and Adaptation

Implement:

- Learning analytics.
- Goal progress.
- Interest-level progress.
- Activity history.
- Relevant recommendations based on actual behavior.

Acceptance criteria:

- Metrics come from stored data.
- Progress calculations are reproducible.
- New interests do not erase existing paths.
- The user can control priorities.
- Suggestions remain grounded in available evidence.

## Phase 10: Deployment Readiness

Implement and verify:

- Production configuration.
- Database migrations.
- CORS configuration.
- Authentication and authorization.
- Logging.
- Usage limits.
- Build checks.
- Automated tests.
- Deployment instructions.
- Environment variable documentation.

Do not claim production readiness before testing
authentication, data ownership, errors, migrations and
the actual deployment configuration.

---

# 26. Cursor Implementation Rules

These rules are mandatory.

## Rule 1: Inspect Before Editing

Always inspect existing files before creating or
replacing them.

Reuse existing compatible implementations.

Do not recreate the project from scratch.

## Rule 2: Follow Existing Reality

The repository may differ from the target architecture.

Identify the differences and adapt incrementally.

Never assume a feature exists merely because it is
described in this README.

## Rule 3: Work in Small Phases

Complete one implementation phase at a time.

For each phase:

1. Inspect relevant files.
2. Explain the implementation plan.
3. Identify required schema changes.
4. Implement the smallest coherent change.
5. Add or update tests.
6. Run relevant tests and build checks.
7. Fix failures.
8. Summarize changed files and remaining work.

Do not regenerate unrelated modules.

## Rule 4: No Unnecessary Fallbacks

Do not add alternative execution paths merely to
avoid diagnosing a failure.

Do not return mock data in production paths.

Use deterministic behavior when appropriate.

Use explicit errors for missing dependencies and
invalid configuration.

## Rule 5: Keep Endpoints Thin

Routes should validate requests, invoke services and
return defined responses.

Move complex workflows into services.

Keep database operations behind clear repository
or data-access functions when this improves maintainability.

Do not introduce repository abstractions that add no
useful separation to a simple operation.

## Rule 6: Use Typed Contracts

Use Pydantic models for backend request and response
schemas.

Use TypeScript types for frontend API contracts.

Keep frontend and backend contracts aligned.

Do not use untyped dictionaries as the default
representation for every application object.

## Rule 7: Secure Every User-Owned Resource

Every protected operation must derive identity from
verified authentication.

Test access boundaries between users.

Do not trust ownership claims made in request bodies.

## Rule 8: Keep Secrets Out of Source Control

Use environment variables and server-side configuration.

Never commit actual credentials.

Never expose server secrets to React.

## Rule 9: Verify External Information

Do not invent jobs, salaries, learning resources or
API responses.

Keep source information and retrieval timestamps.

## Rule 10: Do Not Overbuild

Do not add:

- Unnecessary microservices
- Kubernetes
- Redis
- Celery
- A vector database without a demonstrated need
- Multiple overlapping AI frameworks
- Generic abstractions for hypothetical future use
- Excessive fallback chains

## Rule 11: Do Not Claim Untested Success

Run the available checks.

Report what passed and what failed.

If an external service cannot be tested because credentials
are missing, state that limitation.

## Rule 12: Preserve Existing Data

Never reset the database or delete existing application
files as a shortcut.

Generate migrations that preserve existing data wherever
possible.

## Rule 13: Keep Documentation Current

Update relevant documentation when:

- API contracts change.
- Environment variables change.
- Database migrations are added.
- External integrations are introduced.
- Setup instructions change.

## Rule 14: Explain Significant Decisions

For major architectural decisions, explain:

- The problem.
- The chosen approach.
- Why it is appropriate.
- The alternatives rejected.
- The operational consequences.

Keep explanations concise and useful.

---

# 27. Definition of Done

A feature is complete only when:

1. Its behavior is implemented.
2. Its database changes are versioned when required.
3. Its authentication and authorization are correct.
4. Input validation is implemented.
5. Errors are handled appropriately.
6. Tests cover the important behavior.
7. The frontend is connected to the real backend.
8. Data persists when persistence is required.
9. The feature works after a page reload.
10. Documentation reflects the implementation.

Do not consider placeholder buttons, static mock dashboards
or hardcoded responses to be completed functionality.

Static fixtures are acceptable in automated tests and
explicitly labeled development previews, but they must
not be presented as live external data.

---

# 28. Initial End-to-End Acceptance Scenario

The first complete demo must support this journey.

1. A new user signs in with Google.
2. The user completes conversational onboarding.
3. The system identifies several interests.
4. The user reviews and edits the suggested interests.
5. The interest network displays the resulting graph.
6. The user opens a learning pathway.
7. The user reviews its modules and resources.
8. The user enrolls in the pathway.
9. The user completes an activity.
10. The dashboard reflects the updated progress.
11. The user creates a personal goal.
12. The user asks the AI how to balance the goal with
    their current professional development.
13. The AI responds using relevant stored context.
14. The user's data remains available after logout and
    subsequent login.
15. A different user cannot access these records.

This is the minimum complete end-to-end product journey.

Additional functionality should build on this working
foundation.

---

# 29. Initial Development Commands

Commands must be adapted to the actual repository
structure and installed dependencies.

## Backend

Activate the existing virtual environment:

source backend/.venv/bin/activate

Start the application from the repository root:

uvicorn app.main:app --reload --app-dir backend

Alternatively, if the backend package is already configured
for direct imports, use its documented startup command.

Interactive documentation:

http://127.0.0.1:8000/docs

Run backend tests:

pytest backend/tests

## Frontend

cd frontend

npm install
npm run dev

Run frontend tests:

npm test

Run the production build:

npm run build

Do not run database migrations against a production
database without verifying the target connection.

---

# 30. Final Engineering Objective

Build PlotPlanner as a reliable, personalized, AI-powered
platform that helps people explore multiple interests,
learn useful skills, make realistic plans, pursue personal
goals and discover opportunities.

The software must prioritize:

- Useful functionality
- Clean architecture
- Reliable data
- Clear interfaces
- User control
- Secure authentication
- Verifiable information
- Low operating costs
- Maintainability
- Incremental development

Do not optimize for the number of AI agents, microservices
or technologies used.

Optimize for the quality of the product and the clarity
of its implementation.

The goal is to build a complete, demonstrable application
that can grow into a production-ready system without
requiring an architectural rewrite.

Start with the repository audit.

Do not implement all phases in a single operation.

